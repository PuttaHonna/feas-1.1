"""
Forensic Evidence Analysis System (FEAS) - FastAPI Route Handlers
Exposes endpoints for evidence analysis, batch processing, case retrieval, PDF reports, suspect management, and health checks.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
import torch

from src.api.orchestrator import run_batch_forensic_analysis, run_parallel_forensic_analysis
from src.config import DEVICE, REPORTS_DIR, STORAGE_DIR, TEMP_DIR
from src.db.audit import (
    create_case_sync,
    get_audit_trail_sync,
    get_case_sync,
    get_suspect_profiles_sync,
    list_cases_sync,
    log_audit_event_sync
)
from src.models.audio.voice_forensics import analyze_audio_forensics
from src.models.deepfake.detector import detect_deepfake
from src.pipeline.advanced_metadata import inspect_advanced_binary_metadata
from src.pipeline.ingestion import process_uploaded_media
from src.reports.batch_report import build_batch_pdf
from src.reports.pdf_generator import build_pdf

router = APIRouter(prefix="/api/v1")


@router.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint returning system & device telemetry."""
    return {
        "status": "HEALTHY",
        "device": str(DEVICE),
        "cuda_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A",
        "storage_ready": STORAGE_DIR.exists(),
        "reports_ready": REPORTS_DIR.exists()
    }


@router.post("/analyze", tags=["Evidence Analysis"])
async def analyze_evidence(
    file: UploadFile = File(...),
    investigator_name: str = Form("Forensic Analyst"),
    operator_notes: str = Form("")
) -> Dict[str, Any]:
    """
    Ingest and analyze single multimedia evidence across all 4 forensic engines in parallel.
    Enforces <= 12s execution timeout, logs immutable SQLite audit trails, and returns full case analysis.
    """
    try:
        content = await file.read()
        filename = file.filename or "evidence_file.jpg"
        
        # 1. Ingestion & Preprocessing
        media_info = process_uploaded_media(content, filename)
        input_sha256 = media_info["input_sha256"]
        file_type = media_info["file_type"]

        # 2. Create Case Record
        case_id = create_case_sync(
            filename=filename,
            file_type=file_type,
            input_sha256=input_sha256,
            investigator_name=investigator_name,
            operator_notes=operator_notes
        )

        # 3. Parallel Forensic Analysis
        summary = await run_parallel_forensic_analysis(
            case_id=case_id,
            media_info=media_info,
            operator_notes=operator_notes
        )

        summary["investigator_name"] = investigator_name
        summary["operator_notes"] = operator_notes

        return summary

    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis pipeline error: {str(e)}")


@router.post("/analyze/batch", tags=["Batch Evidence Analysis"])
async def analyze_evidence_batch(
    files: List[UploadFile] = File(...),
    investigator_name: str = Form("Forensic Analyst"),
    operator_notes: str = Form("")
) -> Dict[str, Any]:
    """
    Ingest and analyze multiple evidence files in batch mode.
    Runs forensic models concurrently, records individual audit trails, and returns consolidated triage statistics.
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded for batch processing.")

    batch_id = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
    file_items = []

    for f in files:
        content = await f.read()
        file_items.append({
            "filename": f.filename or "evidence.jpg",
            "file_bytes": content
        })

    batch_results = await run_batch_forensic_analysis(
        batch_id=batch_id,
        file_items=file_items,
        investigator_name=investigator_name,
        operator_notes=operator_notes
    )

    # Cache batch result for PDF generation
    batch_dir = TEMP_DIR / "batches"
    batch_dir.mkdir(parents=True, exist_ok=True)
    with open(batch_dir / f"{batch_id}.json", "w", encoding="utf-8") as bf:
        json.dump(batch_results, bf, default=str)

    # Pre-generate batch PDF
    pdf_res = build_batch_pdf(batch_results)
    batch_results["pdf_path"] = pdf_res["pdf_path"]
    batch_results["pdf_sha256"] = pdf_res["pdf_sha256"]

    return batch_results


@router.get("/cases", tags=["Cases"])
async def list_cases(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve list of recent forensic cases."""
    return list_cases_sync(limit=limit)


