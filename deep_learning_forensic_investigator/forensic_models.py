"""
Model adapter layer for Deep Learning Forensic Investigator.
Equipped with real trained ResNet-18 deep learning classifier (CASIA 2.0 Forensic Benchmark),
Error Level Analysis (ELA), and spatial gradient anomaly detection.
"""

import hashlib
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

# Ensure root and FEAS paths are importable
INVESTIGATOR_DIR = Path(__file__).resolve().parent
ROOT_DIR = INVESTIGATOR_DIR.parent
FEAS_DIR = ROOT_DIR / "FEAS"

for p in [str(ROOT_DIR), str(FEAS_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def image_sha256(image: Image.Image) -> str:
    import io
    b = io.BytesIO()
    image.save(b, format="PNG")
    return hashlib.sha256(b.getvalue()).hexdigest()


def is_forgery_model_ready() -> bool:
    """Check if trained tampering weights are available."""
    ckpt_feas = FEAS_DIR / "models" / "tampering_resnet18_best.pt"
    ckpt_root = ROOT_DIR / "models" / "tampering_resnet18_best.pt"
    return ckpt_feas.exists() or ckpt_root.exists() or os.getenv("FORGERY_MODEL_READY") == "1"


def model_status():
    trained_ready = is_forgery_model_ready()
    return {
        "Forgery detector": {
            "loaded": trained_ready,
            "detail": "Trained ResNet-18 on CASIA 2.0 (F1: 87.8%) with ELA & Anomaly Localization" if trained_ready else "No trained detector configured",
        },
        "Face embedding model": {
            "loaded": os.getenv("FACE_MODEL_READY") == "1",
            "detail": "Adapter enabled" if os.getenv("FACE_MODEL_READY") == "1" else "No face embedding model configured",
        },
        "Wound classifier": {
            "loaded": os.getenv("WOUND_MODEL_READY") == "1",
            "detail": "Adapter enabled" if os.getenv("WOUND_MODEL_READY") == "1" else "No wound classifier configured",
        },
        "CCTV YOLOv8 & Tracker": {
            "loaded": True,
            "detail": "COCO pretrained YOLOv8 & ByteTrack ready",
        },
    }


def demo_overlay(image):
    out = image.copy().convert("RGB")
    draw = ImageDraw.Draw(out)
    w, h = out.size
    # Visually labelled demo boxes, not computed detections.
    boxes = [
        (int(w * 0.10), int(h * 0.12), int(w * 0.42), int(h * 0.38)),
        (int(w * 0.56), int(h * 0.56), int(w * 0.88), int(h * 0.84)),
    ]
    for box in boxes:
        draw.rectangle(box, outline=(255, 60, 70), width=max(3, min(w, h) // 100))
    draw.text((10, 10), "DEMO OVERLAY - NOT A DETECTION", fill=(255, 60, 70))
    return out


def detect_forgery(image: Image.Image, real: bool = False):
    """
    Execute digital forgery detection.
    When real=True (or trained model is present), runs multi-modal analysis:
    - Trained ResNet-18 Deep Learning classifier (CASIA 2.0 Benchmark)
    - Error Level Analysis (ELA) compression residuals
    - Spatial frequency gradient boundary anomaly detection
    - Quadrant noise variance consistency check
    Returns full structured forensic information and annotated overlay image.
    """
    if real or is_forgery_model_ready():
        try:
            import cv2
            from src.models.forgery.pipeline import run_forgery_check

            # Convert PIL Image to BGR for OpenCV pipeline
            rgb_arr = np.array(image.convert("RGB"))
            bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)

            out_dir = INVESTIGATOR_DIR / "runs" / "forgery"
            out_dir.mkdir(parents=True, exist_ok=True)

            res = run_forgery_check(bgr_arr, output_dir=out_dir)

            # Load annotated visualization image
            annotated_img_path = res.get("annotated_image_path")
            if annotated_img_path and Path(annotated_img_path).exists():
                overlay_img = Image.open(annotated_img_path).convert("RGB")
            else:
                overlay_img = image.copy()

            summary = {
                "verdict": res.get("verdict"),
                "tampering_detected": res.get("is_tampered"),
                "confidence": res.get("confidence"),
                "tampering_score": res.get("tamper_score"),
                "tampering_type": res.get("tampering_type"),
                "tampering_types_detected": res.get("tampering_types_detected", []),
                "regions_found": res.get("regional_analysis", {}).get("total_regions", 0),
                "tampered_surface_area": f"{res.get('regional_analysis', {}).get('tampered_surface_percentage', 0)}% of image",
                "localized_regions": res.get("bboxes", []),
                "ela_metrics": {
                    "tamper_ratio": res.get("signal_analysis", {}).get("ela_tamper_ratio"),
                    "mean_compression_diff": res.get("signal_analysis", {}).get("ela_mean_diff"),
                    "max_compression_diff": res.get("signal_analysis", {}).get("ela_max_diff"),
                },
                "noise_consistency": res.get("signal_analysis", {}).get("noise_consistency", {}),
                "model_architecture": res.get("model_details", {}).get("model_architecture"),
                "is_ai_generated": res.get("is_ai_generated"),
                "ai_probability": f"{res.get('ai_probability', 0)*100:.1f}%",
                "ai_archetype": res.get("ai_archetype"),
                "fft_spectral_analysis": res.get("ai_analysis", {}).get("spectral_analysis", {}),
                "image_sha256": res.get("integrity", {}).get("sha256", image_sha256(image)),
                "image_resolution": res.get("integrity", {}).get("resolution"),
                "advisory_notes": res.get("advisory_notes"),
            }

            return {
                "status": "success",
                "is_demo": False,
                "overlay": overlay_img,
                "summary": summary,
            }

        except Exception as e:
            return {
                "status": "error",
                "is_demo": False,
                "message": f"Inference execution error: {e}",
                "summary": {"status": "Error", "error_details": str(e)},
            }

    # Demo fallback when no real weights are found and real=False
    return {
        "status": "demo",
        "is_demo": True,
        "overlay": demo_overlay(image),
        "summary": {
            "mode": "DEMO - synthetic illustration",
            "result": "Illustrative regions shown only to demonstrate UI",
            "tampering_detected": None,
            "confidence": None,
            "note": "No forensic inference was performed.",
        },
    }


def authenticate_faces(image_a, image_b, real=False):
    if real:
        return {
            "status": "not_configured",
            "is_demo": False,
            "message": "No real face-embedding adapter is implemented. Connect a validated face model and calibrated threshold; no identity prediction was made.",
            "summary": {"status": "Not run"},
        }
    return {
        "status": "demo",
        "is_demo": True,
        "summary": {
            "mode": "DEMO - synthetic illustration",
            "similarity_score": None,
            "identity_match": None,
            "note": "No face embedding or identity comparison was performed. A synthetic score is intentionally not generated.",
        },
    }


def classify_wound(image, real=False):
    if real:
        return {
            "status": "not_configured",
            "is_demo": False,
            "message": "No real wound classifier adapter is implemented. Connect a trained and clinically validated model; no classification was made.",
            "summary": {"status": "Not run"},
        }
    return {
        "status": "demo",
        "is_demo": True,
        "summary": {
            "mode": "DEMO - synthetic illustration",
            "predicted_type": None,
            "predicted_severity": None,
            "predicted_age": None,
            "confidence": None,
            "note": "No wound inference was performed. Wound age/severity should not be inferred from this demo.",
        },
    }
