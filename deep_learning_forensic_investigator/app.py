import io, json, os, hashlib, tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

from forensic_models import (
    detect_forgery, authenticate_faces, classify_wound,
    model_status, demo_overlay, image_sha256
)
from src.cctv_pipeline import run_cctv_analysis
from src.cctv.video_validator import validate_cctv_video
from src.cctv.integrity import calculate_file_sha256

st.set_page_config(page_title="Deep Learning Forensic Investigator", page_icon="🔎", layout="wide")

st.markdown("""
<style>
:root { --navy:#081426; --panel:#101f35; --panel2:#142842; --line:#263d5b; --cyan:#48c7d8; }
.stApp { background:linear-gradient(140deg,#07111f 0%,#0a1830 55%,#0c2039 100%); color:#edf4ff; }
[data-testid="stSidebar"] { background:#081426; border-right:1px solid #263d5b; }
.block-container { padding-top:1.4rem; max-width:1500px; }
h1,h2,h3 { color:#f3f7ff !important; }
p, label, .stMarkdown { color:#d4e0f1; }
div[data-testid="stMetric"] { background:#101f35; border:1px solid #263d5b; padding:16px; border-radius:14px; }
div[data-testid="stMetric"] label { color:#a9bdd8; }
div[data-testid="stMetricValue"] { color:#f4f8ff; }
.stButton > button, .stDownloadButton > button { background:#1c7590; color:white; border:1px solid #3aa7be; border-radius:9px; font-weight:600; }
.stButton > button:hover, .stDownloadButton > button:hover { background:#238da8; color:white; border-color:#64d7e8; }
div[data-testid="stFileUploader"] { background:#101f35; border:1px dashed #3a587a; border-radius:12px; padding:8px; }
.panel { background:#101f35; border:1px solid #263d5b; padding:18px; border-radius:15px; margin-bottom:12px; }
.kicker { color:#58d2df; text-transform:uppercase; letter-spacing:.12em; font-size:.76rem; font-weight:700; }
.muted { color:#a9bdd8; font-size:.9rem; }
.warning { background:#3b2b14; border:1px solid #916a2d; border-radius:10px; padding:12px; color:#ffe5b0; }
.good { background:#10352f; border:1px solid #287d6a; border-radius:10px; padding:12px; color:#b9f6e5; }
</style>
""", unsafe_allow_html=True)

if "results" not in st.session_state:
    st.session_state.results = []
if "report_items" not in st.session_state:
    st.session_state.report_items = []

st.sidebar.markdown("## 🔎 Forensic Investigator")
st.sidebar.caption("AI-assisted image analysis workspace")
page = st.sidebar.radio("Workspace", [
    "Overview", "Forgery Localization", "Face Authentication",
    "Wound Classification", "CCTV Video Analysis", "Forensic Report"
])
mode = st.sidebar.selectbox("Inference mode", ["Demo mode (clearly labelled)", "Real model adapters"])
st.sidebar.markdown("---")
st.sidebar.markdown("### Model status")
statuses = model_status()
for name, status in statuses.items():
    st.sidebar.write(("🟢 " if status["loaded"] else "⚪ ") + name)
    st.sidebar.caption(status["detail"])
st.sidebar.markdown("---")
st.sidebar.caption("Prototype UI. Outputs are not legal or medical conclusions.")

def add_result(module, result, source_names):
    item = {
        "module": module,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": source_names,
        "mode": "DEMO" if mode.startswith("Demo") else "REAL MODEL",
        "result": result
    }
    st.session_state.report_items.append(item)
    st.session_state.results.append(item)

def uploaded_image(label, key):
    f = st.file_uploader(label, type=["jpg", "jpeg", "png"], key=key)
    if f:
        try:
            im = Image.open(f).convert("RGB")
            st.image(im, caption=f.name, use_container_width=True)
            return im, f.name
        except Exception:
            st.error("Could not read this image. Please upload a valid JPG or PNG.")
    return None, None

