"""
Fixture Generation Script for FEAS Test Suite
Generates synthetic forensic test assets: sample images, low-res faces, bullet striae, and test video.
"""

import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import piexif
from src.config import FIXTURES_DIR


def generate_sample_image(output_path: Path) -> Path:
    """Generate sample forensic image with simulated tampering and valid EXIF GPS."""
    img = Image.new("RGB", (640, 480), color=(220, 225, 230))
    draw = ImageDraw.Draw(img)
    
    # Draw background elements
    draw.rectangle([50, 50, 590, 430], outline=(100, 100, 100), width=3)
    draw.text((80, 80), "EVIDENCE RECORD: ITEM #094-B", fill=(20, 20, 20))
    draw.text((80, 120), "FORENSIC INTEGRITY TEST CASE", fill=(50, 50, 50))
    
    # Spliced / tampered zone (different texture / noise)
    draw.rectangle([250, 180, 450, 320], fill=(200, 210, 225), outline=(255, 0, 0), width=2)
    draw.text((270, 230), "[MODIFIED ZONE]", fill=(180, 20, 20))

    # Add realistic EXIF metadata and GPS tags
    zeroth_ifd = {
        piexif.ImageIFD.Make: b"Nikon",
        piexif.ImageIFD.Model: b"D850-Forensic",
        piexif.ImageIFD.Software: b"FEAS Firmware v1.0"
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: b"2026:08:20 14:32:00",
    }
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: b"N",
        piexif.GPSIFD.GPSLatitude: ((37, 1), (46, 1), (2974, 100)),  # 37.774928
        piexif.GPSIFD.GPSLongitudeRef: b"W",
        piexif.GPSIFD.GPSLongitude: ((122, 1), (25, 1), (998, 100)), # -122.41944
    }
    exif_dict = {"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": gps_ifd}
    exif_bytes = piexif.dump(exif_dict)
    
    img.save(output_path, "JPEG", exif=exif_bytes, quality=95)
    return output_path


def generate_cctv_face_crop(output_path: Path) -> Path:
    """Generate a low-resolution (64x64) CCTV face crop for super-resolution and embeddings."""
    img = np.zeros((64, 64, 3), dtype=np.uint8) + 180
    # Add face-like geometric structure
    cv2.circle(img, (32, 30), 20, (150, 160, 190), -1)  # head
    cv2.circle(img, (26, 26), 3, (40, 40, 40), -1)      # left eye
    cv2.circle(img, (38, 26), 3, (40, 40, 40), -1)      # right eye
    cv2.ellipse(img, (32, 38), (8, 4), 0, 0, 180, (50, 50, 50), -1) # mouth
    # Add surveillance blur & noise
    noise = np.random.normal(0, 10, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    cv2.imwrite(str(output_path), img)
    return output_path


def generate_wound_sample(output_path: Path) -> Path:
    """Generate a simulated wound image for triage classification."""
    img = np.zeros((256, 256, 3), dtype=np.uint8) + 210
    # Draw simulated wound lesion
    cv2.ellipse(img, (128, 128), (45, 25), 30, 0, 360, (40, 30, 180), -1)
    cv2.circle(img, (128, 128), 15, (20, 20, 120), -1)
    cv2.putText(img, "CASE #W-401", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1)
    cv2.imwrite(str(output_path), img)
    return output_path


def generate_bullet_sample(output_path: Path) -> Path:
    """Generate a simulated microscopic bullet striation image."""
    img = np.zeros((256, 256, 3), dtype=np.uint8) + 140
    # Draw vertical striae lines with varied thickness and intensity
    for x in range(20, 240, 6):
        intensity = int(80 + 100 * np.sin(x * 0.2))
        thickness = 1 if x % 12 != 0 else 2
        cv2.line(img, (x, 20), (x, 235), (intensity, intensity + 5, intensity + 10), thickness)
    # Add casing curvature shading
    overlay = img.copy()
    cv2.circle(overlay, (128, 128), 110, (180, 180, 180), 3)
    cv2.putText(overlay, "STRIAE-9MM-6R", (20, 245), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 20, 20), 1)
    cv2.imwrite(str(output_path), overlay)
    return output_path


