"""
Forensic Evidence Analysis System (FEAS) - Ultra-Modern Forensic Intelligence Workstation
Interactive forensic dashboard supporting single-evidence deep analysis,
high-throughput batch triage, biometric suspect galleries, AI deepfakes, audio forensics, and court-ready PDF generation.
"""

import asyncio
import io
import json
import os
from pathlib import Path
import uuid
import cv2
import numpy as np
import pandas as pd
from PIL import Image
import streamlit as st
import torch

from src.api.orchestrator import run_batch_forensic_analysis, run_parallel_forensic_analysis
from src.config import (
    DEVICE,
    FIXTURES_DIR,
    REPORTS_DIR,
    STORAGE_DIR,
    TEMP_DIR
)
from src.db.audit import (
    create_case_sync,
    get_audit_trail_sync,
    get_case_sync,
    get_suspect_profiles_sync,
    init_db,
    list_cases_sync
)
from src.pipeline.ingestion import process_uploaded_media
from src.reports.batch_report import build_batch_pdf
from src.reports.pdf_generator import build_pdf
from src.ui.components import (
    apply_forensic_theme,
    render_header,
    render_metric_card,
    render_suspect_card,
    render_verdict_card,
    render_cctv_surveillance_matrix,
    render_3d_face_mesh,
    render_3d_fft_surface,
    render_audio_telemetry_radar,
    render_ballistics_striation_3d
)

