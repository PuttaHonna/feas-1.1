"""
Forensic Evidence Analysis System (FEAS) - Async Analysis Orchestrator
Executes Forgery, Deepfake, Audio, Face, Wound, and Ballistics engines concurrently with 12s timeout enforcement.
"""

import asyncio
import concurrent.futures
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union
from PIL import Image

from src.config import EXECUTION_TIMEOUT_SECONDS, TEMP_DIR
from src.db.audit import log_audit_event_sync, update_case_results_sync
from src.pipeline.advanced_metadata import inspect_advanced_binary_metadata
from src.pipeline.ingestion import compute_sha256_file

# Pre-import torchvision to eliminate thread-level circular import on Windows/Linux
try:
    import torchvision
    from torchvision.transforms import InterpolationMode
except Exception:
    pass

# Thread pool for CPU/GPU bound model execution (2 workers to conserve RAM on cloud instances)
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

def _run_forgery_lazy(img, out_dir):
    from src.models.forgery.pipeline import run_forgery_check
    return run_forgery_check(img, out_dir)

def _run_face_lazy(img, out_dir):
    from src.models.face.pipeline import process_face
    return process_face(img, out_dir)

def _run_wound_lazy(img, out_dir):
    from src.models.wound.efficientnet_triage import predict_wound
    return predict_wound(img, out_dir)

def _run_ballistics_lazy(img, out_dir):
    from src.models.ballistics.striae_cnn import analyze_striae
    return analyze_striae(img, out_dir)

def _run_deepfake_lazy(img, out_dir):
    from src.models.deepfake.detector import detect_deepfake
    return detect_deepfake(img, out_dir)

def _run_audio_lazy(src_path, out_dir):
    from src.models.audio.voice_forensics import analyze_audio_forensics
    return analyze_audio_forensics(src_path, out_dir)


def _compute_overall_verdict(
    forgery_res: Dict[str, Any],
    face_res: Dict[str, Any],
    wound_res: Dict[str, Any],
    ballistics_res: Dict[str, Any],
    deepfake_res: Optional[Dict[str, Any]] = None,
    audio_res: Optional[Dict[str, Any]] = None,
    adv_meta: Optional[Dict[str, Any]] = None
) -> str:
    """Derive an authoritative forensic verdict reflecting genuine detected evidence."""
    verdicts = []
    deepfake_res = deepfake_res or {}
    audio_res = audio_res or {}
    adv_meta = adv_meta or {}
    
    # 1. AI Deepfake & Synthetic Media verdict
    if deepfake_res.get("is_deepfake"):
        verdicts.append(f"AI SYNTHETIC MEDIA DETECTED ({deepfake_res.get('model_attribution')}, Probability: {deepfake_res.get('deepfake_score', 0)*100:.1f}%)")

    # 2. Audio & Voice Authenticity verdict
    if audio_res.get("has_audio") and audio_res.get("is_synthetic_voice"):
        verdicts.append(f"SYNTHETIC VOICE CLONE DETECTED (Voice Index: {audio_res.get('synthetic_voice_score', 0)*100:.1f}%)")

    # 3. Tampering / Integrity verdict
    if forgery_res.get("is_tampered"):
        verdicts.append(f"DIGITAL TAMPERING DETECTED (Tamper Index: {forgery_res.get('tamper_score', 0)*100:.1f}%)")
    elif not deepfake_res.get("is_deepfake") and not (audio_res.get("has_audio") and audio_res.get("is_synthetic_voice")):
        verdicts.append("MEDIA AUTHENTIC (Integrity Verified — No Tampering Detected)")

    # 4. Suspect identification (ONLY if face was actually detected and matched with high confidence)
    if face_res.get("face_detected"):
        top_match = face_res.get("top_match")
        if top_match and top_match.get("similarity", 0) >= 0.65:
            verdicts.append(f"SUSPECT MATCH: {top_match['name']} ({top_match['similarity']*100:.1f}%)")
        else:
            verdicts.append("FACIAL SUBJECT IDENTIFIED (No Prior Gallery Match)")

    # 5. Wound / Clinical assessment (ONLY if biological trauma is present)
    if wound_res.get("wound_detected"):
        verdicts.append(f"CLINICAL TRAUMA: {wound_res.get('wound_type', '').upper()} ({wound_res.get('severity', '').upper()})")

    # 6. Ballistics match (ONLY if ballistic micro-striations are present)
    if ballistics_res.get("striae_detected"):
        verdicts.append(f"BALLISTICS: {ballistics_res.get('caliber')} {ballistics_res.get('rifling')} ({ballistics_res.get('manufacturer')})")

    # 7. Metadata provenance flags (if AI tool tags present)
    if adv_meta.get("ai_tools"):
        verdicts.append(f"PROVENANCE: Embedded {', '.join(adv_meta['ai_tools'])}")

    return " | ".join(verdicts)