def build_pdf(items):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="NavyTitle", parent=styles["Title"], textColor=colors.HexColor("#102849"), fontSize=20, leading=25))
    styles.add(ParagraphStyle(name="SmallBody", parent=styles["BodyText"], fontSize=9, leading=13))
    story = [
        Paragraph("Deep Learning Forensic Investigator", styles["NavyTitle"]),
        Paragraph("AI-based forgery localization, face authentication and wound image classification", styles["Normal"]),
        Spacer(1, 5*mm),
        Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
        Spacer(1, 3*mm),
        Paragraph("<b>Important limitations</b>: Demo-mode entries are synthetic examples, not model predictions. Real-model entries are only as reliable as the connected model, data, and validation. This report is an investigative aid, not a legal conclusion, identity proof, or medical diagnosis.", styles["SmallBody"]),
        Spacer(1, 6*mm)
    ]
    if not items:
        story.append(Paragraph("No analysis results have been added to this report.", styles["BodyText"]))
    for idx, item in enumerate(items, 1):
        story.append(Paragraph(f"{idx}. {item['module']} — {item['mode']}", styles["Heading2"]))
        story.append(Paragraph(f"Timestamp: {item['timestamp']}", styles["SmallBody"]))
        story.append(Paragraph(f"Input files: {', '.join(item.get('sources', [])) or 'Not recorded'}", styles["SmallBody"]))
        result_text = json.dumps(item.get("result", {}), ensure_ascii=False, indent=2)
        result_text = result_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>").replace(" ", "&nbsp;")
        story.append(Paragraph(result_text[:9000], styles["SmallBody"]))
        story.append(Spacer(1, 4*mm))
    doc.build(story)
    return buf.getvalue()

if page == "Overview":
    st.markdown('<div class="kicker">Investigation workspace</div>', unsafe_allow_html=True)
    st.title("Deep Learning Forensic Investigator")
    st.write("A unified workspace for image tampering review, face comparison, wound-image classification, and evidence reporting.")
    if mode.startswith("Demo"):
        st.markdown('<div class="warning"><b>DEMO MODE ACTIVE</b> — outputs are illustrative placeholders and must not be interpreted as actual forensic findings.</div>', unsafe_allow_html=True)
    else:
        st.info("Real-model mode selected. Each module will stop with a clear message unless its adapter is configured with a real trained model.")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Analysis modules", "04")
    c2.metric("Results in session", len(st.session_state.results))
    c3.metric("Report entries", len(st.session_state.report_items))
    c4.metric("Model adapters loaded", sum(1 for x in statuses.values() if x["loaded"]))
    st.markdown("### Workflow")
    a,b,c,d = st.columns(4)
    with a:
        st.markdown('<div class="panel"><div class="kicker">01 · Image integrity</div><h3>Forgery localization</h3><p class="muted">Review suspicious regions and preserve the original input for comparison.</p></div>', unsafe_allow_html=True)
    with b:
        st.markdown('<div class="panel"><div class="kicker">02 · Face comparison</div><h3>Face authentication</h3><p class="muted">Compare two face images using a configured embedding model.</p></div>', unsafe_allow_html=True)
    with c:
        st.markdown('<div class="panel"><div class="kicker">03 · Wound analysis</div><h3>Wound classification</h3><p class="muted">Classify visible wound-image features using a trained model.</p></div>', unsafe_allow_html=True)
    with d:
        st.markdown('<div class="panel"><div class="kicker">04 · CCTV Analysis</div><h3>Video Tracking</h3><p class="muted">Deterministic enhancement, multi-object tracking, and event extraction.</p></div>', unsafe_allow_html=True)
    st.markdown("### Recent results")
    if st.session_state.results:
        for r in reversed(st.session_state.results[-5:]):
            st.write(f"**{r['module']}** · {r['mode']} · {r['timestamp']}")
            st.json(r["result"], expanded=False)
    else:
        st.caption("No analyses yet. Choose a module from the sidebar to begin.")

elif page == "Forgery Localization":
    st.title("Forgery Localization")
    st.caption("Image tampering review and suspected-region visualization")
    im, name = uploaded_image("Upload suspected image", "forgery_image")
    if im:
        st.caption(f"SHA-256: `{image_sha256(im)}`")
        if st.button("Analyze image", type="primary"):
            try:
                result = detect_forgery(im, real=mode.startswith("Real"))
                st.session_state.forgery_result = result
                add_result("Forgery Localization", result["summary"], [name])
            except Exception as e:
                st.error(str(e))
        result = st.session_state.get("forgery_result")
        if result:
            st.markdown(f"**Result status:** `{result['status']}`")
            if result.get("overlay"):
                col1,col2 = st.columns(2)
                with col1: st.image(im, caption="Original image", use_container_width=True)
                with col2: st.image(result["overlay"], caption="Visualization — demo overlay or model output", use_container_width=True)
            st.json(result["summary"])
            if result.get("is_demo"):
                st.warning("Synthetic demonstration only. The marked boxes are randomly illustrative and do not indicate actual tampering.")
            elif result.get("status") != "success":
                st.error(result.get("message", "No valid model output returned."))

