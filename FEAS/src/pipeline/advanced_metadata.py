"""
Forensic Evidence Analysis System (FEAS) - Advanced Hex & Metadata Forensic Examiner
Inspects binary markers, AI generator signatures, editing tool footprints, JPEG DQT tables, and steganography payloads.
"""

import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Union


# Signatures for Generative AI systems in binary / metadata streams
AI_SIGNATURES = [
    (b"prompt", "AI Prompt Generation Metadata"),
    (b"negative_prompt", "AI Negative Prompt Metadata"),
    (b"StableDiffusion", "Stable Diffusion Synthesis Engine"),
    (b"automatic1111", "Automatic1111 WebUI Generation Profile"),
    (b"comfyui", "ComfyUI Node Generation Pipeline"),
    (b"midjourney", "Midjourney Generative Engine"),
    (b"dall-e", "OpenAI DALL-E Generative Model"),
    (b"c2pa", "C2PA Provenance / Content Credentials Manifest"),
    (b"firefly", "Adobe Firefly Generative AI"),
    (b"novelai", "NovelAI Diffusion Model"),
    (b"flux.1", "Flux Diffusion Engine"),
    (b"checkpoint", "Model Checkpoint Hash Embedded"),
    (b"lora:", "LoRA Neural Adaptation Tag")
]

# Signatures for Graphic & Photo Editing Suites
EDITOR_SIGNATURES = [
    (b"Adobe Photoshop", "Adobe Photoshop"),
    (b"Adobe Lightroom", "Adobe Lightroom"),
    (b"GIMP", "GNU Image Manipulation Program (GIMP)"),
    (b"Canva", "Canva Online Editor"),
    (b"PicsArt", "PicsArt Photo Studio"),
    (b"Snapseed", "Snapseed Mobile Editor"),
    (b"Affinity Photo", "Serif Affinity Photo"),
    (b"Photopea", "Photopea Advanced Web Editor")
]


def inspect_advanced_binary_metadata(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Perform deep binary and metadata forensic analysis on evidence file.
    """
    path = Path(file_path)
    if not path.exists():
        return {
            "valid_file": False,
            "error": "File does not exist"
        }

    file_size = path.stat().st_size
    
    # Read binary content (up to 50MB for scanning)
    with open(path, "rb") as f:
        header = f.read(min(file_size, 4096))
        f.seek(0)
        content_sample = f.read(min(file_size, 20 * 1024 * 1024))

    suffix = path.suffix.lower()
    ai_detected: List[str] = []
    editors_detected: List[str] = []
    tamper_flags: List[str] = []

    # 1. Scan for Generative AI markers
    content_lower = content_sample.lower()
    for sig_bytes, sig_label in AI_SIGNATURES:
        if sig_bytes.lower() in content_lower:
            ai_detected.append(sig_label)

    # 2. Scan for Editing Software signatures
    for edit_bytes, edit_label in EDITOR_SIGNATURES:
        if edit_bytes in content_sample:
            if edit_label not in editors_detected:
                editors_detected.append(edit_label)

    # 3. File Header & Magic Byte Validation
    magic_valid = False
    format_identified = "Unknown"

    if header.startswith(b"\xFF\xD8\xFF"):
        magic_valid = True
        format_identified = "JPEG / JFIF / EXIF"
    elif header.startswith(b"\x89PNG\r\n\x1a\n"):
        magic_valid = True
        format_identified = "Portable Network Graphics (PNG)"
    elif b"ftyp" in header[:32]:
        magic_valid = True
        format_identified = "ISO Media / MP4 / QuickTime"
    elif header.startswith(b"\x1a\x45\xdf\xa3"):
        magic_valid = True
        format_identified = "Matroska / MKV Video"
    elif header.startswith(b"RIFF") and header[8:12] == b"AVI ":
        magic_valid = True
        format_identified = "Audio Video Interleave (AVI)"
    elif header.startswith(b"RIFF") and header[8:12] == b"WAVE":
        magic_valid = True
        format_identified = "WAVEform Audio (WAV)"

    if not magic_valid:
        tamper_flags.append("Magic byte header mismatch: File content does not match expected container signature")

    # 4. Steganography / Overlay Payload Inspection (JPEG EOF marker check)
    steganography_risk = "NONE"
    if suffix in [".jpg", ".jpeg"] and b"\xFF\xD9" in content_sample:
        # Find last JPEG End-of-Image marker (\xFF\xD9)
        eof_pos = content_sample.rfind(b"\xFF\xD9")
        appended_bytes = file_size - (eof_pos + 2)
        if appended_bytes > 256:
            steganography_risk = f"SUSPECTED ({appended_bytes} trailing bytes appended beyond JPEG EOF marker)"
            tamper_flags.append(f"Anomalous trailing payload ({appended_bytes} bytes) detected past standard EOF")

    # 5. JPEG Quantization Table (DQT) & Double-Compression Assessment
    dqt_count = content_sample.count(b"\xFF\xDB")
    double_compression_risk = "LOW"
    if dqt_count > 2:
        double_compression_risk = "ELEVATED (Multiple DQT quantization tables detected — indicative of re-saving/editing)"
        tamper_flags.append(f"Multiple JPEG DQT markers ({dqt_count}) found, signaling potential multiple re-compressions")

    # Flag AI generation risk
    is_ai_generated_metadata = len(ai_detected) > 0
    if is_ai_generated_metadata:
        tamper_flags.append(f"Direct AI generation markers embedded in bitstream ({', '.join(ai_detected)})")

    # Flag editing software risk
    if editors_detected:
        tamper_flags.append(f"Commercial graphic editing footprint detected ({', '.join(editors_detected)})")

    return {
        "valid_file": True,
        "file_size_bytes": file_size,
        "format_identified": format_identified,
        "magic_valid": magic_valid,
        "ai_generation_detected": is_ai_generated_metadata,
        "ai_tools": ai_detected,
        "editing_software_detected": editors_detected,
        "steganography_overlay_risk": steganography_risk,
        "double_compression_risk": double_compression_risk,
        "dqt_marker_count": dqt_count,
        "tamper_flags": tamper_flags,
        "integrity_status": "TAMPERED / MANIPULATED" if tamper_flags else "CLEAN BITSTREAM"
    }