async def run_parallel_forensic_analysis(
    case_id: str,
    media_info: Dict[str, Any],
    operator_notes: str = ""
) -> Dict[str, Any]:
    """
    Run forensic models concurrently with a strict 12.0s timeout.
    Updates SQLite case status and records detailed audit events.
    """
    primary_image = media_info.get("primary_image_path", media_info.get("stored_path"))
    source_media_path = media_info.get("stored_path", primary_image)
    case_dir = TEMP_DIR / "cases" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    loop = asyncio.get_running_loop()
    start_time = time.time()

    # Define tasks for each forensic module (lazy runners)
    task_forgery = loop.run_in_executor(_executor, _run_forgery_lazy, primary_image, case_dir / "forgery")
    task_face = loop.run_in_executor(_executor, _run_face_lazy, primary_image, case_dir / "face")
    task_wound = loop.run_in_executor(_executor, _run_wound_lazy, primary_image, case_dir / "wound")
    task_ballistics = loop.run_in_executor(_executor, _run_ballistics_lazy, primary_image, case_dir / "ballistics")
    task_deepfake = loop.run_in_executor(_executor, _run_deepfake_lazy, primary_image, case_dir / "deepfake")
    task_audio = loop.run_in_executor(_executor, _run_audio_lazy, source_media_path, case_dir / "audio")

    try:
        # Execute all 6 engines concurrently with 12s timeout
        forgery_res, face_res, wound_res, ballistics_res, deepfake_res, audio_res = await asyncio.wait_for(
            asyncio.gather(task_forgery, task_face, task_wound, task_ballistics, task_deepfake, task_audio, return_exceptions=False),
            timeout=EXECUTION_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        forgery_res = {"tamper_score": 0.0, "is_tampered": False, "bboxes": [], "error": "Execution Timed Out"}
        face_res = {"face_detected": False, "matches": [], "error": "Execution Timed Out"}
        wound_res = {"wound_detected": False, "error": "Execution Timed Out"}
        ballistics_res = {"striae_detected": False, "error": "Execution Timed Out"}
        deepfake_res = {"is_deepfake": False, "deepfake_score": 0.0, "model_attribution": "Timeout", "error": "Execution Timed Out"}
        audio_res = {"has_audio": False, "is_synthetic_voice": False, "synthetic_voice_score": 0.0, "error": "Execution Timed Out"}

    elapsed_time = round(time.time() - start_time, 3)

    if "restored_img" in face_res:
        del face_res["restored_img"]

    # Advanced metadata inspection
    adv_meta = media_info.get("advanced_metadata")
    if not adv_meta and source_media_path:
        adv_meta = inspect_advanced_binary_metadata(source_media_path)

    # Compute overall forensic verdict reflecting true detections
    verdict = _compute_overall_verdict(
        forgery_res, face_res, wound_res, ballistics_res, deepfake_res, audio_res, adv_meta
    )

    confidence_matrix = {
        "tamper_confidence": forgery_res.get("tamper_score", 0.0),
        "deepfake_confidence": deepfake_res.get("deepfake_score", 0.0),
        "synthetic_voice_confidence": audio_res.get("synthetic_voice_score", 0.0) if audio_res.get("has_audio") else 0.0,
        "face_match_confidence": face_res.get("top_match", {}).get("similarity", 0.0) if face_res.get("top_match") else 0.0,
        "wound_confidence": wound_res.get("wound_type_confidence", 0.0) if wound_res.get("wound_detected") else 0.0,
        "ballistics_confidence": ballistics_res.get("caliber_confidence", 0.0) if ballistics_res.get("striae_detected") else 0.0,
        "elapsed_seconds": elapsed_time
    }

    summary = {
        "case_id": case_id,
        "status": "COMPLETED",
        "filename": media_info.get("filename"),
        "file_type": media_info.get("file_type"),
        "input_sha256": media_info.get("input_sha256"),
        "metadata": media_info.get("metadata", {}),
        "advanced_metadata": adv_meta,
        "is_video": media_info.get("is_video", False),
        "keyframes": media_info.get("keyframes", []),
        "primary_image_path": primary_image,
        "forgery": forgery_res,
        "deepfake": deepfake_res,
        "audio": audio_res,
        "face": face_res,
        "wound": wound_res,
        "ballistics": ballistics_res,
        "verdict": verdict,
        "confidence_scores": confidence_matrix,
        "elapsed_seconds": elapsed_time
    }

    # Record completion in SQLite audit database
    log_audit_event_sync(
        case_id=case_id,
        action="PARALLEL_ANALYSIS_COMPLETED",
        input_sha256=media_info.get("input_sha256"),
        exif_data=media_info.get("metadata"),
        confidence_scores=confidence_matrix,
        details={"elapsed_seconds": elapsed_time, "verdict": verdict},
        operator_notes=operator_notes
    )

    update_case_results_sync(
        case_id=case_id,
        status="COMPLETED",
        verdict=verdict,
        summary=summary
    )

    return summary


async def run_batch_forensic_analysis(
    batch_id: str,
    file_items: list,
    investigator_name: str = "Forensic Examiner",
    operator_notes: str = ""
) -> Dict[str, Any]:
    """
    Execute batch forensic triage across multiple evidence files.
    Processes items concurrently, logs audit trails, and produces consolidated summary metrics.
    """
    from src.db.audit import create_case_sync
    from src.pipeline.ingestion import process_uploaded_media
    from datetime import datetime, timezone

    start_time = time.time()
    batch_results = []
    
    # Process files with worker semaphore to avoid memory pressure
    semaphore = asyncio.Semaphore(2)

    async def _process_single(item):
        async with semaphore:
            fn = item.get("filename", "evidence.jpg")
            fb = item.get("file_bytes")
            
            if fb is not None:
                media_info = process_uploaded_media(fb, fn)
            elif "media_info" in item:
                media_info = item["media_info"]
            else:
                raise ValueError("Either file_bytes or media_info must be provided for batch item.")

            case_id = create_case_sync(
                filename=fn,
                file_type=media_info.get("file_type", "UNKNOWN"),
                input_sha256=media_info.get("input_sha256", "UNKNOWN"),
                investigator_name=investigator_name,
                operator_notes=f"Batch {batch_id}: {operator_notes}"
            )
            
            res = await run_parallel_forensic_analysis(case_id, media_info, operator_notes)
            return res

    tasks = [_process_single(item) for item in file_items]
    batch_results = await asyncio.gather(*tasks, return_exceptions=False)
    
    total_files = len(batch_results)
    tampered_count = sum(1 for r in batch_results if (r.get("forgery") or {}).get("is_tampered"))
    deepfake_count = sum(1 for r in batch_results if (r.get("deepfake") or {}).get("is_deepfake"))
    synthetic_voice_count = sum(1 for r in batch_results if (r.get("audio") or {}).get("is_synthetic_voice"))
    suspect_hits_count = sum(1 for r in batch_results if (r.get("face") or {}).get("face_detected") and ((r.get("face") or {}).get("top_match") or {}).get("similarity", 0) >= 0.65)
    wound_alerts_count = sum(1 for r in batch_results if (r.get("wound") or {}).get("wound_detected"))
    ballistics_alerts_count = sum(1 for r in batch_results if (r.get("ballistics") or {}).get("striae_detected"))
    total_elapsed = round(time.time() - start_time, 3)

    summary_metrics = {
        "total_files": total_files,
        "tampered_count": tampered_count,
        "tamper_rate": round(tampered_count / total_files, 3) if total_files > 0 else 0.0,
        "deepfake_count": deepfake_count,
        "synthetic_voice_count": synthetic_voice_count,
        "suspect_hits_count": suspect_hits_count,
        "wound_alerts_count": wound_alerts_count,
        "ballistics_alerts_count": ballistics_alerts_count,
        "total_elapsed_seconds": total_elapsed,
        "average_seconds_per_file": round(total_elapsed / total_files, 3) if total_files > 0 else 0.0
    }

    return {
        "batch_id": batch_id,
        "investigator_name": investigator_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary_metrics,
        "items": batch_results
    }
