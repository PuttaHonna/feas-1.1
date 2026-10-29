"""
Forensic Evidence Analysis System (FEAS 2.0) - FastAPI Backend
Provides RESTful forensic endpoints for:
- Evidence intake, hashing, and vault preservation
- Image tampering detection
- CCTV video enhancement and object tracking
- Consented wound visual classification
- Toolmark similarity retrieval
- Append-only audit trail queries
- Factual PDF technical report generation
"""

import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.common.config import FORENSIC_CONFIG
from src.common.hashing import calculate_sha256
from src.common.file_validation import validate_file_integrity
from src.common.audit_db import AuditDatabase
from src.common.utils import preserve_original_evidence, create_working_copy
from src.common.report_generator import ForensicReportGenerator
from src.tampering.predict import TamperingPredictor
from src.cctv.pipeline import run_cctv_pipeline
from src.wound_research.predict import WoundResearchPredictor
from src.toolmark_research.retrieve import ToolmarkRetriever


app = FastAPI(
    title="Deep Learning Forensics Investigator API",
    version="2.0.0-experimental",
    description="A modular, verifiable, and responsible digital-forensics analysis engine.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

audit_db = AuditDatabase()
report_gen = ForensicReportGenerator()


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0-experimental",
        "vault_directory": str(FORENSIC_CONFIG.EVIDENCE_VAULT_DIR),
        "audit_database": str(FORENSIC_CONFIG.AUDIT_DB_PATH),
        "disclaimer": FORENSIC_CONFIG.MANDATORY_DISCLAIMER,
    }


@app.post("/api/v1/evidence/upload")
async def upload_evidence(file: UploadFile = File(...)):
    """
    Intake endpoint: validates file integrity, computes SHA-256, stores original read-only in vault,
    and produces a derived working copy for automated analysis.
    """
    temp_dir = FORENSIC_CONFIG.DATA_DIR / "temp_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / file.filename

    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1. Validation
    val_res = validate_file_integrity(temp_file)
    if not val_res.is_valid:
        if temp_file.exists():
            temp_file.unlink()
        raise HTTPException(status_code=400, detail=f"Evidence validation failed: {val_res.error_message}")

    # 2. Vault preservation & working copy
    evidence_id = f"EV_{val_res.sha256[:12]}"
    vault_path, orig_sha = preserve_original_evidence(temp_file, evidence_id=evidence_id)
    working_path, work_sha = create_working_copy(vault_path, evidence_id=evidence_id)

    # Clean up temp
    if temp_file.exists():
        temp_file.unlink()

    # 3. Register in SQLite
    registered_id = audit_db.register_evidence(
        original_filename=file.filename,
        original_sha256=orig_sha,
        working_copy_sha256=work_sha,
        file_type=val_res.file_type,
        file_size_bytes=val_res.file_size_bytes,
        original_path=str(vault_path),
        working_copy_path=str(working_path),
        metadata=val_res.metadata,
        evidence_id=evidence_id,
    )

    return {
        "evidence_id": registered_id,
        "original_filename": file.filename,
        "original_sha256": orig_sha,
        "working_copy_sha256": work_sha,
        "file_type": val_res.file_type,
        "metadata": val_res.metadata,
        "status": "preserved_read_only",
    }


@app.get("/api/v1/evidence/{evidence_id}/audit-trail")
def get_evidence_audit_trail(evidence_id: str):
    """Retrieve full chronological audit history for a given evidence ID."""
    runs = audit_db.get_run_history(evidence_id)
    all_events = []
    for r in runs:
        events = audit_db.get_audit_trail(r["run_id"])
        all_events.extend(events)

    return {
        "evidence_id": evidence_id,
        "runs": runs,
        "audit_events": all_events,
    }


