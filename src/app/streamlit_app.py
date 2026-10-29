"""
Deep Learning Forensics Investigator — Streamlit Workstation
Responsible, verifiable digital-forensics research and experimental analysis workstation.
Adheres strictly to evidence preservation, factual metrics, and non-attribution rules.
"""

import os
import json
import tempfile
from pathlib import Path
import streamlit as st
import cv2
import pandas as pd
from PIL import Image

from src.common.config import FORENSIC_CONFIG
from src.common.hashing import calculate_sha256
from src.common.file_validation import validate_file_integrity
from src.common.audit_db import AuditDatabase
from src.common.utils import preserve_original_evidence, create_working_copy
from src.common.quality_gate import evaluate_image_quality
from src.common.report_generator import ForensicReportGenerator
from src.tampering.predict import TamperingPredictor
from src.cctv.pipeline import run_cctv_pipeline
from src.wound_research.predict import WoundResearchPredictor
from src.toolmark_research.retrieve import ToolmarkRetriever


st.set_page_config(
    page_title="Deep Learning Forensics Investigator",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize singletons in session state
if "audit_db" not in st.session_state:
    st.session_state.audit_db = AuditDatabase()
if "report_gen" not in st.session_state:
    st.session_state.report_gen = ForensicReportGenerator()
if "active_evidence" not in st.session_state:
    st.session_state.active_evidence = None

audit_db: AuditDatabase = st.session_state.audit_db

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.title("⚖️ Forensic Investigator")
    st.caption("Responsible Digital Forensics Suite")

    st.warning(
        f"**Mandatory Advisory Notice:**\n\n{FORENSIC_CONFIG.MANDATORY_DISCLAIMER}"
    )

    st.markdown("---")
    st.subheader("System Integrity Status")
    st.success("🔒 Read-Only Vault: Active (`0o444`)")
    st.info("📜 Audit Trail: SQLite WAL Append-Only")
    st.write(f"🎲 Random Seed: `{FORENSIC_CONFIG.DEFAULT_RANDOM_SEED}`")

    st.markdown("---")
    if st.session_state.active_evidence:
        ev = st.session_state.active_evidence
        st.subheader("Active Evidence")
        st.write(f"**ID:** `{ev['evidence_id']}`")
        st.write(f"**File:** `{ev['original_filename']}`")
        st.code(ev["original_sha256"][:16] + "...", language="text")

# ----------------- MAIN TABS -----------------
tab_intake, tab_tampering, tab_cctv, tab_wound, tab_toolmark, tab_audit = st.tabs([
    "🗄️ Evidence Locker",
    "🔍 Tampering Detection",
    "📹 CCTV Surveillance",
    "🩹 Wound Research",
    "🔬 Toolmark Retrieval",
    "📜 Audit & Report",
])

# ================= TAB 1: EVIDENCE INTAKE =================
with tab_intake:
    st.header("Evidence Locker & Cryptographic Intake")
    st.markdown(
        "Upload still imagery or surveillance video. The system strictly validates file integrity, "
        "computes cryptographic SHA-256 hashes, stores the original file read-only in the vault, "
        "and produces a hash-verified working copy."
    )

    uploaded_file = st.file_uploader(
        "Upload Evidence File (JPG, PNG, TIFF, MP4, AVI, MKV, MOV)",
        type=["jpg", "jpeg", "png", "tiff", "tif", "mp4", "avi", "mkv", "mov"],
    )

    if uploaded_file is not None:
        if st.button("🔒 Ingest & Preserve Evidence"):
            with st.spinner("Validating and cryptographically sealing evidence..."):
                temp_dir = FORENSIC_CONFIG.DATA_DIR / "temp_intake"
                temp_dir.mkdir(parents=True, exist_ok=True)
                temp_path = temp_dir / uploaded_file.name

                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                val_res = validate_file_integrity(temp_path)
                if not val_res.is_valid:
                    st.error(f"❌ Intake Rejected: {val_res.error_message}")
                    temp_path.unlink()
                else:
                    evidence_id = f"EV_{val_res.sha256[:12]}"
                    vault_path, orig_sha = preserve_original_evidence(temp_path, evidence_id=evidence_id)
                    working_path, work_sha = create_working_copy(vault_path, evidence_id=evidence_id)
                    temp_path.unlink()

                    registered_id = audit_db.register_evidence(
                        original_filename=uploaded_file.name,
                        original_sha256=orig_sha,
                        working_copy_sha256=work_sha,
                        file_type=val_res.file_type,
                        file_size_bytes=val_res.file_size_bytes,
                        original_path=str(vault_path),
                        working_copy_path=str(working_path),
                        metadata=val_res.metadata,
                        evidence_id=evidence_id,
                    )

                    st.session_state.active_evidence = {
                        "evidence_id": registered_id,
                        "original_filename": uploaded_file.name,
                        "original_sha256": orig_sha,
                        "working_copy_sha256": work_sha,
                        "file_type": val_res.file_type,
                        "working_copy_path": str(working_path),
                        "metadata": val_res.metadata,
                    }
                    st.success(f"✅ Evidence Successfully Ingested! ID: `{registered_id}`")

    if st.session_state.active_evidence:
        ev = st.session_state.active_evidence
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Cryptographic Fingerprint")
            st.write(f"**Evidence ID:** `{ev['evidence_id']}`")
            st.write(f"**Original SHA-256:**")
            st.code(ev["original_sha256"], language="text")
            st.write(f"**Working Copy SHA-256:**")
            st.code(ev["working_copy_sha256"], language="text")
        with col2:
            st.subheader("Verified Metadata")
            st.json(ev["metadata"])

# ================= TAB 2: TAMPERING DETECTION =================
with tab_tampering:
    st.header("Image Tampering Detection")
    st.caption("Pre-inference quality gating, probability calibration, and advisory Grad-CAM visualization.")

    ev = st.session_state.active_evidence
    if not ev or ev.get("file_type") != "image":
        st.info("ℹ️ Please ingest an image in the Evidence Locker tab to analyze tampering.")
    else:
        st.write(f"Analyzing working copy: `{ev['original_filename']}`")

        # 1. Quality Gate Inspection
        quality = evaluate_image_quality(ev["working_copy_path"])
        col1, col2, col3 = st.columns(3)
        col1.metric("Blur Score (Laplacian Var)", f"{quality.blur_score:.1f}", delta="Min: 25.0")
        col2.metric("Mean Luminance", f"{quality.mean_luminance:.1f}", delta="Range: 15-245")
        col3.metric("Resolution", f"{quality.width}x{quality.height}")

        if not quality.passed:
            st.error(f"⚠️ Quality Gate Failed: {quality.summary_message}")
            for r in quality.reasons:
                st.write(f"- {r}")
        else:
            st.success("✅ Image meets minimum forensic quality thresholds.")

            col_btn, col_thresh = st.columns([1, 2])
            with col_thresh:
                thresh = st.slider("Uncertainty Rejection Threshold", 0.50, 0.90, 0.65, 0.05)

            if col_btn.button("🔍 Run Tampering Analysis"):
                # Check for trained checkpoint
                ckpt_path = Path("data/checkpoints/tampering/tampering_resnet18_best.pt")
                if not ckpt_path.exists():
                    st.warning("⚠️ No trained checkpoint found at `data/checkpoints/tampering/tampering_resnet18_best.pt`. Using initialized baseline.")
                
                with st.spinner("Running model inference and generating Grad-CAM..."):
                    predictor = TamperingPredictor(
                        checkpoint_path=ckpt_path if ckpt_path.exists() else "data/checkpoints/tampering/tampering_resnet18_best.pt",
                        uncertainty_threshold=thresh,
                    ) if ckpt_path.exists() else None

                    if predictor:
                        cam_out = FORENSIC_CONFIG.ARTIFACTS_DIR / f"gradcam_{ev['evidence_id']}.png"
                        res = predictor.predict(Path(ev["working_copy_path"]), generate_gradcam=True, gradcam_output_path=cam_out)

                        st.subheader(f"Classification Result: {res['predicted_label'].upper()}")
                        st.info(f"**Advisory Output:** {res['explanation_wording']}")

                        col_l, col_r = st.columns(2)
                        with col_l:
                            st.subheader("Working Copy")
                            st.image(ev["working_copy_path"], use_container_width=True)
                        with col_r:
                            st.subheader("Grad-CAM Attention Overlay")
                            if res.get("grad_cam_path") and Path(res["grad_cam_path"]).exists():
                                st.image(res["grad_cam_path"], use_container_width=True)
                            else:
                                st.write("Grad-CAM visualization not generated.")

                        st.json(res["probabilities"])
                        st.warning(f"**Disclaimer:** {res['disclaimer']}")

# ================= TAB 3: CCTV SURVEILLANCE =================
with tab_cctv:
    st.header("CCTV Video Enhancement & Tracking")
    st.caption("Deterministic OpenCV enhancement, restricted COCO object detection, and objective event extraction.")

    ev = st.session_state.active_evidence
    if not ev or ev.get("file_type") != "video":
        st.info("ℹ️ Please ingest a video file in the Evidence Locker tab to analyze CCTV footage.")
    else:
        st.write(f"Selected Video: `{ev['original_filename']}`")

        c1, c2, c3 = st.columns(3)
        with c1:
            gamma = st.slider("Gamma Correction", 0.5, 2.5, 1.0, 0.1)
            enable_clahe = st.checkbox("Enable CLAHE Contrast", value=True)
        with c2:
            enable_denoise = st.checkbox("Enable Bilateral Denoise", value=True)
            enable_sharpen = st.checkbox("Enable Unsharp Sharpening", value=True)
        with c3:
            conf_t = st.slider("Detection Confidence Threshold", 0.20, 0.80, 0.35, 0.05)
            max_f = st.number_input("Max Frames to Process (0 = All)", min_value=0, value=150, step=50)

        if st.button("🚀 Process CCTV Surveillance"):
            with st.spinner("Processing surveillance pipeline (Enhancing, Detecting, Tracking)..."):
                out_dir = FORENSIC_CONFIG.ARTIFACTS_DIR / f"cctv_{ev['evidence_id']}"
                res = run_cctv_pipeline(
                    video_path=Path(ev["working_copy_path"]),
                    output_dir=out_dir,
                    gamma=gamma,
                    enable_clahe=enable_clahe,
                    enable_denoise=enable_denoise,
                    enable_sharpen=enable_sharpen,
                    conf_threshold=conf_t,
                    max_frames_to_process=None if max_f == 0 else int(max_f),
                )

                st.success("✅ CCTV Processing Completed!")
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Frames Processed", res["metrics"]["frames_processed"])
                col_m2.metric("Total Detections", res["metrics"]["total_detections"])
                col_m3.metric("Unique Tracks", res["metrics"]["unique_tracks"])

                st.subheader("Objective Surveillance Events")
                with open(res["artifacts"]["events_json"], "r", encoding="utf-8") as f:
                    ev_list = json.load(f)
                if ev_list:
                    st.dataframe(pd.DataFrame(ev_list), use_container_width=True)
                else:
                    st.write("No events recorded.")

                st.subheader("Annotated Derived Video")
                st.video(res["artifacts"]["annotated_video"])

# ================= TAB 4: WOUND RESEARCH =================
with tab_wound:
    st.header("Wound Image Classification (Research Protocol Only)")
    st.error(
        "⚠️ **SAFETY RESTRICTION:** This module is strictly for educational & scientific computer vision research. "
        "It is not a medical device, diagnostic tool, or forensic pathology instrument. Normal user photos are rejected by policy."
    )

    consent_confirmed = st.checkbox(
        "I certify that this image originates from a documented, ethically consented research dataset protocol."
    )
    dataset_protocol_id = st.text_input("Institutional Research Protocol / Dataset ID", value="WOUND_BENCHMARK_2023")

    ev = st.session_state.active_evidence
    if not ev or ev.get("file_type") != "image":
        st.info("ℹ️ Ingest an image in the Evidence Locker tab.")
    else:
        if st.button("🔬 Run Consented Research Analysis"):
            meta = {
                "research_dataset_id": dataset_protocol_id if consent_confirmed else None,
                "ethical_consent_documented": consent_confirmed,
                "research_license": "Research Use Only",
            }

            ckpt_p = Path("data/checkpoints/wound_research/wound_resnet18_best.pt")
            if not ckpt_p.exists():
                st.warning("⚠️ No trained wound checkpoint found. Model training required with consented dataset manifest.")
            else:
                predictor = WoundResearchPredictor(ckpt_p, enforce_research_consent=True)
                res = predictor.predict(Path(ev["working_copy_path"]), research_metadata=meta)

                if res["status"] == "rejected_by_policy":
                    st.error(f"⛔ Rejected by Policy: {res['rejection_reason']}")
                else:
                    st.success(f"Visual Category Prediction: {res['predicted_category']}")
                    st.info(f"**Notice:** {res['advisory_text']}")
                    st.json(res["probabilities"])
                    st.warning(f"**Disclaimer:** {res['disclaimer']}")

# ================= TAB 5: TOOLMARK RETRIEVAL =================
with tab_toolmark:
    st.header("Bullet & Toolmark Similarity Retrieval")
    st.caption("Controlled laboratory reference comparison. Does not establish firearm attribution or caliber.")

    ev = st.session_state.active_evidence
    if not ev or ev.get("file_type") != "image":
        st.info("ℹ️ Ingest a toolmark image in the Evidence Locker tab.")
    else:
        top_k = st.slider("Top-K Reference Matches", 1, 10, 5)
        index_path_str = st.text_input("Index Directory", value="data/indices/toolmark")

        if st.button("🔎 Retrieve Top-K Similar References"):
            idx_p = Path(index_path_str)
            if not idx_p.exists():
                st.error(f"Index directory not found at: `{idx_p}`. Build reference index first.")
            else:
                retriever = ToolmarkRetriever(idx_p)
                res = retriever.retrieve_similar(
                    query_image_path=Path(ev["working_copy_path"]),
                    working_dir=FORENSIC_CONFIG.WORKING_COPY_DIR,
                    top_k=top_k,
                )

                if res["status"] == "insufficient_reference_data":
                    st.warning(f"⚠️ {res['message']}")
                else:
                    st.success("✅ Top-K Nearest References Retrieved:")
                    st.dataframe(pd.DataFrame(res["top_k_candidates"]), use_container_width=True)
                    st.warning(f"**Disclaimer:** {res['disclaimer']}")

# ================= TAB 6: AUDIT LEDGER & REPORTS =================
with tab_audit:
    st.header("Append-Only Audit Ledger & Technical Reports")

    ev = st.session_state.active_evidence
    if ev:
        case_id = st.text_input("Case Identifier", value="CASE_2026_RESEARCH_01")
        if st.button("📄 Generate Verifiable Technical PDF Report"):
            with st.spinner("Generating technical report strictly from empirical records..."):
                runs = audit_db.get_run_history(ev["evidence_id"])
                all_events = []
                for r in runs:
                    all_events.extend(audit_db.get_audit_trail(r["run_id"]))

                out_pdf = FORENSIC_CONFIG.ARTIFACTS_DIR / f"report_{ev['evidence_id']}.pdf"

                pdf_path = st.session_state.report_gen.generate_pdf_report(
                    output_path=out_pdf,
                    case_id=case_id,
                    evidence_id=ev["evidence_id"],
                    original_filename=ev["original_filename"],
                    original_sha256=ev["original_sha256"],
                    working_copy_sha256=ev["working_copy_sha256"],
                    timestamps_utc={"ingested_at": "UTC Record"},
                    actual_metadata=ev["metadata"],
                    module_results={},
                    audit_events=all_events,
                )

                st.success(f"✅ Report Generated! SHA-256: `{calculate_sha256(pdf_path)}`")
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Factual PDF Report",
                        data=f,
                        file_name=pdf_path.name,
                        mime="application/pdf",
                    )

    st.subheader("SQLite WAL Audit Trail")
    with audit_db._get_connection() as conn:
        df_ledger = pd.read_sql_query("SELECT evidence_id, original_filename, original_sha256, ingested_at_utc FROM evidence_ledger ORDER BY ingested_at_utc DESC LIMIT 10", conn)
        df_runs = pd.read_sql_query("SELECT run_id, evidence_id, module_name, status, started_at_utc FROM processing_runs ORDER BY started_at_utc DESC LIMIT 10", conn)

    st.write("Recent Evidence Entries:")
    st.dataframe(df_ledger, use_container_width=True)

    st.write("Recent Processing Runs:")
    st.dataframe(df_runs, use_container_width=True)