elif page == "Face Authentication":
    st.title("Face Authentication")
    st.caption("Compare two face images. Use only images you are authorized to process.")
    col1,col2 = st.columns(2)
    with col1: im1,n1 = uploaded_image("Upload reference face", "face_ref")
    with col2: im2,n2 = uploaded_image("Upload comparison face", "face_cmp")
    if im1 and im2 and st.button("Compare faces", type="primary"):
        try:
            result = authenticate_faces(im1, im2, real=mode.startswith("Real"))
            st.session_state.face_result = result
            add_result("Face Authentication", result.get("summary", result), [n1,n2])
        except Exception as e:
            st.error(str(e))
    result = st.session_state.get("face_result")
    if result:
        if result.get("is_demo"):
            st.warning("DEMO OUTPUT: the displayed score is synthetic and does not represent identity similarity.")
        elif result.get("status") != "success":
            st.error(result.get("message", "Real face model is not configured."))
        st.json(result.get("summary", result))

elif page == "Wound Classification":
    st.title("Wound Classification")
    st.caption("Experimental image classification — not a medical diagnostic tool.")
    im, name = uploaded_image("Upload wound image", "wound_image")
    if im and st.button("Classify wound image", type="primary"):
        try:
            result = classify_wound(im, real=mode.startswith("Real"))
            st.session_state.wound_result = result
            add_result("Wound Classification", result.get("summary", result), [name])
        except Exception as e:
            st.error(str(e))
    result = st.session_state.get("wound_result")
    if result:
        if result.get("is_demo"):
            st.warning("DEMO OUTPUT: these labels and confidence values are synthetic placeholders, not predictions.")
        elif result.get("status") != "success":
            st.error(result.get("message", "Real wound model is not configured."))
        st.json(result.get("summary", result))
        st.caption("Do not use this output to determine wound age, severity, cause, treatment, or legal facts without qualified expert assessment.")

