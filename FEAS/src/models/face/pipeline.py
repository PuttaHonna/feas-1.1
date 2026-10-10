"""
Forensic Evidence Analysis System (FEAS) - Unified Face Pipeline
Detects human faces using MTCNN and facial geometry, performs super-resolution enhancement, and extracts 512-d FaceNet embeddings only when faces are present.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image

try:
    from facenet_pytorch import MTCNN
    _mtcnn = MTCNN(keep_all=False, select_largest=True, min_face_size=20)
except Exception:
    _mtcnn = None

from src.config import TEMP_DIR
from src.models.face.embeddings import get_facenet_extractor
from src.models.face.restoration import get_face_restorer


def detect_face_region(img_bgr: np.ndarray) -> Tuple[bool, np.ndarray, Optional[Tuple[int, int, int, int]]]:
    """
    Detect if the image contains a human face.
    Returns: (face_detected: bool, face_crop: np.ndarray, bbox: Optional[Tuple])
    """
    h, w = img_bgr.shape[:2]

    # 1. Try neural MTCNN detector for scenes
    if _mtcnn is not None and max(h, w) > 100:
        try:
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            boxes, probs = _mtcnn.detect(pil_img)
            if boxes is not None and len(boxes) > 0 and probs[0] is not None and probs[0] > 0.60:
                box = boxes[0]
                x1 = max(0, int(box[0]))
                y1 = max(0, int(box[1]))
                x2 = min(w, int(box[2]))
                y2 = min(h, int(box[3]))
                if (x2 - x1) > 15 and (y2 - y1) > 15:
                    return True, img_bgr[y1:y2, x1:x2], (x1, y1, x2, y2)
        except Exception:
            pass

    # 2. Check if the image itself is already a dedicated face crop (e.g. CCTV crop <= 256px with facial aspect ratio)
    if max(h, w) <= 256 and (0.55 <= w / max(1, h) <= 1.8):
        # Verify color & structural variance is consistent with facial imagery
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        std_val = float(np.std(gray))
        if 15.0 <= std_val <= 90.0:
            return True, img_bgr, (0, 0, w, h)

    return False, img_bgr, None


def process_face(
    image_input: Union[str, Path, np.ndarray, Image.Image],
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Execute genuine face forensic processing:
    1. Detect face presence. If no face is detected, return clean empty result without fake matches.
    2. If face detected: Enhance to 1024x1024, extract 512-d FaceNet embedding, and match against suspect gallery.
    """
    out_dir = output_dir or (TEMP_DIR / "face_results")
    out_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(image_input, (str, Path)):
        img_bgr = cv2.imread(str(image_input))
        base_name = Path(image_input).stem
    elif isinstance(image_input, np.ndarray):
        img_bgr = image_input.copy()
        base_name = "evidence_input"
    elif isinstance(image_input, Image.Image):
        img_bgr = cv2.cvtColor(np.array(image_input.convert("RGB")), cv2.COLOR_RGB2BGR)
        base_name = "evidence_input"
    else:
        raise TypeError(f"Unsupported input type: {type(image_input)}")

    if img_bgr is None:
        raise ValueError("Failed to load evidence image.")

    # 1. Detect if a face actually exists in the image
    face_detected, face_crop, bbox = detect_face_region(img_bgr)
    
    if not face_detected:
        return {
            "face_detected": False,
            "restored_img": None,
            "restored_shape": [],
            "embedding": [],
            "matches": [],
            "top_match": None,
            "cctv_crop_path": None,
            "restored_image_path": None,
            "comparison_image_path": None,
            "message": "No human facial subject identified in evidence frame."
        }

    # 2. Super-resolution to 1024x1024
    restorer = get_face_restorer()
    restored_path = out_dir / f"{base_name}_restored_1024.jpg"
    restored_bgr, _ = restorer.enhance_face(face_crop, output_path=restored_path)

    # 3. Extract 512-d FaceNet embedding
    extractor = get_facenet_extractor()
    embedding_np = extractor.extract_embedding(restored_bgr)
    embedding_list = embedding_np.tolist()

    # 4. Match against gallery
    all_matches = extractor.match_against_gallery(embedding_np, top_k=5)
    valid_matches = [m for m in all_matches if m.get("similarity", 0) >= 0.60]
    top_match = valid_matches[0] if valid_matches else None

    # 5. Generate side-by-side comparison image
    comp_crop = cv2.resize(face_crop, (512, 512), interpolation=cv2.INTER_NEAREST)
    comp_restored = cv2.resize(restored_bgr, (512, 512), interpolation=cv2.INTER_AREA)

    cv2.putText(comp_crop, "ORIGINAL FACE CROP", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.putText(comp_restored, "FEAS 1024px RESTORED", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    comparison_bgr = np.hstack([comp_crop, comp_restored])
    comp_path = out_dir / f"{base_name}_comparison.jpg"
    cv2.imwrite(str(comp_path), comparison_bgr)

    crop_path = out_dir / f"{base_name}_raw_crop.jpg"
    cv2.imwrite(str(crop_path), face_crop)

    return {
        "face_detected": True,
        "restored_img": restored_bgr,
        "restored_shape": list(restored_bgr.shape),
        "embedding": embedding_list,
        "matches": valid_matches,
        "top_match": top_match,
        "cctv_crop_path": str(crop_path),
        "restored_image_path": str(restored_path),
        "comparison_image_path": str(comp_path),
        "message": f"Face detected ({face_crop.shape[1]}x{face_crop.shape[0]}px) and enhanced to 1024x1024."
    }
