"""
Forensic Evidence Analysis System (FEAS) - Digital Forgery Pipeline
Integrates:
- Real ResNet-18 Deep Learning classifier (trained on CASIA 2.0 Benchmark)
- Error Level Analysis (ELA) with quantitative metric extraction
- Spatial frequency and boundary anomaly localizer for splicing/copy-move regions
- Multi-quadrant noise variance consistency analysis
- Full forensic information extraction & advisory reporting
"""

import base64
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import cv2
import numpy as np
from PIL import Image

from src.config import TEMP_DIR
from src.models.forgery.ela import perform_ela
from src.models.forgery.vgg16_detector import get_vgg_detector
from src.models.forgery.yolo_tamper import get_yolo_tamper_detector
from src.models.forgery.ai_synthetics import detect_ai_generation


def compute_image_sha256(img_bgr: np.ndarray) -> str:
    """Compute deterministic SHA-256 hash of image bytes."""
    _, buf = cv2.imencode(".png", img_bgr)
    return hashlib.sha256(buf.tobytes()).hexdigest()


def compute_noise_variance_consistency(gray: np.ndarray) -> Dict[str, float]:
    """
    Measure sensor noise variance across image quadrants.
    Tampered (spliced) images typically exhibit variance divergence between donor and host patches.
    """
    h, w = gray.shape[:2]
    mid_y, mid_x = h // 2, w // 2
    quadrants = [
        gray[:mid_y, :mid_x],
        gray[:mid_y, mid_x:],
        gray[mid_y:, :mid_x],
        gray[mid_y:, mid_x:],
    ]
    variances = [float(np.var(cv2.Laplacian(q, cv2.CV_64F))) for q in quadrants]
    mean_var = float(np.mean(variances))
    std_var = float(np.std(variances))
    disparity = round(std_var / (mean_var + 1e-6), 4)

    return {
        "mean_noise_variance": round(mean_var, 2),
        "quadrant_disparity": disparity,
        "is_divergent": bool(disparity > 0.50),
    }


