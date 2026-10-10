"""Model adapter layer.

Demo mode deliberately returns synthetic illustrative outputs.
Real mode only runs when a real, trained model adapter is configured.
Do not replace the real-mode guards with fabricated scores.
"""
import hashlib
import os
from PIL import Image, ImageDraw

def image_sha256(image):
    import io
    b = io.BytesIO()
    image.save(b, format="PNG")
    return hashlib.sha256(b.getvalue()).hexdigest()

def model_status():
    # Set these environment variables only after implementing the corresponding adapter.
    return {
        "Forgery detector": {
            "loaded": os.getenv("FORGERY_MODEL_READY") == "1",
            "detail": "Adapter enabled" if os.getenv("FORGERY_MODEL_READY") == "1" else "No trained detector configured"
        },
        "Face embedding model": {
            "loaded": os.getenv("FACE_MODEL_READY") == "1",
            "detail": "Adapter enabled" if os.getenv("FACE_MODEL_READY") == "1" else "No face embedding model configured"
        },
        "Wound classifier": {
            "loaded": os.getenv("WOUND_MODEL_READY") == "1",
            "detail": "Adapter enabled" if os.getenv("WOUND_MODEL_READY") == "1" else "No wound classifier configured"
        },
        "CCTV YOLOv8 & Tracker": {
            "loaded": True,
            "detail": "COCO pretrained YOLOv8 & ByteTrack ready"
        }
    }

def demo_overlay(image):
    out = image.copy().convert("RGB")
    draw = ImageDraw.Draw(out)
    w, h = out.size
    # Visually labelled demo boxes, not computed detections.
    boxes = [
        (int(w*.10), int(h*.12), int(w*.42), int(h*.38)),
        (int(w*.56), int(h*.56), int(w*.88), int(h*.84))
    ]
    for box in boxes:
        draw.rectangle(box, outline=(255, 60, 70), width=max(3, min(w,h)//100))
    draw.text((10, 10), "DEMO OVERLAY - NOT A DETECTION", fill=(255, 60, 70))
    return out

def detect_forgery(image, real=False):
    if real:
        if os.getenv("FORGERY_MODEL_READY") != "1":
            return {"status":"not_configured", "is_demo":False, "message":"No real forgery model adapter is configured. Implement your trained model call in forensic_models.py; no prediction was made.", "summary":{"status":"Not run"}}
        # Intentionally fail closed until project-specific model inference is implemented.
        return {"status":"not_configured", "is_demo":False, "message":"FORGERY_MODEL_READY is set, but inference adapter is not implemented. Connect your model's preprocessing and output postprocessing before enabling this flag.", "summary":{"status":"Not run"}}
    return {
        "status":"demo",
        "is_demo":True,
        "overlay":demo_overlay(image),
        "summary":{
            "mode":"DEMO - synthetic illustration",
            "result":"Illustrative regions shown only to demonstrate UI",
            "tampering_detected":None,
            "confidence":None,
            "note":"No forensic inference was performed."
        }
    }

def authenticate_faces(image_a, image_b, real=False):
    if real:
        return {"status":"not_configured","is_demo":False,"message":"No real face-embedding adapter is implemented. Connect a validated face model and calibrated threshold; no identity prediction was made.","summary":{"status":"Not run"}}
    return {
        "status":"demo","is_demo":True,
        "summary":{
            "mode":"DEMO - synthetic illustration",
            "similarity_score":None,
            "identity_match":None,
            "note":"No face embedding or identity comparison was performed. A synthetic score is intentionally not generated."
        }
    }

def classify_wound(image, real=False):
    if real:
        return {"status":"not_configured","is_demo":False,"message":"No real wound classifier adapter is implemented. Connect a trained and clinically validated model; no classification was made.","summary":{"status":"Not run"}}
    return {
        "status":"demo","is_demo":True,
        "summary":{
            "mode":"DEMO - synthetic illustration",
            "predicted_type":None,
            "predicted_severity":None,
            "predicted_age":None,
            "confidence":None,
            "note":"No wound inference was performed. Wound age/severity should not be inferred from this demo."
        }
    }