def generate_sample_video(output_path: Path) -> Path:
    """Generate a 3-second 30fps synthetic video with 3 distinct frames to test 1fps keyframe extraction."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = 30
    duration_sec = 3
    total_frames = fps * duration_sec
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (320, 240))
    
    for i in range(total_frames):
        sec = i // fps
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        color = (min(255, 40 * (sec + 1)), min(255, 60 * (sec + 1)), min(255, 70 * (sec + 1)))
        frame[:] = color
        cv2.putText(frame, f"FEAS TIMECODE: 00:0{sec}", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        writer.write(frame)
        
    writer.release()
    return output_path


def generate_mock_case_data(output_path: Path) -> Path:
    """Generate structured mock case JSON for report testing."""
    mock_data = {
        "case_id": "8f2a71bc-341e-4c7b-b389-10fa312984ea",
        "created_at": "2026-08-22T06:15:00.000000Z",
        "investigator_name": "Special Agent J. Miller",
        "filename": "surveillance_sector4_cam02.jpg",
        "file_type": "image",
        "input_sha256": "4a7d1ed414474e4033ac29ccb8653d9b168aae62c3e1fecd4f1345d3e0c0b891",
        "output_sha256": "c89b3f4e223910c2830f5a1e78019bca458319f390218de42b8901ab78239014",
        "status": "COMPLETED",
        "verdict": "TAMPERED / SUSPECT MATCH IDENTIFIED",
        "operator_notes": "Immediate evidence intake following sector 4 incident. High priority suspect match.",
        "metadata": {
            "has_exif": True,
            "device_make": "Nikon",
            "device_model": "D850-Forensic",
            "software": "FEAS Firmware v1.0",
            "datetime_original": "2026-08-20 14:32:00",
            "gps": {"latitude": 37.774928, "longitude": -122.41944}
        },
        "forgery": {
            "tamper_score": 0.88,
            "is_tampered": True,
            "bboxes": [
                {"x1": 250, "y1": 180, "x2": 450, "y2": 320, "label": "splicing", "confidence": 0.92}
            ],
            "ela_metrics": {
                "mean_error": 18.42,
                "max_error": 142.0,
                "tamper_ratio": 0.14
            },
            "annotated_image_path": str(FIXTURES_DIR / "sample.jpg"),
            "ela_image_path": str(FIXTURES_DIR / "sample.jpg")
        },
        "face": {
            "restored_shape": [1024, 1024, 3],
            "top_match": {
                "suspect_id": "SUSP-10492",
                "name": "Marcus Vance",
                "similarity": 0.84,
                "distance": 0.16,
                "notes": "Prior Grand Larceny, subject spotted near sector 4 CCTV."
            },
            "matches": [
                {
                    "suspect_id": "SUSP-10492",
                    "name": "Marcus Vance",
                    "similarity": 0.84,
                    "distance": 0.16,
                    "notes": "Prior Grand Larceny, subject spotted near sector 4 CCTV."
                },
                {
                    "suspect_id": "SUSP-88301",
                    "name": "Elena Rostova",
                    "similarity": 0.32,
                    "distance": 0.68,
                    "notes": "Cyber forgery suspect."
                }
            ],
            "cctv_crop_path": str(FIXTURES_DIR / "cctv_crop.jpg"),
            "restored_image_path": str(FIXTURES_DIR / "cctv_crop.jpg")
        },
        "wound": {
            "wound_type": "gunshot",
            "wound_type_confidence": 0.94,
            "severity": "severe",
            "severity_confidence": 0.91,
            "age": "fresh",
            "age_confidence": 0.87,
            "location": "torso",
            "location_confidence": 0.95,
            "annotated_image_path": str(FIXTURES_DIR / "wound_sample.jpg")
        },
        "ballistics": {
            "caliber": "9mm",
            "caliber_confidence": 0.96,
            "rifling": "6R",
            "rifling_confidence": 0.93,
            "manufacturer": "Glock",
            "manufacturer_confidence": 0.89,
            "striation_map_path": str(FIXTURES_DIR / "bullet_sample.jpg")
        },
        "audit_trail": [
            {
                "timestamp": "2026-08-22T06:15:00.102340Z",
                "action": "CASE_CREATED",
                "input_sha256": "4a7d1ed414474e4033ac29ccb8653d9b168aae62c3e1fecd4f1345d3e0c0b891",
                "details": "Intake validation passed."
            },
            {
                "timestamp": "2026-08-22T06:15:01.450120Z",
                "action": "EXIF_METADATA_EXTRACTED",
                "details": "GPS coordinates verified (37.774928, -122.41944)."
            },
            {
                "timestamp": "2026-08-22T06:15:03.882100Z",
                "action": "FORGERY_INFERENCE_COMPLETED",
                "details": "Tampering detected at (250, 180, 450, 320), confidence 0.92."
            },
            {
                "timestamp": "2026-08-22T06:15:05.120400Z",
                "action": "FACE_RECOGNITION_COMPLETED",
                "details": "Suspect match SUSP-10492 (Marcus Vance), similarity 0.84."
            },
            {
                "timestamp": "2026-08-22T06:15:06.901230Z",
                "action": "WOUND_BALLISTICS_COMPLETED",
                "details": "Wound classified gunshot/severe, 9mm 6R Glock signature."
            }
        ]
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mock_data, f, indent=2)
    return output_path


def generate_deepfake_sample(output_path: Path) -> Path:
    """Generate synthetic AI face image with periodic checkerboard artifacts and AI tool markers."""
    h, w = 512, 512
    img = np.zeros((h, w, 3), dtype=np.uint8) + 160
    
    # Face structure
    cv2.circle(img, (256, 230), 140, (140, 160, 210), -1)
    cv2.circle(img, (200, 200), 22, (30, 30, 30), -1)
    cv2.circle(img, (312, 200), 22, (30, 30, 30), -1)
    cv2.ellipse(img, (256, 300), (55, 25), 0, 0, 180, (40, 40, 140), -1)
    
    # Inject high-frequency periodic grid spikes (GAN transposed-convolution signature)
    y, x = np.mgrid[:h, :w]
    grid_pattern = (np.sin(2 * np.pi * x / 8.0) * np.sin(2 * np.pi * y / 8.0) * 20.0).astype(np.int16)
    img = np.clip(img.astype(np.int16) + grid_pattern[:, :, None], 0, 255).astype(np.uint8)

    # Save as PNG with embedded AI generation parameters chunk
    from PIL import PngImagePlugin
    meta = PngImagePlugin.PngInfo()
    meta.add_text("parameters", "StableDiffusion model: SDXL prompt: photorealistic forensic portrait, seed 42")
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    pil_img.save(output_path, "PNG", pnginfo=meta)
    return output_path


def generate_audio_sample(output_path: Path) -> Path:
    """Generate synthetic audio WAV file (16kHz mono) with robotic harmonic series."""
    from scipy.io import wavfile
    sr = 16000
    duration = 3.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    
    # Formant harmonics (180 Hz, 360 Hz, 540 Hz)
    f0 = 180.0
    voice = 0.4 * np.sin(2 * np.pi * f0 * t) + 0.25 * np.sin(2 * np.pi * 2 * f0 * t) + 0.15 * np.sin(2 * np.pi * 3 * f0 * t)
    
    # Low micro-jitter (flat synthetic tone)
    voice = (voice * 32767.0).astype(np.int16)
    wavfile.write(str(output_path), sr, voice)
    return output_path


def create_all_fixtures() -> None:
    """Generate all test fixtures in tests/fixtures directory."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    generate_sample_image(FIXTURES_DIR / "sample.jpg")
    generate_cctv_face_crop(FIXTURES_DIR / "cctv_crop.jpg")
    generate_wound_sample(FIXTURES_DIR / "wound_sample.jpg")
    generate_bullet_sample(FIXTURES_DIR / "bullet_sample.jpg")
    generate_sample_video(FIXTURES_DIR / "sample_video.mp4")
    generate_deepfake_sample(FIXTURES_DIR / "deepfake_sample.png")
    generate_audio_sample(FIXTURES_DIR / "sample_audio.wav")
    generate_mock_case_data(FIXTURES_DIR / "mock_case_data.json")
    print(f"Successfully generated all test fixtures in {FIXTURES_DIR}")


if __name__ == "__main__":
    create_all_fixtures()