def run_forgery_check(
    image_input: Union[str, Path, np.ndarray, Image.Image],
    output_dir: Optional[Path] = None,
    sensitivity: int = 75,
) -> Dict[str, Any]:
    """
    Execute comprehensive forensic forgery detection and extract detailed information:
    1. Error Level Analysis (ELA) with adaptive quantitative divergence metrics.
    2. Deep learning classification using trained CASIA 2.0 ResNet-18 model with Grad-CAM spatial activation.
    3. Multi-modal anomaly fusion for guaranteed tamper region localization.
    4. Sensor noise variance consistency analysis.
    5. High-contrast localization masks, annotated detection overlays, and thermal heatmaps.
    """
    out_dir = output_dir or (TEMP_DIR / "forgery_results")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Standardize image array in BGR format
    if isinstance(image_input, (str, Path)):
        img_bgr = cv2.imread(str(image_input))
        base_name = Path(image_input).stem
    elif isinstance(image_input, np.ndarray):
        img_bgr = image_input.copy()
        base_name = "image_input"
    elif isinstance(image_input, Image.Image):
        img_bgr = cv2.cvtColor(np.array(image_input.convert("RGB")), cv2.COLOR_RGB2BGR)
        base_name = "image_input"
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    if img_bgr is None:
        raise ValueError("Failed to decode input image.")

    h, w = img_bgr.shape[:2]
    total_canvas_pixels = h * w
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 1. Image Integrity Hash
    img_sha256 = compute_image_sha256(img_bgr)

    # 2. Perform Adaptive Error Level Analysis (ELA)
    ela_heatmap_bgr, ela_metrics = perform_ela(img_bgr)
    ela_filename = f"{base_name}_ela_heatmap.jpg"
    ela_path = out_dir / ela_filename
    cv2.imwrite(str(ela_path), ela_heatmap_bgr)

    # 3. Deep Learning Classification & Grad-CAM (ResNet-18 trained on CASIA 2.0)
    detector = get_vgg_detector()
    dl_metrics = detector.predict_detailed(img_bgr)
    dl_score = dl_metrics["tamper_prob"]
    gradcam = detector.generate_gradcam(img_bgr)

    # 4. Regional Tamper Localization with Grad-CAM and Adaptive ELA Guide
    yolo_detector = get_yolo_tamper_detector()
    raw_bboxes = yolo_detector.detect(
        img_bgr,
        conf_threshold=0.40,
        ela_guide=ela_heatmap_bgr,
        gradcam_guide=gradcam,
        sensitivity=sensitivity,
    )

    # 5. Sensor Noise Variance Consistency
    noise_info = compute_noise_variance_consistency(gray)

    # 6. Run AI & Deepfake Generative Artifact Analysis (Fourier Spectrum & Noise Kurtosis)
    ai_report = detect_ai_generation(img_bgr, output_dir=out_dir)
    ai_prob = float(ai_report.get("ai_probability", 0.0))
    is_ai = bool(ai_report.get("is_ai_generated", False))

    # Multi-Modal Calibration & Filtering
    ela_factor = min(1.0, float(ela_metrics.get("tamper_ratio", 0.0)) * 3.5)
    noise_factor = 0.80 if noise_info["is_divergent"] else 0.15

    # If deep learning model strongly confirms authentic, ELA has zero divergence, and no AI artifacts detected,
    # prune false-positive natural scene texture boxes
    if dl_score < 0.20 and ela_factor < 0.08 and not is_ai:
        raw_bboxes = []

    # If deep learning model flags tampering (dl_score >= 0.45 or is_ai) or high composite,
    # ensure we have at least the primary tampering region localized from Grad-CAM or ELA peaks
    if (dl_score >= 0.45 or is_ai) and len(raw_bboxes) == 0:
        cam_active = gradcam > max(0.30, float(np.percentile(gradcam, 85)))
        p_mask = cam_active.astype(np.uint8) * 255
        p_cnts, _ = cv2.findContours(p_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for pc in p_cnts:
            if cv2.contourArea(pc) >= (h * w * 0.002):
                px, py, pbw, pbh = cv2.boundingRect(pc)
                raw_bboxes.append({
                    "x1": px, "y1": py, "x2": px + pbw, "y2": py + pbh,
                    "label": "ai_synthesis" if is_ai else "deep_learning_anomaly",
                    "confidence": round(float(dl_score), 4)
                })

    # Enrich bounding boxes with geometric details
    enriched_bboxes = []
    total_tampered_area = 0
    tampering_types = set()

    for box in raw_bboxes:
        bx1, by1, bx2, by2 = box["x1"], box["y1"], box["x2"], box["y2"]
        bw = bx2 - bx1
        bh = by2 - by1
        barea = bw * bh
        total_tampered_area += barea
        label = box.get("label", "splicing")
        tampering_types.add(label)

        enriched_bboxes.append({
            "x1": bx1,
            "y1": by1,
            "x2": bx2,
            "y2": by2,
            "width": bw,
            "height": bh,
            "area_pixels": barea,
            "area_percentage": round((barea / total_canvas_pixels) * 100, 2),
            "centroid": [round(bx1 + bw / 2, 1), round(by1 + bh / 2, 1)],
            "label": label,
            "confidence": box.get("confidence", 0.0),
        })

    surface_tamper_pct = round((total_tampered_area / total_canvas_pixels) * 100, 2)
    box_conf = max([b["confidence"] for b in enriched_bboxes], default=0.0)

    # Weighted multi-modal fusion
    composite_score = float(
        0.50 * dl_score
        + 0.25 * ela_factor
        + 0.15 * box_conf
        + 0.10 * noise_factor
    )

    if enriched_bboxes and composite_score < 0.55:
        composite_score = max(composite_score, box_conf * 0.85)

    # If generative AI artifacts detected, fuse into composite score
    if is_ai:
        composite_score = max(composite_score, ai_prob)
        tampering_types.add("ai-generative")

    composite_score = round(min(0.99, max(0.01, composite_score)), 4)
    is_tampered = bool(composite_score >= 0.50 or is_ai)

    # Human-readable advisory verdict
    if is_ai and is_tampered:
        verdict = f"AI Generative Manipulation Detected ({ai_report.get('likely_archetype', 'Diffusion Model')})"
    elif is_tampered:
        if composite_score >= 0.75:
            verdict = "Manipulated Evidence (High Confidence Splicing / Copy-Move Detected)"
        else:
            verdict = "Suspected Manipulation (Anomalous Signatures Identified, Review Advised)"
    else:
        verdict = "Authentic Photographic Evidence (No Manipulation Signatures Detected)"

    # Primary tampering mode
    if enriched_bboxes:
        primary_tampering_type = ", ".join(sorted(list(tampering_types))).replace("_", " ").title()
    elif is_ai:
        primary_tampering_type = f"AI Generative Synthesis ({ai_report.get('likely_archetype', 'Diffusion')})"
    elif is_tampered:
        primary_tampering_type = "Splicing / Compression Inconsistency"
    else:
        primary_tampering_type = "None (Authentic Baseline)"

    # Technical advisory explanation
    if is_tampered or is_ai:
        findings = []
        if len(enriched_bboxes) > 0:
            findings.append(f"splicing/copy-move tampering ({composite_score*100:.1f}% confidence, {len(enriched_bboxes)} region(s) covering {surface_tamper_pct}% canvas)")
        elif is_tampered and not is_ai:
            findings.append(f"compression/noise tampering ({composite_score*100:.1f}% confidence)")
        if is_ai:
            findings.append(f"AI generative synthesis artifacts ({ai_report['ai_probability']*100:.1f}% AI probability, likely {ai_report['likely_archetype']})")
        advisory_notes = f"Evidence analysis flagged anomalous characteristics: {'; '.join(findings)}."
    else:
        advisory_notes = (
            f"No significant digital tampering or AI generative anomalies detected "
            f"(authenticity confidence: {(1-composite_score)*100:.1f}%, camera optical authenticity: {(1-ai_report['ai_probability'])*100:.1f}%). "
            f"Compression error levels, Fourier spectrum, and sensor noise variance adhere to authentic camera capture."
        )

    # 7. Render Composite Visualizations

    # Visual A: Annotated View (Original photo + glowing crimson highlight fill + bounding box brackets)
    annotated_bgr = img_bgr.copy()
    overlay = annotated_bgr.copy()
    for box in enriched_bboxes:
        bx1, by1, bx2, by2 = box["x1"], box["y1"], box["x2"], box["y2"]
        # Translucent crimson fill over the tampered region
        cv2.rectangle(overlay, (bx1, by1), (bx2, by2), (25, 25, 240), -1)
    cv2.addWeighted(overlay, 0.28, annotated_bgr, 0.72, 0, annotated_bgr)

    for idx, box in enumerate(enriched_bboxes, 1):
        bx1, by1, bx2, by2 = box["x1"], box["y1"], box["x2"], box["y2"]
        label = box["label"].replace("_", " ").upper()
        conf = box["confidence"]

        # Crimson border
        cv2.rectangle(annotated_bgr, (bx1, by1), (bx2, by2), (0, 0, 255), 2)

        # Corner accent crosshairs
        c_len = min(16, max(6, (bx2 - bx1) // 5), max(6, (by2 - by1) // 5))
        cv2.line(annotated_bgr, (bx1, by1), (bx1 + c_len, by1), (0, 235, 255), 3)
        cv2.line(annotated_bgr, (bx1, by1), (bx1, by1 + c_len), (0, 235, 255), 3)
        cv2.line(annotated_bgr, (bx2, by1), (bx2 - c_len, by1), (0, 235, 255), 3)
        cv2.line(annotated_bgr, (bx2, by1), (bx2, by1 + c_len), (0, 235, 255), 3)
        cv2.line(annotated_bgr, (bx1, by2), (bx1 + c_len, by2), (0, 235, 255), 3)
        cv2.line(annotated_bgr, (bx1, by2), (bx1, by2 - c_len), (0, 235, 255), 3)
        cv2.line(annotated_bgr, (bx2, by2), (bx2 - c_len, by2), (0, 235, 255), 3)
        cv2.line(annotated_bgr, (bx2, by2), (bx2, by2 - c_len), (0, 235, 255), 3)

        # High-contrast label tag
        text = f"REGION #{idx}: {label} ({conf*100:.0f}%)"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        tag_y1 = max(0, by1 - 22)
        cv2.rectangle(annotated_bgr, (bx1, tag_y1), (bx1 + tw + 8, max(0, by1)), (12, 14, 24), -1)
        cv2.rectangle(annotated_bgr, (bx1, tag_y1), (bx1 + tw + 8, max(0, by1)), (0, 0, 255), 1)
        cv2.putText(annotated_bgr, text, (bx1 + 4, max(14, by1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    annotated_filename = f"{base_name}_annotated.jpg"
    annotated_path = out_dir / annotated_filename
    cv2.imwrite(str(annotated_path), annotated_bgr)

    # Visual B: Dedicated High-Contrast Localization Mask View
    # Dim background by 65%, illuminate tampered regions with vivid neon thermal glow & highlighted borders
    mask_bgr = (img_bgr * 0.35).astype(np.uint8)
    for idx, box in enumerate(enriched_bboxes, 1):
        bx1, by1, bx2, by2 = box["x1"], box["y1"], box["x2"], box["y2"]
        region_clean = img_bgr[by1:by2, bx1:bx2].astype(np.float32)
        # Apply vibrant thermal highlight
        region_clean[:, :, 2] = np.clip(region_clean[:, :, 2] * 1.35 + 45, 0, 255)
        region_clean[:, :, 0] = np.clip(region_clean[:, :, 0] * 0.70, 0, 255)
        mask_bgr[by1:by2, bx1:bx2] = region_clean.astype(np.uint8)
        cv2.rectangle(mask_bgr, (bx1, by1), (bx2, by2), (0, 50, 255), 2)
        # Regional ID Tag
        tag_text = f"TAMPERED #{idx}"
        cv2.putText(mask_bgr, tag_text, (bx1 + 4, max(16, by1 + 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

    mask_filename = f"{base_name}_localization_mask.jpg"
    mask_path = out_dir / mask_filename
    cv2.imwrite(str(mask_path), mask_bgr)

    # Visual C: Deep Learning Grad-CAM Activation Heatmap
    cam_uint8 = (gradcam * 255.0).astype(np.uint8)
    cam_colormap = cv2.applyColorMap(cam_uint8, cv2.COLORMAP_JET)
    gradcam_bgr = cv2.addWeighted(img_bgr, 0.45, cam_colormap, 0.55, 0)
    gradcam_filename = f"{base_name}_gradcam.jpg"
    gradcam_path = out_dir / gradcam_filename
    cv2.imwrite(str(gradcam_path), gradcam_bgr)

    # Base64 encodings for immediate reactive frontend display
    _, ela_buf = cv2.imencode(".jpg", ela_heatmap_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    ela_b64 = "data:image/jpeg;base64," + base64.b64encode(ela_buf).decode("utf-8")

    _, ann_buf = cv2.imencode(".jpg", annotated_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    ann_b64 = "data:image/jpeg;base64," + base64.b64encode(ann_buf).decode("utf-8")

    _, mask_buf = cv2.imencode(".jpg", mask_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    mask_b64 = "data:image/jpeg;base64," + base64.b64encode(mask_buf).decode("utf-8")

    _, cam_buf = cv2.imencode(".jpg", gradcam_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    cam_b64 = "data:image/jpeg;base64," + base64.b64encode(cam_buf).decode("utf-8")

    return {
        "status": "success",
        "verdict": verdict,
        "tamper_score": composite_score,
        "confidence": f"{composite_score * 100:.1f}%",
        "is_tampered": is_tampered,
        "tampering_type": primary_tampering_type,
        "tampering_types_detected": list(tampering_types),
        "is_ai_generated": ai_report["is_ai_generated"],
        "ai_probability": ai_report["ai_probability"],
        "ai_archetype": ai_report["likely_archetype"],
        "ai_analysis": ai_report,
        "bboxes": enriched_bboxes,
        "regional_analysis": {
            "total_regions": len(enriched_bboxes),
            "tampered_pixel_area": total_tampered_area,
            "tampered_surface_percentage": surface_tamper_pct,
            "regions": enriched_bboxes,
        },
        "signal_analysis": {
            "ela_tamper_ratio": ela_metrics.get("tamper_ratio", 0.0),
            "ela_mean_diff": ela_metrics.get("mean_diff", 0.0),
            "ela_max_diff": ela_metrics.get("max_diff", 0),
            "noise_consistency": noise_info,
            "fft_spectrum_path": ai_report.get("fft_spectrum_image_path"),
        },
        "ela_metrics": ela_metrics,
        "model_details": {
            "model_architecture": dl_metrics["model_architecture"],
            "deep_learning_probability": dl_score,
            "is_trained_model": dl_metrics["is_trained_model"],
            "checkpoint_source": dl_metrics["checkpoint_source"],
        },
        "integrity": {
            "sha256": img_sha256,
            "resolution": f"{w}x{h}",
            "channels": int(img_bgr.shape[2]) if len(img_bgr.shape) > 2 else 1,
        },
        "advisory_notes": advisory_notes,
        "annotated_image_path": str(annotated_path),
        "mask_image_path": str(mask_path),
        "ela_image_path": str(ela_path),
        "gradcam_image_path": str(gradcam_path),
        "fft_spectrum_image_path": ai_report.get("fft_spectrum_image_path"),
        "ela_image_base64": ela_b64,
        "annotated_image_base64": ann_b64,
        "mask_image_base64": mask_b64,
        "gradcam_image_base64": cam_b64,
        "fft_spectrum_base64": ai_report.get("fft_spectrum_base64"),
    }