# Page configuration
st.set_page_config(
    page_title="FEAS - Forensic Evidence Analysis System",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
init_db()

# Apply custom dark forensic theme
apply_forensic_theme()


def main():
    # Render Workstation Header
    render_header()

    # Sidebar Controls & Hardware Telemetry
    with st.sidebar:
        st.markdown("### 📋 Examiner Intake Profile")
        investigator_name = st.text_input("Lead Examiner", value="Special Agent Forensic Examiner")
        operator_notes = st.text_area(
            "Incident / Intake Notes",
            value="Standard forensic intake and evidentiary integrity verification protocol."
        )

        st.markdown("---")
        st.markdown("### ⚡ Quick-Load Test Assets")
        st.caption("Click any asset to instantly run end-to-end neural forensic analysis:")
        
        col_f1, col_f2 = st.columns(2)
        load_sample = col_f1.button("🔍 Tampered", use_container_width=True)
        load_cctv = col_f2.button("👤 CCTV Face", use_container_width=True)
        load_wound = col_f1.button("🩺 Wound", use_container_width=True)
        load_bullet = col_f2.button("💥 Ballistics", use_container_width=True)
        load_deepfake = col_f1.button("🤖 AI Deepfake", use_container_width=True)
        load_audio = col_f2.button("🎙️ Audio Voice", use_container_width=True)
        load_video = st.button("🎥 3-Sec Video (1fps Keyframes)", use_container_width=True)

        st.markdown("---")
        st.markdown("### 🖥️ Hardware Telemetry")
        
        cuda_on = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if cuda_on else "None (CPU Active)"
        
        st.markdown(
            f"""
            <div style="background: rgba(14, 23, 38, 0.9); border: 1px solid rgba(56, 189, 248, 0.15); border-radius: 10px; padding: 12px; font-size: 12px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #94a3b8;">COMPUTE:</span>
                    <span style="color: #00f0ff; font-weight: 700;">{str(DEVICE).upper()}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #94a3b8;">ACCELERATOR:</span>
                    <span style="color: {'#10b981' if cuda_on else '#f59e0b'}; font-weight: 700;">{'CUDA READY' if cuda_on else 'CPU OPTIMIZED'}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #94a3b8;">DEVICE:</span>
                    <span style="color: #cbd5e1; font-weight: 600; font-size: 11px;">{gpu_name[:16]}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #94a3b8;">AUDIT STORE:</span>
                    <span style="color: #a855f7; font-weight: 700;">SQLITE WAL</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Main Navigation Tabs
    nav_single, nav_batch, nav_suspects, nav_cctv = st.tabs([
        "🔍 Single Evidence Workstation",
        "📁 High-Throughput Batch Triage",
        "👥 Biometric Suspect Registry",
        "📡 Live CCTV Surveillance Operations Center"
    ])

    # =========================================================================
    # TAB 1: SINGLE EVIDENCE DEEP ANALYSIS
    # =========================================================================
    with nav_single:
        # Handle Quick-Load Fixtures
        uploaded_file_bytes = None
        uploaded_filename = None

        if load_sample and (FIXTURES_DIR / "sample.jpg").exists():
            uploaded_file_bytes = open(FIXTURES_DIR / "sample.jpg", "rb").read()
            uploaded_filename = "sample_tampered.jpg"
        elif load_cctv and (FIXTURES_DIR / "cctv_crop.jpg").exists():
            uploaded_file_bytes = open(FIXTURES_DIR / "cctv_crop.jpg", "rb").read()
            uploaded_filename = "cctv_crop.jpg"
        elif load_wound and (FIXTURES_DIR / "wound_sample.jpg").exists():
            uploaded_file_bytes = open(FIXTURES_DIR / "wound_sample.jpg", "rb").read()
            uploaded_filename = "wound_sample.jpg"
        elif load_bullet and (FIXTURES_DIR / "bullet_sample.jpg").exists():
            uploaded_file_bytes = open(FIXTURES_DIR / "bullet_sample.jpg", "rb").read()
            uploaded_filename = "bullet_sample.jpg"
        elif load_deepfake and (FIXTURES_DIR / "deepfake_sample.png").exists():
            uploaded_file_bytes = open(FIXTURES_DIR / "deepfake_sample.png", "rb").read()
            uploaded_filename = "deepfake_sample.png"
        elif load_audio and (FIXTURES_DIR / "sample_audio.wav").exists():
            uploaded_file_bytes = open(FIXTURES_DIR / "sample_audio.wav", "rb").read()
            uploaded_filename = "sample_audio.wav"
        elif load_video and (FIXTURES_DIR / "sample_video.mp4").exists():
            uploaded_file_bytes = open(FIXTURES_DIR / "sample_video.mp4", "rb").read()
            uploaded_filename = "sample_surveillance.mp4"

        # Evidence Uploader
        if not uploaded_file_bytes:
            uploaded_file = st.file_uploader(
                "Upload Forensic Evidence (Images: JPG, PNG | Video: MP4, MKV, AVI | Audio: WAV — Max 500 MB)",
                type=["jpg", "jpeg", "png", "mp4", "mkv", "avi", "wav"],
                help="Cryptographic SHA-256 computed on intake.",
                key="single_uploader"
            )
            if uploaded_file is not None:
                uploaded_file_bytes = uploaded_file.read()
                uploaded_filename = uploaded_file.name

        if uploaded_file_bytes and uploaded_filename:
            # Execution Pipeline with High-Tech Status
            with st.status("🔒 Ingesting Evidence & Executing Parallel Forensic Models...", expanded=True) as status_box:
                st.write("Computing cryptographic SHA-256 bitstream checksum...")
                media_info = process_uploaded_media(uploaded_file_bytes, uploaded_filename)
                input_sha256 = media_info["input_sha256"]
                st.write(f"SHA-256 Digest: `{input_sha256}`")

                st.write("Initializing SQLite WAL Immutable Case Log...")
                case_id = create_case_sync(
                    filename=uploaded_filename,
                    file_type=media_info["file_type"],
                    input_sha256=input_sha256,
                    investigator_name=investigator_name,
                    operator_notes=operator_notes
                )
                st.write(f"Court Case Assigned: `{case_id}`")

                st.write("Executing parallel neural inference models (Forgery, Deepfake, Audio, Face, Wound, Ballistics)...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(
                    run_parallel_forensic_analysis(case_id, media_info, operator_notes)
                )
                loop.close()

                st.write("Rendering Court-Ready Master PDF Report with digital cryptographic seal...")
                pdf_out = build_pdf(results)
                results["pdf_path"] = pdf_out["pdf_path"]
                results["pdf_sha256"] = pdf_out["pdf_sha256"]

                status_box.update(label="✅ Forensic Assessment Complete • PDF Report Sealed!", state="complete", expanded=False)

            # Executive Verdict Banner
            forgery = results.get("forgery") or {}
            deepfake = results.get("deepfake") or {}
            audio = results.get("audio") or {}
            is_tampered = forgery.get("is_tampered", False) or deepfake.get("is_deepfake", False) or audio.get("is_synthetic_voice", False)
            verdict = results.get("verdict", "MEDIA AUTHENTIC")
            render_verdict_card(verdict, is_tampered, case_id, input_sha256)

            # High-Impact 6-Deck KPI Row
            col_k1, col_k2, col_k3, col_k4, col_k5, col_k6 = st.columns(6)
            
            # 1. Tamper KPI
            tamper_pct = forgery.get("tamper_score", 0) * 100
            with col_k1:
                render_metric_card(
                    "Forgery Ratio",
                    f"{tamper_pct:.1f}%",
                    "Tampered" if forgery.get("is_tampered") else "Authentic",
                    "#ff3366" if forgery.get("is_tampered") else "#10b981"
                )

            # 2. Deepfake KPI
            df_pct = deepfake.get("deepfake_score", 0) * 100
            with col_k2:
                render_metric_card(
                    "AI Synthesis",
                    f"{df_pct:.1f}%",
                    "Synthetic" if deepfake.get("is_deepfake") else "Sensor Natural",
                    "#ec4899" if deepfake.get("is_deepfake") else "#10b981"
                )

            # 3. Audio / Voice KPI
            with col_k3:
                if audio.get("has_audio"):
                    voice_pct = audio.get("synthetic_voice_score", 0) * 100
                    is_synth = audio.get("is_synthetic_voice", False)
                    render_metric_card(
                        "Voice Cloner",
                        f"{voice_pct:.1f}%",
                        "Synthetic TTS" if is_synth else "Human Voice",
                        "#e11d48" if is_synth else "#10b981"
                    )
                else:
                    render_metric_card("Voice Forensics", "No Audio", "Visual Media", "#64748b")

            # 4. Face Biometric KPI
            face = results.get("face") or {}
            top_m = face.get("top_match")
            with col_k4:
                if face.get("face_detected"):
                    match_name = top_m["name"] if top_m else "No High Conf Match"
                    match_sim = f"{top_m['similarity']*100:.1f}%" if top_m else "N/A"
                    render_metric_card("Biometric Match", match_name, f"Similarity: {match_sim}", "#a855f7")
                else:
                    render_metric_card("Biometric Face", "Not Detected", "Scene / Object", "#64748b")

            # 5. Wound KPI
            wound = results.get("wound") or {}
            with col_k5:
                if wound.get("wound_detected"):
                    w_type = wound.get("wound_type", "").upper()
                    w_sev = wound.get("severity", "").upper()
                    render_metric_card("Wound Triage", w_type, f"Severity: {w_sev}", "#f59e0b")
                else:
                    render_metric_card("Clinical Wound", "None Detected", "No Trauma", "#64748b")

            # 6. Ballistics KPI
            ballistics = results.get("ballistics") or {}
            with col_k6:
                if ballistics.get("striae_detected"):
                    cal = ballistics.get("caliber", "")
                    mfg = ballistics.get("manufacturer", "")
                    render_metric_card("Ballistic Signature", cal, f"Mfg: {mfg}", "#00f0ff")
                else:
                    render_metric_card("Micro-Striations", "None Detected", "No Toolmarks", "#64748b")

            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

            # PDF Download Action Bar
            pdf_path = results.get("pdf_path")
            if pdf_path and Path(pdf_path).exists():
                with open(pdf_path, "rb") as pdf_f:
                    pdf_bytes = pdf_f.read()
                
                col_d1, col_d2 = st.columns([3, 1])
                with col_d1:
                    st.markdown(
                        f"""
                        <div style="background: rgba(14, 23, 38, 0.8); border: 1px solid rgba(56, 189, 248, 0.15); border-radius: 10px; padding: 10px 16px; font-size: 12px; font-family: 'JetBrains Mono', monospace; display: flex; align-items: center; gap: 10px;">
                            <span style="color: #10b981; font-weight: 700;">⚖️ COURT SEAL SHA-256:</span>
                            <span style="color: #ffffff;">{results.get('pdf_sha256', '')}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                with col_d2:
                    st.download_button(
                        label="📄 Download Sealed PDF Report",
                        data=pdf_bytes,
                        file_name=f"FEAS_Report_{case_id}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )

            st.markdown("---")

            # Multi-Deck Forensic Inspection Tabs
            tab_forgery, tab_deepfake, tab_audio, tab_face, tab_trauma_ballistics, tab_video, tab_audit = st.tabs([
                "🔍 Digital Forgery & ELA",
                "🤖 AI Deepfake & FFT Spectrum",
                "🎙️ Acoustic & Voice Forensics",
                "👤 Biometric Face Super-Res",
                "🩺 Clinical Trauma & 💥 Ballistics",
                "🎥 Surveillance Video Keyframes",
                "📜 Bitstream Integrity & Audit Log"
            ])

            # TAB 1: Digital Forgery
            with tab_forgery:
                ela_metrics = forgery.get("ela_metrics") or {}
                col_i1, col_i2 = st.columns(2)
                annotated_path = forgery.get("annotated_image_path")
                ela_path = forgery.get("ela_image_path")

                with col_i1:
                    st.markdown("##### 🎯 Localized Tamper Regions (YOLOv8 Detection)")
                    if annotated_path and Path(annotated_path).exists():
                        st.image(annotated_path, use_container_width=True)
                    else:
                        st.caption("No localized anomalies.")

                with col_i2:
                    st.markdown("##### 🔬 95% JPEG Error Level Analysis (ELA)")
                    if ela_path and Path(ela_path).exists():
                        st.image(ela_path, use_container_width=True)
                    else:
                        st.caption("No ELA heatmap generated.")

                bboxes = forgery.get("bboxes", [])
                if bboxes:
                    st.markdown("##### 📍 Spliced / Inpainted Bounding Coordinates")
                    st.dataframe(pd.DataFrame(bboxes), use_container_width=True)
                else:
                    st.success("✅ Clean compression profile: No anomalous splicing, inpainting, or copy-move artifacts detected.")

            # TAB 2: Deepfake & Synthetic Media
            with tab_deepfake:
                st.markdown(f"#### 🤖 Generative Model Attribution: **{deepfake.get('model_attribution', 'Organic Capture')}**")
                
                col_df1, col_df2 = st.columns(2)
                fft_path = deepfake.get("fft_spectrum_image_path")
                boundary_path = deepfake.get("blend_boundary_map_path")

                with col_df1:
                    st.markdown("##### 🌐 2D Fast Fourier Transform (FFT) Power Spectrum")
                    if fft_path and Path(fft_path).exists():
                        st.image(fft_path, use_container_width=True)
                        st.caption("Concentric circles mark frequency cutoffs. Bright grid spikes indicate periodic upsampling artifacts.")
                    else:
                        st.caption("No FFT spectrum generated.")

                with col_df2:
                    st.markdown("##### 🧩 Blending Boundary & Seam Gradient Anomaly Map")
                    if boundary_path and Path(boundary_path).exists():
                        st.image(boundary_path, use_container_width=True)
                        st.caption("Localized high-energy edges highlight FaceSwap and Poisson inpainting blending seams.")
                    else:
                        st.caption("No boundary map generated.")

                signals = deepfake.get("artifact_signals", [])
                if signals:
                    st.markdown("##### 🚩 Generative Artifact Signals Detected")
                    for s in signals:
                        st.warning(f"• {s}")
                else:
                    st.success("✅ Natural sensor noise profile: No periodic GAN lattice or diffusion smoothing artifacts detected.")

                fft_meta = deepfake.get("fft_metrics", {})
                if fft_meta:
                    st.markdown("##### 📊 Quantitative Frequency Domain Metrics")
                    st.dataframe(pd.DataFrame([fft_meta]), use_container_width=True)

                # 3D FFT Frequency Domain Surface Landscape
                render_3d_fft_surface(fft_path)

            # TAB 3: Acoustic & Voice Forensics
            with tab_audio:
                if audio.get("has_audio"):
                    col_a1, col_a2 = st.columns(2)
                    spec_path = audio.get("spectrogram_image_path")
                    wave_path = audio.get("waveform_image_path")

                    with col_a1:
                        st.markdown("##### 📈 Calibrated Short-Time Fourier Transform (STFT) Spectrogram")
                        if spec_path and Path(spec_path).exists():
                            st.image(spec_path, use_container_width=True)

                    with col_a2:
                        st.markdown("##### 🔊 Time-Domain Oscillogram Waveform")
                        if wave_path and Path(wave_path).exists():
                            st.image(wave_path, use_container_width=True)

                    # Acoustic Metrics Row
                    col_am1, col_am2, col_am3, col_am4 = st.columns(4)
                    col_am1.metric("Duration", f"{audio.get('duration_seconds', 0):.2f}s")
                    col_am2.metric("Sample Rate", f"{audio.get('sample_rate_hz', 0)} Hz")
                    col_am3.metric("Acoustic SNR", f"{audio.get('snr_db', 0):.1f} dB")
                    col_am4.metric("Pitch (F0) Jitter", f"{audio.get('pitch_jitter', 0)*100:.2f}%")

                    # High-Graphics Acoustic Voiceprint Multi-Vector Radar
                    render_audio_telemetry_radar(audio)

                    anomalies = audio.get("voice_anomalies", [])
                    if anomalies:
                        st.markdown("##### ⚠️ Acoustic & Vocal Inconsistencies")
                        for a in anomalies:
                            st.warning(f"• {a}")
                    else:
                        st.success("✅ Natural human vocal jitter and organic acoustic background noise floor confirmed.")
                else:
                    st.info("🎙️ No playable acoustic audio stream present in evidence file. Audio forensics triggers for video (.mp4, .mkv) and audio (.wav) evidence.")

            # TAB 4: Face Super-Resolution & Biometrics
            with tab_face:
                if face.get("face_detected"):
                    comp_path = face.get("comparison_image_path")
                    if comp_path and Path(comp_path).exists():
                        st.markdown("##### ⚡ Low-Res CCTV Crop vs. FEAS 1024x1024 Enhanced Tensor")
                        st.image(comp_path, use_container_width=True)

                    col_sub1, col_sub2 = st.columns([1, 1])
                    with col_sub1:
                        st.markdown("##### 🗃️ Biometric Suspect Hits")
                        matches = face.get("matches", [])
                        if matches:
                            for i, match in enumerate(matches):
                                render_suspect_card(match, rank=i+1)
                        else:
                            st.info("No matching suspect profiles found in gallery above the 60% confidence threshold.")

                    with col_sub2:
                        st.markdown("##### 🧬 3D Biometric Facial Topology Mesh")
                        emb = face.get("embedding", [])
                        top_m = face.get("top_match")
                        match_name = top_m["name"] if top_m else "Subject"
                        if emb:
                            render_3d_face_mesh(emb, match_name)
                        else:
                            st.caption("No FaceNet vector embedding generated.")
                else:
                    st.info("👤 No human facial subject was detected in the submitted evidence.")

            # TAB 5: Trauma & Ballistics
            with tab_trauma_ballistics:
                col_w, col_b = st.columns(2)
                
                with col_w:
                    st.markdown("#### 🩺 Clinical Wound Assessment")
                    if wound.get("wound_detected"):
                        w_path = wound.get("annotated_image_path")
                        if w_path and Path(w_path).exists():
                            st.image(w_path, use_container_width=True)

                        col_w1, col_w2 = st.columns(2)
                        col_w1.metric("Wound Type", f"{wound.get('wound_type', 'N/A').upper()}", f"{wound.get('wound_type_confidence', 0)*100:.1f}%")
                        col_w2.metric("Severity", f"{wound.get('severity', 'N/A').upper()}", f"{wound.get('severity_confidence', 0)*100:.1f}%")
                        
                        col_w3, col_w4 = st.columns(2)
                        col_w3.metric("Estimated Age", f"{wound.get('age', 'N/A').upper()}", f"{wound.get('age_confidence', 0)*100:.1f}%")
                        col_w4.metric("Anatomical Location", f"{wound.get('location', 'N/A').upper()}", f"{wound.get('location_confidence', 0)*100:.1f}%")
                    else:
                        st.info("🩺 No biological wound or trauma pattern identified in evidence frame.")

                with col_b:
                    st.markdown("#### 💥 Ballistics Micro-Striations")
                    if ballistics.get("striae_detected"):
                        b_path = ballistics.get("striation_map_path")
                        if b_path and Path(b_path).exists():
                            st.image(b_path, use_container_width=True)

                        col_b1, col_b2 = st.columns(2)
                        col_b1.metric("Caliber", f"{ballistics.get('caliber', 'N/A')}", f"{ballistics.get('caliber_confidence', 0)*100:.1f}%")
                        col_b2.metric("Rifling", f"{ballistics.get('rifling', 'N/A')}", f"{ballistics.get('rifling_confidence', 0)*100:.1f}%")
                        
                        st.metric("Manufacturer Signature", f"{ballistics.get('manufacturer', 'N/A')}", f"{ballistics.get('manufacturer_confidence', 0)*100:.1f}%")
                        
                        # 3D Micro-Striation Topography
                        render_ballistics_striation_3d(b_path)
                    else:
                        st.info("💥 No microscopic bullet striations identified in evidence frame.")

            # TAB 6: Video Keyframes & CCTV Surveillance Matrix
            with tab_video:
                if results.get("is_video"):
                    keyframes = results.get("keyframes", [])
                    render_cctv_surveillance_matrix(
                        keyframes=keyframes,
                        media_info=results.get("media_info")
                    )
                else:
                    st.info("Uploaded evidence is a single frame image. Previewing in CCTV Surveillance HUD:")
                    preview_img = results.get("enhanced_image_path") or results.get("annotated_image_path")
                    if not preview_img and (FIXTURES_DIR / "cctv_crop.jpg").exists():
                        preview_img = str(FIXTURES_DIR / "cctv_crop.jpg")
                    render_cctv_surveillance_matrix(
                        keyframes=[preview_img] if preview_img else [],
                        media_info={"fps": 1.0}
                    )

            # TAB 7: Bitstream & Audit Log
            with tab_audit:
                st.markdown("##### 🔍 Advanced Bitstream & Hex Metadata Assessment")
                adv_meta = results.get("advanced_metadata", {})
                if adv_meta:
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        st.markdown(f"**Identified Format:** `{adv_meta.get('format_identified', 'N/A')}`")
                        st.markdown(f"**Magic Header:** `{'✅ VALID' if adv_meta.get('magic_valid') else '🚩 MISMATCH'}`")
                        st.markdown(f"**Steganography Risk:** `{adv_meta.get('steganography_overlay_risk', 'NONE')}`")
                    with col_m2:
                        st.markdown(f"**Double Compression:** `{adv_meta.get('double_compression_risk', 'LOW')}`")
                        st.markdown(f"**AI Tools Detected:** `{', '.join(adv_meta.get('ai_tools', [])) or 'None'}`")
                        st.markdown(f"**Editing Tools Detected:** `{', '.join(adv_meta.get('editing_software_detected', [])) or 'None'}`")

                st.markdown("##### ⚖️ Immutable SQLite WAL Execution Log")
                audit_events = get_audit_trail_sync(case_id)
                if audit_events:
                    st.dataframe(pd.DataFrame(audit_events), use_container_width=True)
                
                exif_data = results.get("metadata", {})
                if exif_data and exif_data.get("has_exif"):
                    st.markdown("##### 📷 EXIF / GPS Hardware Telemetry")
                    st.json(exif_data)
                else:
                    st.caption("No embedded EXIF metadata detected in source file.")

        else:
            st.markdown(
                """
                <div style="background: rgba(14, 23, 38, 0.6); border: 2px dashed rgba(56, 189, 248, 0.25); border-radius: 14px; padding: 40px; text-align: center; margin-top: 20px;">
                <div style="font-size: 42px; margin-bottom: 10px;">🛡️</div>
                    <div style="font-size: 18px; font-weight: 700; color: #ffffff; margin-bottom: 6px;">
                        Awaiting Evidence File
                    </div>
                    <div style="color: #94a3b8; font-size: 13px; max-width: 480px; margin: 0 auto;">
                        Upload crime scene photos, deepfakes, CCTV frames, or audio/surveillance videos above, or select any quick-load test asset in the sidebar to begin.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # =========================================================================
    # TAB 2: BATCH MULTI-EVIDENCE TRIAGE
    # =========================================================================
    with nav_batch:
        st.markdown("### 📁 High-Throughput Batch Evidence Triage")
        st.caption("Analyze large evidence folders simultaneously with automated parallel triage matrices and sealed batch reports.")

        col_b_act1, col_b_act2 = st.columns([3, 1])
        batch_files = col_b_act1.file_uploader(
            "Select Multiple Photos / Videos / Audio for Batch Intake",
            type=["jpg", "jpeg", "png", "mp4", "mkv", "avi", "wav"],
            accept_multiple_files=True,
            key="batch_uploader"
        )
        load_all_fixtures = col_b_act2.button("⚡ Test All 6 Test Assets", use_container_width=True)

        batch_items = []
        if load_all_fixtures:
            for fn in ["sample.jpg", "deepfake_sample.png", "sample_audio.wav", "cctv_crop.jpg", "wound_sample.jpg", "bullet_sample.jpg"]:
                p = FIXTURES_DIR / fn
                if p.exists():
                    batch_items.append({"filename": fn, "file_bytes": open(p, "rb").read()})
        elif batch_files:
            for bf in batch_files:
                batch_items.append({"filename": bf.name, "file_bytes": bf.read()})

        if batch_items:
            batch_id = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
            st.markdown(f"**Selected Evidence Files:** `{len(batch_items)}` | **Batch ID:** `{batch_id}`")

            if st.button("🚀 Run Parallel Batch Analysis", type="primary", use_container_width=True):
                progress_bar = st.progress(0, text="Initializing batch processing engine...")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                batch_res = loop.run_until_complete(
                    run_batch_forensic_analysis(
                        batch_id=batch_id,
                        file_items=batch_items,
                        investigator_name=investigator_name,
                        operator_notes=operator_notes
                    )
                )
                loop.close()

                # Generate batch PDF
                pdf_res = build_batch_pdf(batch_res)
                batch_res["pdf_path"] = pdf_res["pdf_path"]
                batch_res["pdf_sha256"] = pdf_res["pdf_sha256"]

                progress_bar.progress(100, text="✅ Batch Triage Analysis & Consolidated Master PDF Sealed!")

                # Render Batch Summary Metrics
                summary = batch_res.get("summary", {})
                st.markdown("---")
                col_bm1, col_bm2, col_bm3, col_bm4 = st.columns(4)
                
                with col_bm1:
                    render_metric_card("Total Items", f"{summary.get('total_files', 0)} files", "Processed", "#00f0ff")
                with col_bm2:
                    render_metric_card("Tampering Hits", f"{summary.get('tampered_count', 0)}", f"{summary.get('tamper_rate', 0)*100:.0f}% Flagged", "#ff3366")
                with col_bm3:
                    render_metric_card("AI Deepfakes", f"{summary.get('deepfake_count', 0)}", "Synthetic Media", "#ec4899")
                with col_bm4:
                    render_metric_card("Avg Throughput", f"{summary.get('average_seconds_per_file', 0):.2f}s", "Per File Latency", "#10b981")

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

                # PDF Download Action Bar
                col_bp1, col_bp2 = st.columns([3, 1])
                with col_bp1:
                    st.markdown(
                        f"""
                        <div style="background: rgba(14, 23, 38, 0.8); border: 1px solid rgba(56, 189, 248, 0.15); border-radius: 10px; padding: 10px 16px; font-size: 12px; font-family: 'JetBrains Mono', monospace; display: flex; align-items: center; gap: 10px;">
                            <span style="color: #10b981; font-weight: 700;">⚖️ BATCH MASTER PDF SHA-256:</span>
                            <span style="color: #ffffff;">{batch_res.get('pdf_sha256')}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                with col_bp2:
                    with open(pdf_res["pdf_path"], "rb") as b_pdf_f:
                        st.download_button(
                            label="📄 Download Master Batch PDF",
                            data=b_pdf_f.read(),
                            file_name=f"FEAS_Batch_Triage_{batch_id}.pdf",
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True
                        )

                # Batch Matrix Table
                st.markdown("#### 📋 Master Evidence Triage Matrix")
                rows = []
                for item in batch_res.get("items", []):
                    forg = item.get("forgery") or {}
                    df_item = item.get("deepfake") or {}
                    au_item = item.get("audio") or {}
                    fc = item.get("face") or {}
                    wd = item.get("wound") or {}
                    bl = item.get("ballistics") or {}
                    
                    rows.append({
                        "Case ID": item.get("case_id"),
                        "Filename": item.get("filename"),
                        "Tamper Prob": f"{forg.get('tamper_score', 0)*100:.1f}%",
                        "Deepfake Prob": f"{df_item.get('deepfake_score', 0)*100:.1f}%",
                        "Integrity": "🚩 TAMPERED" if (forg.get("is_tampered") or df_item.get("is_deepfake") or au_item.get("is_synthetic_voice")) else "✅ AUTHENTIC",
                        "Biometric Match": ((fc.get("top_match") or {}).get("name") or "None") if fc.get("face_detected") else "No Face",
                        "Wound Type": wd.get("wound_type", "None").upper() if wd.get("wound_detected") else "None",
                        "Ballistics": bl.get("caliber", "None") if bl.get("striae_detected") else "None",
                        "Verdict": item.get("verdict", "")
                    })
                
                df_batch = pd.DataFrame(rows)
                st.dataframe(df_batch, use_container_width=True)

        else:
            st.info("👆 Upload multiple files above or click '⚡ Test All 6 Test Assets' to execute batch triage.")

    # =========================================================================
    # TAB 3: BIOMETRIC SUSPECT REGISTRY
    # =========================================================================
    with nav_suspects:
        st.markdown("### 👥 Biometric Suspect Registry")
        st.caption("Active suspect gallery with pre-indexed 512-dimensional FaceNet vectors stored in SQLite WAL.")
        
        suspects = get_suspect_profiles_sync()
        if suspects:
            cols = st.columns(min(3, len(suspects)))
            for i, s in enumerate(suspects):
                with cols[i % len(cols)]:
                    render_suspect_card({
                        "name": s.get("name"),
                        "suspect_id": s.get("suspect_id"),
                        "notes": s.get("notes"),
                        "similarity": 0.0,
                        "distance": 0.0
                    }, rank=i+1)
        else:
            st.info("No suspect profiles registered in database.")

    # =========================================================================
    # TAB 4: LIVE CCTV SURVEILLANCE & DERIVED VIDEO ANALYSIS
    # =========================================================================
    with nav_cctv:
        st.markdown("### 📡 CCTV Video Analysis & Surveillance Operations")
        st.caption("Forensic CCTV video intake, deterministic enhancement, YOLOv8 tracking, and objective event extraction.")

        # Mandatory advisory warning banner
        st.markdown("""
        <div style="background: rgba(30, 20, 10, 0.8); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 8px; padding: 12px; margin-bottom: 16px; color: #fde68a; font-size: 13px;">
            <b>ADVISORY FORENSIC PROTOTYPE</b><br/>
            This is an experimental computer-vision analysis. Detections and tracking results are automated estimates and require human review. The application does not identify people or establish legal conclusions.
        </div>
        """, unsafe_allow_html=True)

        col_cctv_up, col_cctv_conf = st.columns([1.1, 0.9])
        with col_cctv_up:
            st.markdown("#### 01 · Evidence Intake")
            cctv_file = st.file_uploader(
                "Upload CCTV Footage (MP4, AVI, MKV, MOV — Immutable Intake)",
                type=["mp4", "avi", "mkv", "mov"],
                key="feas_cctv_uploader"
            )
            col_cid1, col_cid2 = st.columns(2)
            with col_cid1:
                c_case_id = st.text_input("Case ID", value="CASE-2026-001", key="cctv_case_id")
                c_cam_id = st.text_input("Camera ID", value="CAM-NORTH-01", key="cctv_cam_id")
                c_event_dt = st.text_input("Event Date/Time", value="", placeholder="YYYY-MM-DD HH:MM:SS", key="cctv_event_dt")
            with col_cid2:
                c_ev_id = st.text_input("Evidence ID", value="EV-CCTV-001", key="cctv_ev_id")
                c_cam_loc = st.text_input("Camera Location", value="Perimeter Gate 3", key="cctv_cam_loc")
                c_tz = st.selectbox("Timezone", ["UTC", "EST", "CST", "PST", "GMT", "IST"], index=0, key="cctv_tz")

        with col_cctv_conf:
            st.markdown("#### 02 · Analytics Parameters")
            c_mode = st.radio("Analysis Mode", ["Fast Review (1 FPS)", "Full Analysis"], index=0, key="cctv_mode")
            c_mode_val = "fast_review" if "Fast Review" in c_mode else "full_analysis"
            c_step = st.number_input("Frame Sampling Step", min_value=1, max_value=30, value=2, step=1, key="cctv_step") if c_mode_val == "full_analysis" else 1

            c_enh = st.selectbox(
                "Deterministic Enhancement",
                ["Basic (CLAHE + Contrast)", "Low Light (Gamma + Denoise + CLAHE)", "None (Raw working frames)"],
                key="cctv_enh"
            )
            c_enh_val = "low_light" if "Low Light" in c_enh else ("none" if "None" in c_enh else "basic")
            c_conf = st.slider("Detection Confidence", min_value=0.10, max_value=0.90, value=0.40, step=0.05, key="cctv_conf")

            use_roi = st.checkbox("Configure Spatial ROI Zone (Optional)", value=False, key="feas_cctv_roi")
            roi_polygon = None
            if use_roi:
                rx1, ry1 = st.columns(2)
                with rx1:
                    roi_x1 = st.number_input("ROI Left (X1)", value=100, step=10, key="roi_x1")
                    roi_y1 = st.number_input("ROI Top (Y1)", value=100, step=10, key="roi_y1")
                with ry1:
                    roi_x2 = st.number_input("ROI Right (X2)", value=800, step=10, key="roi_x2")
                    roi_y2 = st.number_input("ROI Bottom (Y2)", value=600, step=10, key="roi_y2")
                roi_polygon = [(roi_x1, roi_y1), (roi_x2, roi_y1), (roi_x2, roi_y2), (roi_x1, roi_y2)]

        if cctv_file is not None:
            import tempfile
            from src.cctv.video_validator import validate_cctv_video
            from src.cctv.integrity import calculate_file_sha256
            from src.cctv_pipeline import run_cctv_analysis

            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=Path(cctv_file.name).suffix)
            tfile.write(cctv_file.read())
            tfile.flush()
            tfile.close()
            temp_path = Path(tfile.name)

            val = validate_cctv_video(temp_path)
            if not val.is_valid:
                st.error(f"Validation Error: {val.error_message}")
            else:
                orig_hash = calculate_file_sha256(temp_path)
                st.markdown(f"**Evidence Intake File:** `{cctv_file.name}` ({val.file_size_bytes / (1024*1024):.2f} MB)")
                st.markdown(f"**SHA-256 Digest:** `{orig_hash}`")

                if st.button("🚀 Execute CCTV Forensic Analysis", type="primary", use_container_width=True, key="btn_run_feas_cctv"):
                    p_bar = st.progress(0.0)
                    p_status = st.empty()

                    def on_prog(pct, msg):
                        p_bar.progress(pct)
                        p_status.markdown(f"**Status:** {msg}")

                    try:
                        res = run_cctv_analysis(
                            input_video_path=temp_path,
                            case_id=c_case_id,
                            evidence_id=c_ev_id,
                            camera_id=c_cam_id,
                            camera_location=c_cam_loc,
                            event_datetime=c_event_dt,
                            timezone_str=c_tz,
                            analysis_mode=c_mode_val,
                            frame_sampling_step=c_step,
                            enhancement_mode=c_enh_val,
                            confidence_threshold=c_conf,
                            roi_polygon=roi_polygon,
                            progress_callback=on_prog
                        )
                        st.session_state.feas_cctv_res = res
                        st.success("CCTV forensic analysis successfully completed.")
                    except Exception as ex:
                        st.error(f"Analysis failed: {ex}")
                    finally:
                        try:
                            temp_path.unlink(missing_ok=True)
                        except Exception:
                            pass

        # Display results if available
        c_res = st.session_state.get("feas_cctv_res")
        if c_res:
            st.markdown("---")
            st.markdown("### 📊 CCTV Forensic Dossier & Derived Artifacts")
            st.info(c_res.get("derived_label", "Derived output for human review"))

            cm1, cm2, cm3, cm4, cm5, cm6 = st.columns(6)
            cm1.metric("Frames Analyzed", c_res.get("total_frames_processed", 0))
            cm2.metric("Total Detections", c_res.get("total_detections", 0))
            cm3.metric("Tracked Objects", c_res.get("total_tracks", 0))
            cm4.metric("Vehicles Profiled", c_res.get("total_vehicles", 0))
            cm5.metric("💥 Crashes Detected", c_res.get("total_collisions", 0))
            cm6.metric("⚠️ Suspicious Alerts", c_res.get("total_suspicious_alerts", 0))

            # Cryptographic Integrity
            st.markdown("#### 🔒 Cryptographic Chain of Custody")
            st.markdown(f"- **Original File Hash (SHA-256):** `{c_res.get('original_sha256')}`")
            st.markdown(f"- **Working Copy Hash (SHA-256):** `{c_res.get('working_copy_sha256')}`")
            if c_res.get('original_sha256') == c_res.get('working_copy_sha256'):
                st.markdown('<div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 10px; color: #10b981; font-size: 13px;">✓ Working copy verified byte-for-byte identical to original evidence.</div>', unsafe_allow_html=True)

            # Download Artifacts
            st.markdown("#### 📥 Exported Forensic Artifacts")
            dc1, dc2, dc3, dc4, dc5 = st.columns(5)
            v_p = Path(c_res.get("annotated_video_path", ""))
            if v_p.is_file():
                with open(v_p, "rb") as f:
                    dc1.download_button("Download Video", data=f.read(), file_name=v_p.name, mime="video/mp4", key="dl_feas_vid")
            veh_p = Path(c_res.get("vehicles_csv_path", ""))
            if veh_p.is_file():
                with open(veh_p, "rb") as f:
                    dc2.download_button("Vehicles CSV", data=f.read(), file_name=veh_p.name, mime="text/csv", key="dl_feas_veh")
            col_p = Path(c_res.get("collisions_csv_path", ""))
            if col_p.is_file():
                with open(col_p, "rb") as f:
                    dc3.download_button("Collisions CSV", data=f.read(), file_name=col_p.name, mime="text/csv", key="dl_feas_col")
            susp_p = Path(c_res.get("suspicious_csv_path", ""))
            if susp_p.is_file():
                with open(susp_p, "rb") as f:
                    dc4.download_button("Suspicious CSV", data=f.read(), file_name=susp_p.name, mime="text/csv", key="dl_feas_susp")
            rep_p = Path(c_res.get("report_md_path", ""))
            if rep_p.is_file():
                with open(rep_p, "rb") as f:
                    dc5.download_button("Report (MD)", data=f.read(), file_name=rep_p.name, mime="text/markdown", key="dl_feas_rep")

            # 1. Collision Alerts
            feas_collisions = c_res.get("collisions", [])
            if feas_collisions:
                st.markdown("#### 💥 Vehicle Crash & Collision Dynamics Detected")
                for fc in feas_collisions:
                    st.error(
                        f"**Collision Incident {fc.get('incident_id')} at {fc.get('timestamp_hms')}** | "
                        f"Vehicles: `{fc.get('primary_track_id')}` & `{fc.get('secondary_track_id') or 'Barrier'}` | "
                        f"Severity: **{fc.get('severity_advisory')}** (Impact Delta-V: {fc.get('impact_speed_delta_px_s')} px/s)\n\n"
                        f"*{fc.get('description')}*"
                    )
            else:
                st.success("✓ No collision dynamics or sudden deceleration impacts detected.")

            # 2. Suspicious Activities
            feas_susp = c_res.get("suspicious_activities", [])
            if feas_susp:
                st.markdown("#### ⚠️ Suspicious Vehicle Behaviors & Kinematic Anomalies")
                s_data = []
                for s in feas_susp:
                    s_data.append({
                        "Alert ID": s.get("alert_id"),
                        "Track ID": s.get("track_id"),
                        "Anomaly Type": s.get("activity_type"),
                        "Timestamp": s.get("timestamp_hms"),
                        "Severity": s.get("severity_level"),
                        "Speed (px/s)": s.get("speed_px_s"),
                        "Heading": f"{s.get('heading_degrees')}°" if s.get('heading_degrees') is not None else "N/A",
                        "Description": s.get("description")
                    })
                st.dataframe(pd.DataFrame(s_data), use_container_width=True)

            # 3. Vehicle Registry
            feas_vehs = c_res.get("vehicles", [])
            if feas_vehs:
                st.markdown("#### 🚗 Vehicle Forensic Registry (ANPR, Make/Model, Paint Color)")
                v_data = []
                for v in feas_vehs:
                    plt_str = v.get("license_plate_number") or "Not Resolved"
                    p_conf = v.get("license_plate_confidence", 0.0)
                    v_data.append({
                        "Track ID": v.get("track_id"),
                        "Type": v.get("vehicle_type"),
                        "Body Classification": v.get("estimated_body_type"),
                        "Advisory Model Profile": v.get("estimated_model_profile"),
                        "Paint Color": v.get("dominant_color"),
                        "License Plate": f"{plt_str} ({int(p_conf*100)}%)" if plt_str != "Not Resolved" else "N/A",
                        "Collision?": "💥 YES" if v.get("crash_involved") else "No",
                        "Suspicious Flags": ", ".join(v.get("suspicious_activities", [])) or "None",
                        "Speed (px/s)": v.get("speed_estimate_px_s", 0.0)
                    })
                st.dataframe(pd.DataFrame(v_data), use_container_width=True)

                # Vehicle crops gallery
                st.markdown("##### 🔍 Vehicle Keyframe Crops & License Plate Extracts")
                crops_list = [v for v in feas_vehs if v.get("license_plate_crop_path") or v.get("vehicle_crop_path")]
                if crops_list:
                    cp_cols = st.columns(min(4, len(crops_list)))
                    for idx, v in enumerate(crops_list[:8]):
                        with cp_cols[idx % len(cp_cols)]:
                            v_crop = v.get("vehicle_crop_path")
                            p_crop = v.get("license_plate_crop_path")
                            if v_crop and Path(v_crop).is_file():
                                st.image(str(v_crop), caption=f"Vehicle: {v.get('track_id')}", use_container_width=True)
                            if p_crop and Path(p_crop).is_file():
                                st.image(str(p_crop), caption=f"Plate: {v.get('license_plate_number') or 'Unresolved'}", use_container_width=True)

            if v_p.is_file():
                st.markdown("#### 🎬 Derived Annotated Video Preview")
                st.video(str(v_p))

            ev_list = c_res.get("events", [])
            if ev_list:
                st.markdown("#### 📋 Objective Spatio-Temporal Event Timeline")
                edf = pd.DataFrame(ev_list)[["event_id", "timestamp_hms", "event_type", "track_id", "description", "confidence_summary"]]
                st.dataframe(edf, use_container_width=True)

            sum_p = c_res.get("summary_json_path")
            if sum_p:
                kf_items = list(Path(sum_p).parent.parent.glob("keyframes/*/*.jpg"))
                if kf_items:
                    st.markdown("#### 🖼️ Keyframe Inspection Gallery")
                    k_cols = st.columns(min(4, len(kf_items[:8])))
                    for idx, kf in enumerate(kf_items[:8]):
                        with k_cols[idx % len(k_cols)]:
                            st.image(str(kf), caption=kf.name, use_container_width=True)


if __name__ == "__main__":
    main()