@router.get("/cases/{case_id}", tags=["Cases"])
async def get_case(case_id: str) -> Dict[str, Any]:
    """Retrieve full case details and audit history."""
    case = get_case_sync(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")
    
    audit_trail = get_audit_trail_sync(case_id)
    case["audit_trail"] = audit_trail
    return case


@router.get("/cases/{case_id}/report", tags=["Reports"])
async def get_case_report(case_id: str) -> FileResponse:
    """
    Generate or retrieve court-ready ReportLab PDF report for a case.
    Streams PDF file directly with SHA-256 validation.
    """
    case = get_case_sync(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    report_pdf = REPORTS_DIR / f"FEAS_Report_{case_id}.pdf"
    
    # Generate report if not already cached
    if not report_pdf.exists():
        summary = case.get("summary") or {}
        if not summary:
            summary = {
                "case_id": case_id,
                "created_at": case.get("created_at"),
                "investigator_name": case.get("investigator_name", "Forensic Analyst"),
                "filename": case.get("filename", "evidence"),
                "file_type": case.get("file_type", "image"),
                "input_sha256": case.get("input_sha256", "N/A"),
                "verdict": case.get("verdict", "PENDING REVIEW"),
                "operator_notes": case.get("operator_notes", ""),
                "metadata": {},
                "forgery": {"tamper_score": 0.0, "is_tampered": False, "bboxes": []},
                "face": {"matches": []},
                "wound": {"wound_type": "N/A", "severity": "N/A", "age": "N/A", "location": "N/A"},
                "ballistics": {"caliber": "N/A", "rifling": "N/A", "manufacturer": "N/A"}
            }
        summary["audit_trail"] = get_audit_trail_sync(case_id)
        build_pdf(summary, str(report_pdf))

    return FileResponse(
        path=str(report_pdf),
        filename=f"FEAS_Court_Report_{case_id}.pdf",
        media_type="application/pdf"
    )


@router.get("/batch/{batch_id}/report", tags=["Reports"])
async def get_batch_report(batch_id: str) -> FileResponse:
    """
    Generate or retrieve consolidated court-ready ReportLab PDF triage report for a batch.
    """
    report_pdf = REPORTS_DIR / f"FEAS_Batch_Triage_{batch_id}.pdf"
    
    if not report_pdf.exists():
        batch_file = TEMP_DIR / "batches" / f"{batch_id}.json"
        if not batch_file.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch '{batch_id}' not found.")
        
        with open(batch_file, "r", encoding="utf-8") as bf:
            batch_data = json.load(bf)
        
        build_batch_pdf(batch_data, str(report_pdf))

    return FileResponse(
        path=str(report_pdf),
        filename=f"FEAS_Batch_Triage_{batch_id}.pdf",
        media_type="application/pdf"
    )


@router.get("/suspects", tags=["Suspects"])
async def list_suspects() -> List[Dict[str, Any]]:
    """Retrieve suspect profiles gallery."""
    return get_suspect_profiles_sync()


@router.post("/analyze/deepfake", tags=["Specialized Engines"])
async def analyze_deepfake_endpoint(
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Dedicated endpoint for AI Deepfake & Synthetic Media Detection.
    Returns 2D FFT spectral metrics, boundary gradients, and model attribution.
    """
    try:
        content = await file.read()
        media_info = process_uploaded_media(content, file.filename or "image.jpg")
        primary_image = media_info.get("primary_image_path", media_info.get("stored_path"))
        
        case_id = f"DF-{uuid.uuid4().hex[:8].upper()}"
        out_dir = TEMP_DIR / "cases" / case_id / "deepfake"
        return detect_deepfake(primary_image, out_dir)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Deepfake analysis failed: {str(e)}")


@router.post("/analyze/audio", tags=["Specialized Engines"])
async def analyze_audio_endpoint(
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Dedicated endpoint for Acoustic & Voice Authenticity Forensics.
    Returns STFT spectrogram, SNR, pitch jitter, and synthetic vocoder detection.
    """
    try:
        content = await file.read()
        media_info = process_uploaded_media(content, file.filename or "media.mp4")
        source_path = media_info.get("stored_path")
        
        case_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
        out_dir = TEMP_DIR / "cases" / case_id / "audio"
        return analyze_audio_forensics(source_path, out_dir)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Audio analysis failed: {str(e)}")


@router.post("/analyze/metadata", tags=["Specialized Engines"])
async def analyze_metadata_endpoint(
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Dedicated endpoint for Advanced Hex Bitstream & Provenance Metadata Inspection.
    Scans for AI tool markers, editing suites, magic bytes, and JPEG quantization table anomalies.
    """
    try:
        content = await file.read()
        media_info = process_uploaded_media(content, file.filename or "evidence.jpg")
        source_path = media_info.get("stored_path")
        return inspect_advanced_binary_metadata(source_path)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Metadata analysis failed: {str(e)}")


@router.post("/cctv/analyze", tags=["CCTV Surveillance Engine"])
async def analyze_cctv_endpoint(
    file: UploadFile = File(...),
    case_id: str = Form("CASE-2026-001"),
    evidence_id: str = Form("EV-CCTV-001"),
    camera_id: str = Form("CAM-01"),
    camera_location: str = Form("Main Gate"),
    analysis_mode: str = Form("fast_review"),
    enhancement_mode: str = Form("basic"),
    confidence_threshold: float = Form(0.40)
) -> Dict[str, Any]:
    """
    Dedicated endpoint for CCTV Video Analysis:
    Deterministic Enhancement, YOLOv8 Object Detection, Multi-Object Tracking,
    Event Extraction, and Cryptographic Evidence Hashing.
    """
    try:
        content = await file.read()
        import tempfile
        suffix = Path(file.filename or "cctv.mp4").suffix or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        from src.cctv_pipeline import run_cctv_analysis
        res = run_cctv_analysis(
            input_video_path=tmp_path,
            case_id=case_id,
            evidence_id=evidence_id,
            camera_id=camera_id,
            camera_location=camera_location,
            analysis_mode=analysis_mode,
            enhancement_mode=enhancement_mode,
            confidence_threshold=confidence_threshold
        )
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        return res
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"CCTV analysis failed: {str(e)}")