elif page == "CCTV Video Analysis":
    st.title("CCTV Video Analysis")
    st.caption("Derived CCTV Enhancement, Multi-Object Tracking, and Spatio-Temporal Event Extraction")

    # Mandatory advisory warning banner
    st.markdown("""
    <div class="warning">
        <b>ADVISORY FORENSIC PROTOTYPE</b><br/>
        This is an experimental computer-vision analysis. Detections and tracking results are automated estimates and require human review. The application does not identify people or establish legal conclusions.
    </div>
    """, unsafe_allow_html=True)
    st.write("")

    col_up, col_config = st.columns([1.1, 0.9])

    with col_up:
        st.markdown('<div class="kicker">01 · Evidence Intake</div>', unsafe_allow_html=True)
        uploaded_vid = st.file_uploader(
            "Upload CCTV Video (Original immutable intake)",
            type=["mp4", "avi", "mkv", "mov"],
            key="cctv_upload_widget",
            help="Accepted containers: MP4, AVI, MKV, MOV. Max recommended size: 500 MB."
        )

        c_id1, c_id2 = st.columns(2)
        with c_id1:
            case_id = st.text_input("Case ID", value="CASE-2026-001", help="Investigative case identifier")
            camera_id = st.text_input("Camera ID", value="CAM-NORTH-01", help="CCTV camera hardware identifier")
            event_dt = st.text_input("Event Date / Time (Optional)", value="", placeholder="YYYY-MM-DD HH:MM:SS")
        with c_id2:
            evidence_id = st.text_input("Evidence ID", value="EV-CCTV-001", help="Unique evidence tracking identifier")
            camera_loc = st.text_input("Camera Location", value="Perimeter Gate 3", help="Camera physical location")
            tz_str = st.selectbox("Timezone", ["UTC", "EST", "CST", "PST", "GMT", "IST"], index=0)

    with col_config:
        st.markdown('<div class="kicker">02 · Processing Parameters</div>', unsafe_allow_html=True)
        analysis_mode = st.radio(
            "Analysis Mode",
            ["Fast Review (1 Frame / Sec)", "Full Analysis"],
            index=0,
            help="Fast Review samples 1 frame per second for rapid triage. Full analysis processes consecutive frames."
        )
        mode_val = "fast_review" if "Fast Review" in analysis_mode else "full_analysis"

        sampling_step = 1
        if mode_val == "full_analysis":
            sampling_step = st.number_input("Frame Sampling Step", min_value=1, max_value=30, value=2, step=1, help="Process every Nth frame")

        enhancement_choice = st.selectbox(
            "Deterministic Enhancement Mode",
            ["Basic (CLAHE + Contrast)", "Low Light (Gamma + Denoise + CLAHE)", "None (Raw working frames)"],
            index=0,
            help="Conventional OpenCV contrast enhancement on derived working copy."
        )
        enh_mode_val = "basic"
        if "Low Light" in enhancement_choice:
            enh_mode_val = "low_light"
        elif "None" in enhancement_choice:
            enh_mode_val = "none"

        yolo_conf = st.slider("YOLO Detection Confidence", min_value=0.10, max_value=0.90, value=0.40, step=0.05)

        # ROI Configuration
        use_roi = st.checkbox("Configure Spatial ROI Zone (Optional)", value=False)
        roi_polygon = None
        if use_roi:
            st.caption("Define rectangular Region of Interest bounds [X1, Y1, X2, Y2]")
            rx1, ry1 = st.columns(2)
            with rx1:
                roi_x1 = st.number_input("ROI Left (X1)", value=100, step=10)
                roi_y1 = st.number_input("ROI Top (Y1)", value=100, step=10)
            with ry1:
                roi_x2 = st.number_input("ROI Right (X2)", value=800, step=10)
                roi_y2 = st.number_input("ROI Bottom (Y2)", value=600, step=10)
            roi_polygon = [(roi_x1, roi_y1), (roi_x2, roi_y1), (roi_x2, roi_y2), (roi_x1, roi_y2)]

    st.markdown("---")

    if uploaded_vid is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_vid.name).suffix)
        tfile.write(uploaded_vid.read())
        tfile.flush()
        tfile.close()
        temp_input_path = Path(tfile.name)

        val = validate_cctv_video(temp_input_path)
        if not val.is_valid:
            st.error(f"Validation Error: {val.error_message}")
        else:
            orig_sha = calculate_file_sha256(temp_input_path)
            st.markdown(f"**Original Evidence File:** `{uploaded_vid.name}` ({val.file_size_bytes / (1024*1024):.2f} MB)")
            st.markdown(f"**SHA-256 Digest:** `{orig_sha}`")

            if st.button("Start CCTV Forensic Analysis", type="primary", use_container_width=True):
                progress_bar = st.progress(0.0)
                status_box = st.empty()

                def on_progress(pct, msg):
                    progress_bar.progress(pct)
                    status_box.markdown(f"**Status:** {msg}")

                try:
                    res = run_cctv_analysis(
                        input_video_path=temp_input_path,
                        case_id=case_id,
                        evidence_id=evidence_id,
                        camera_id=camera_id,
                        camera_location=camera_loc,
                        event_datetime=event_dt,
                        timezone_str=tz_str,
                        analysis_mode=mode_val,
                        frame_sampling_step=sampling_step,
                        enhancement_mode=enh_mode_val,
                        yolo_model_name="yolov8n.pt",
                        confidence_threshold=yolo_conf,
                        roi_polygon=roi_polygon,
                        progress_callback=on_progress
                    )
                    st.session_state.cctv_result = res
                    add_result("CCTV Video Analysis", res.get("summary_json_path", {}), [uploaded_vid.name])
                    st.success("CCTV Analysis successfully completed.")
                except Exception as ex:
                    st.error(f"Processing halted: {ex}")
                finally:
                    try:
                        temp_input_path.unlink(missing_ok=True)
                    except Exception:
                        pass

    # Display results if available
    cctv_res = st.session_state.get("cctv_result")
    if cctv_res:
        st.markdown("### Analysis Results & Evidence Summary")
        st.info(cctv_res.get("derived_label", "Derived output for human review"))

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Frames Analyzed", cctv_res.get("total_frames_processed", 0))
        m2.metric("Total Detections", cctv_res.get("total_detections", 0))
        m3.metric("Unique Tracks", cctv_res.get("total_tracks", 0))
        m4.metric("Events Extracted", cctv_res.get("total_events", 0))
        m5.metric("FPS", cctv_res.get("metadata", {}).get("fps", 0))

        st.markdown("#### Cryptographic Chain of Custody")
        st.markdown(f"- **Original File Hash (SHA-256):** `{cctv_res.get('original_sha256')}`")
        st.markdown(f"- **Working Copy Hash (SHA-256):** `{cctv_res.get('working_copy_sha256')}`")
        if cctv_res.get('original_sha256') == cctv_res.get('working_copy_sha256'):
            st.markdown('<div class="good">✓ Working copy verified byte-for-byte identical to original evidence.</div>', unsafe_allow_html=True)

        st.markdown("#### Exported Derived Artifacts")
        d_col1, d_col2, d_col3, d_col4 = st.columns(4)

        vid_path = Path(cctv_res.get("annotated_video_path", ""))
        if vid_path.is_file():
            with open(vid_path, "rb") as f:
                d_col1.download_button(
                    "Download Annotated Video",
                    data=f.read(),
                    file_name=vid_path.name,
                    mime="video/mp4"
                )

        det_csv = Path(cctv_res.get("detections_csv_path", ""))
        if det_csv.is_file():
            with open(det_csv, "rb") as f:
                d_col2.download_button(
                    "Download Detections CSV",
                    data=f.read(),
                    file_name=det_csv.name,
                    mime="text/csv"
                )

        trk_csv = Path(cctv_res.get("tracks_csv_path", ""))
        if trk_csv.is_file():
            with open(trk_csv, "rb") as f:
                d_col3.download_button(
                    "Download Tracks CSV",
                    data=f.read(),
                    file_name=trk_csv.name,
                    mime="text/csv"
                )

        evt_json = Path(cctv_res.get("events_json_path", ""))
        if evt_json.is_file():
            with open(evt_json, "rb") as f:
                d_col4.download_button(
                    "Download Events JSON",
                    data=f.read(),
                    file_name=evt_json.name,
                    mime="application/json"
                )

        if vid_path.is_file():
            st.markdown("#### Annotated Video Preview (Derived Copy)")
            st.video(str(vid_path))

        events_list = cctv_res.get("events", [])
        if events_list:
            st.markdown("#### Objective Event Timeline")
            evt_df = pd.DataFrame(events_list)[["event_id", "timestamp_hms", "event_type", "track_id", "description", "confidence_summary"]]
            st.dataframe(evt_df, use_container_width=True)

        summary_p = cctv_res.get("summary_json_path")
        if summary_p:
            kfs = list(Path(summary_p).parent.parent.glob("keyframes/*/*.jpg"))
            if kfs:
                st.markdown("#### Keyframe Inspection Gallery")
                cols = st.columns(min(4, len(kfs[:8])))
                for idx, kf in enumerate(kfs[:8]):
                    with cols[idx % len(cols)]:
                        st.image(str(kf), caption=kf.name, use_container_width=True)

elif page == "Forensic Report":
    st.title("Forensic Report")
    st.write("Review saved session results and export a PDF summary.")
    st.markdown('<div class="warning">A report can contain demo outputs. Each entry is labelled DEMO or REAL MODEL. Confirm the source, model version, and evidence-handling process before relying on a report.</div>', unsafe_allow_html=True)
    if st.session_state.report_items:
        for i, item in enumerate(st.session_state.report_items):
            with st.expander(f"{i+1}. {item['module']} · {item['mode']} · {item['timestamp']}"):
                st.write("Input files:", ", ".join(item.get("sources", [])))
                st.json(item["result"])
        if st.button("Clear report entries"):
            st.session_state.report_items = []
            st.session_state.results = []
            st.rerun()
    else:
        st.info("No results yet. Run one or more analyses first.")
    pdf = build_pdf(st.session_state.report_items)
    st.download_button("Generate / Download PDF report", data=pdf, file_name="forensic_investigation_report.pdf", mime="application/pdf", type="primary")
    json_bytes = json.dumps(st.session_state.report_items, indent=2).encode("utf-8")
    st.download_button("Download raw JSON results", data=json_bytes, file_name="forensic_results.json", mime="application/json")