@app.post("/api/v1/cctv/process")
def process_cctv(
    video_path: str = Form(...),
    conf_threshold: float = Form(0.35),
    duration_threshold_sec: float = Form(5.0),
    gamma: float = Form(1.0),
    enable_clahe: bool = Form(True),
    max_frames: Optional[int] = Form(None),
):
    """Process CCTV video with deterministic enhancement, COCO tracking, and event extraction."""
    src_p = Path(video_path)
    if not src_p.exists():
        raise HTTPException(status_code=404, detail="Target video file not found.")

    out_dir = FORENSIC_CONFIG.ARTIFACTS_DIR / f"cctv_{src_p.stem}"
    try:
        result = run_cctv_pipeline(
            video_path=src_p,
            output_dir=out_dir,
            conf_threshold=conf_threshold,
            duration_threshold_sec=duration_threshold_sec,
            gamma=gamma,
            enable_clahe=enable_clahe,
            max_frames_to_process=max_frames,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CCTV pipeline execution failed: {str(e)}")


@app.post("/api/v1/reports/generate")
def generate_technical_report(
    evidence_id: str = Form(...),
    case_id: str = Form("CASE_DEFAULT"),
    report_filename: Optional[str] = Form(None),
):
    """Generates verifiable factual technical PDF report strictly from recorded data."""
    with audit_db._get_connection() as conn:
        cur = conn.execute("SELECT * FROM evidence_ledger WHERE evidence_id = ?", (evidence_id,))
        ev_row = cur.fetchone()

    if not ev_row:
        raise HTTPException(status_code=404, detail="Evidence ID not found in ledger.")

    ev_dict = dict(ev_row)
    runs = audit_db.get_run_history(evidence_id)
    all_events = []
    for r in runs:
        all_events.extend(audit_db.get_audit_trail(r["run_id"]))

    out_pdf = FORENSIC_CONFIG.ARTIFACTS_DIR / (report_filename or f"forensic_report_{evidence_id}.pdf")

    # Aggregate module results from runs
    module_results = {}
    for r in runs:
        mod_name = r["module_name"]
        if "cctv" in mod_name:
            module_results["cctv"] = {
                "status": r["status"],
                "model_version": r.get("model_version", "yolov8n"),
                "metrics": json.loads(r.get("metrics_json") or "{}"),
            }
        elif "tampering" in mod_name:
            module_results["tampering"] = {
                "status": r["status"],
                "model_version": r.get("model_version", "resnet18"),
                "metrics": json.loads(r.get("metrics_json") or "{}"),
            }

    import json
    meta_json = json.loads(ev_dict.get("metadata_json") or "{}")

    pdf_path = report_gen.generate_pdf_report(
        output_path=out_pdf,
        case_id=case_id,
        evidence_id=evidence_id,
        original_filename=ev_dict["original_filename"],
        original_sha256=ev_dict["original_sha256"],
        working_copy_sha256=ev_dict.get("working_copy_sha256") or "N/A",
        timestamps_utc={"ingested_at": ev_dict["ingested_at_utc"]},
        actual_metadata=meta_json,
        module_results=module_results,
        audit_events=all_events,
    )

    pdf_hash = calculate_sha256(pdf_path)

    return {
        "status": "report_generated",
        "report_path": str(pdf_path),
        "report_sha256": pdf_hash,
        "evidence_id": evidence_id,
        "disclaimer": FORENSIC_CONFIG.MANDATORY_REPORT_FOOTER,
    }



@app.post("/api/v1/tampering/predict")
def predict_tampering(
    evidence_id: str = Form(...),
    model_name: str = Form("resnet18"),
):
    """Run tampering prediction on the working copy of registered evidence."""
    with audit_db._get_connection() as conn:
        cur = conn.execute("SELECT * FROM evidence_ledger WHERE evidence_id = ?", (evidence_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Evidence ID not found in ledger.")

    working_copy = Path(row["working_copy_path"])
    if not working_copy.exists():
        raise HTTPException(status_code=404, detail="Working copy not found on disk.")

    predictor = TamperingPredictor(model_name=model_name)
    pred_res = predictor.predict(working_copy)

    # Log processing run to audit DB
    run_id = audit_db.log_processing_run(
        evidence_id=evidence_id,
        module_name="tampering_detection",
        model_name=model_name,
        model_version="1.0-checkpoint",
        input_sha256=row["working_copy_sha256"],
        status="completed" if pred_res.quality_passed else "quality_warning",
        metrics={
            "predicted_label": pred_res.predicted_label,
            "prob_tampered": float(pred_res.probability_tampered),
            "confidence": float(pred_res.confidence),
            "is_uncertain": bool(pred_res.is_uncertain),
            "quality_metrics": pred_res.quality_metrics,
        },
    )

    return {
        "run_id": run_id,
        "evidence_id": evidence_id,
        "predicted_label": pred_res.predicted_label,
        "probability_tampered": pred_res.probability_tampered,
        "confidence": pred_res.confidence,
        "is_uncertain": pred_res.is_uncertain,
        "quality_passed": pred_res.quality_passed,
        "quality_metrics": pred_res.quality_metrics,
        "warning_message": pred_res.warning_message,
        "gradcam_available": pred_res.gradcam_path is not None,
        "disclaimer": FORENSIC_CONFIG.MANDATORY_DISCLAIMER,
    }


@app.post("/api/v1/wound/predict")
def predict_wound(
    evidence_id: str = Form(...),
    consent_acknowledged: bool = Form(...),
):
    """Run research-only wound classification on consented photographic evidence."""
    if not consent_acknowledged:
        raise HTTPException(status_code=403, detail="Ethical consent gate not acknowledged.")

    with audit_db._get_connection() as conn:
        cur = conn.execute("SELECT * FROM evidence_ledger WHERE evidence_id = ?", (evidence_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Evidence ID not found in ledger.")

    working_copy = Path(row["working_copy_path"])
    predictor = WoundResearchPredictor()
    pred_res = predictor.predict(working_copy, verified_consent=True)

    run_id = audit_db.log_processing_run(
        evidence_id=evidence_id,
        module_name="wound_classification_research",
        model_name="wound_resnet18_research",
        model_version="1.0-research",
        input_sha256=row["working_copy_sha256"],
        status="completed",
        metrics={
            "predicted_class": pred_res.predicted_class,
            "confidence": float(pred_res.confidence),
            "probabilities": pred_res.class_probabilities,
        },
    )

    return {
        "run_id": run_id,
        "evidence_id": evidence_id,
        "predicted_class": pred_res.predicted_class,
        "confidence": pred_res.confidence,
        "class_probabilities": pred_res.class_probabilities,
        "disclaimer": pred_res.disclaimer,
    }


@app.post("/api/v1/toolmark/retrieve")
def retrieve_toolmark(
    evidence_id: str = Form(...),
    top_k: int = Form(5),
):
    """Perform visual similarity retrieval against reference toolmark database."""
    with audit_db._get_connection() as conn:
        cur = conn.execute("SELECT * FROM evidence_ledger WHERE evidence_id = ?", (evidence_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Evidence ID not found in ledger.")

    working_copy = Path(row["working_copy_path"])
    retriever = ToolmarkRetriever()
    ret_res = retriever.retrieve(working_copy, top_k=top_k)

    run_id = audit_db.log_processing_run(
        evidence_id=evidence_id,
        module_name="toolmark_similarity_retrieval",
        model_name="toolmark_resnet18_encoder",
        model_version="1.0-research",
        input_sha256=row["working_copy_sha256"],
        status="completed" if ret_res.sufficient_reference_data else "insufficient_reference_data",
        metrics={
            "top_k": top_k,
            "matches_count": len(ret_res.matches),
            "sufficient_data": ret_res.sufficient_reference_data,
        },
    )

    return {
        "run_id": run_id,
        "evidence_id": evidence_id,
        "matches": [m.__dict__ for m in ret_res.matches],
        "examiner_review_notice": ret_res.examiner_review_notice,
        "sufficient_reference_data": ret_res.sufficient_reference_data,
        "disclaimer": FORENSIC_CONFIG.MANDATORY_DISCLAIMER,
    }


@app.post("/api/v1/analyze")
async def analyze_generic(
    file: UploadFile = File(...),
    investigator_name: str = Form("Forensic Examiner"),
    module: Optional[str] = Form(None),
):
    """
    Unified analysis endpoint for React dashboard:
    1. Validates integrity and records file SHA-256.
    2. Preserves evidence read-only in vault.
    3. Runs quality gating and active forensic inference.
    4. Logs to append-only audit trail and returns verified metadata.
    """
    import time
    start_time = time.time()

    temp_dir = FORENSIC_CONFIG.DATA_DIR / "temp_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / file.filename

    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    val_res = validate_file_integrity(temp_file)
    if not val_res.is_valid:
        if temp_file.exists():
            temp_file.unlink()
        raise HTTPException(status_code=400, detail=f"Validation error: {val_res.error_message}")

    evidence_id = f"EV_{val_res.sha256[:12]}"
    vault_path, orig_sha = preserve_original_evidence(temp_file, evidence_id=evidence_id)
    working_path, work_sha = create_working_copy(vault_path, evidence_id=evidence_id)

    if temp_file.exists():
        temp_file.unlink()

    registered_id = audit_db.register_evidence(
        original_filename=file.filename,
        original_sha256=orig_sha,
        working_copy_sha256=work_sha,
        file_type=val_res.file_type,
        file_size_bytes=val_res.file_size_bytes,
        original_path=str(vault_path),
        working_copy_path=str(working_path),
        metadata=val_res.metadata,
        evidence_id=evidence_id,
    )

    verdict = "PRESERVED & REGISTERED"
    quality_passed = True
    details = {}

    if val_res.file_type.startswith("image/"):
        predictor = TamperingPredictor()
        pred_res = predictor.predict(working_path)
        verdict = f"ANALYSIS COMPLETE: {pred_res.predicted_label.upper()}"
        quality_passed = pred_res.quality_passed
        details = {
            "prediction": pred_res.predicted_label,
            "probability_tampered": pred_res.probability_tampered,
            "confidence": pred_res.confidence,
            "is_uncertain": pred_res.is_uncertain,
            "quality_metrics": pred_res.quality_metrics,
            "warning": pred_res.warning_message,
        }
        status_str = "completed" if pred_res.quality_passed else "quality_warning"
    else:
        status_str = "intake_verified"
        verdict = "EVIDENCE INTAKE VERIFIED"

    run_id = audit_db.log_processing_run(
        evidence_id=registered_id,
        module_name="unified_forensic_intake",
        model_name="feas2_intake",
        model_version="2.0",
        input_sha256=orig_sha,
        status=status_str,
        metrics=details,
    )

    elapsed = round(time.time() - start_time, 3)

    return {
        "status": "success",
        "case_id": f"CASE-{registered_id}",
        "evidence_id": registered_id,
        "input_sha256": orig_sha,
        "working_sha256": work_sha,
        "file_type": val_res.file_type,
        "file_size_bytes": val_res.file_size_bytes,
        "verdict": verdict,
        "quality_passed": quality_passed,
        "elapsed_seconds": elapsed,
        "details": details,
        "run_id": run_id,
        "disclaimer": FORENSIC_CONFIG.MANDATORY_DISCLAIMER,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=True)

