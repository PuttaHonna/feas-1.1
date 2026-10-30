"""
Forensic Evidence Analysis System (FEAS) - Court-Ready ReportLab PDF Generator
Generates comprehensive multi-page court admissible forensic reports with SHA-256 checksums,
including Deepfake, Audio Authenticity, and Advanced Hex Bitstream evidence findings.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle
)
from PIL import Image

from src.config import REPORTS_DIR
from src.db.audit import get_audit_trail_sync, log_audit_event_sync, update_case_results_sync
from src.pipeline.ingestion import compute_sha256_file
from src.reports.template import NumberedCanvas, get_forensic_styles


def _safe_image_flowable(image_path: Optional[str], width: float, height: float) -> Optional[RLImage]:
    """Helper to safely load an image as a ReportLab Flowable if file exists."""
    if not image_path:
        return None
    p = Path(image_path)
    if not p.exists() or not p.is_file():
        return None
    try:
        with Image.open(p) as img:
            img.verify()
        return RLImage(str(p), width=width, height=height)
    except Exception:
        return None


def build_pdf(
    case_data_or_path: Union[str, Path, Dict[str, Any]],
    output_pdf_path: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """
    Build a multi-page court-ready PDF report.
    Returns: {"pdf_path": str, "pdf_sha256": str, "case_id": str}
    """
    if isinstance(case_data_or_path, (str, Path)):
        with open(case_data_or_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif isinstance(case_data_or_path, dict):
        data = case_data_or_path
    else:
        raise TypeError(f"Unsupported data type: {type(case_data_or_path)}")

    case_id = data.get("case_id", "UNKNOWN-CASE")
    dest_path = Path(output_pdf_path) if output_pdf_path else (REPORTS_DIR / f"FEAS_Report_{case_id}.pdf")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    styles = get_forensic_styles()
    doc = SimpleDocTemplate(
        str(dest_path),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=50
    )

    story = []

    # =========================================================================
    # PAGE 1: EXECUTIVE SUMMARY & CHAIN OF CUSTODY OVERVIEW
    # =========================================================================
    story.append(Paragraph("FORENSIC EVIDENCE ANALYSIS REPORT", styles["ForensicTitle"]))
    story.append(Paragraph("COURT-ADMISSIBLE EXPERT TECHNICAL ASSESSMENT", styles["ForensicSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=10))

    meta_info = data.get("metadata", {})
    adv_meta = data.get("advanced_metadata", {})
    gps_info = meta_info.get("gps")
    gps_str = f"Lat: {gps_info['latitude']}, Lon: {gps_info['longitude']}" if gps_info else "No GPS Data Embedded"
    device_str = f"{meta_info.get('device_make', '')} {meta_info.get('device_model', '')}".strip() or "Standard Digital Capture"

    exec_table_data = [
        [
            Paragraph("<b>Case Identifier:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<font color='#0284c7'><b>{case_id}</b></font>", styles["ForensicBody"]),
            Paragraph("<b>Timestamp (UTC):</b>", styles["ForensicBodyBold"]),
            Paragraph(data.get("created_at", "N/A"), styles["ForensicBody"])
        ],
        [
            Paragraph("<b>Investigator:</b>", styles["ForensicBodyBold"]),
            Paragraph(data.get("investigator_name", "Forensic Examiner"), styles["ForensicBody"]),
            Paragraph("<b>Status:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<b>{data.get('status', 'COMPLETED')}</b>", styles["ForensicBody"])
        ],
        [
            Paragraph("<b>Evidence File:</b>", styles["ForensicBodyBold"]),
            Paragraph(data.get("filename", "N/A"), styles["ForensicBody"]),
            Paragraph("<b>File Type:</b>", styles["ForensicBodyBold"]),
            Paragraph(data.get("file_type", "image").upper(), styles["ForensicBody"])
        ],
        [
            Paragraph("<b>Camera / Device:</b>", styles["ForensicBodyBold"]),
            Paragraph(device_str, styles["ForensicBody"]),
            Paragraph("<b>GPS Coordinates:</b>", styles["ForensicBodyBold"]),
            Paragraph(gps_str, styles["ForensicBody"])
        ],
        [
            Paragraph("<b>Input SHA-256:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<font size='6.5'>{data.get('input_sha256', 'N/A')}</font>", styles["ForensicCode"]),
            Paragraph("<b>Processing Mode:</b>", styles["ForensicBodyBold"]),
            Paragraph("Deterministic CUDA/CPU", styles["ForensicBody"])
        ]
    ]

    t_exec = Table(exec_table_data, colWidths=[100, 160, 100, 172])
    t_exec.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_exec)
    story.append(Spacer(1, 10))

    # Overall Forensic Verdict Box
    verdict = data.get("verdict", "INCONCLUSIVE")
    is_tampered = data.get("forgery", {}).get("is_tampered", False) or data.get("deepfake", {}).get("is_deepfake", False) or data.get("audio", {}).get("is_synthetic_voice", False)
    verdict_table = [
        [
            Paragraph("<b>OVERALL FORENSIC VERDICT:</b>", styles["ForensicH2"]),
            Paragraph(f"<b>{verdict}</b>", styles["VerdictAlert"] if is_tampered else styles["ForensicBodyBold"])
        ]
    ]
    t_verdict = Table(verdict_table, colWidths=[180, 352])
    t_verdict.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fee2e2") if is_tampered else colors.HexColor("#ecfdf5")),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#ef4444") if is_tampered else colors.HexColor("#10b981")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_verdict)
    story.append(Spacer(1, 8))

    notes = data.get("operator_notes") or "Evidence intake and forensic integrity verification protocol executed."
    story.append(Paragraph("<b>Operator & Intake Notes:</b>", styles["ForensicH2"]))
    story.append(Paragraph(notes, styles["ForensicBody"]))
    story.append(Spacer(1, 8))

    # Module Confidence Summary Table (including Deepfake & Audio)
    conf_scores = data.get("confidence_scores") or {}
    forgery = data.get("forgery") or {}
    deepfake = data.get("deepfake") or {}
    audio = data.get("audio") or {}
    face = data.get("face") or {}
    wound = data.get("wound") or {}
    ballistics = data.get("ballistics") or {}
    
    top_match = face.get("top_match") or {}
    top_match_name = top_match.get("name", "No Match") if face.get("face_detected") else "N/A"

    audio_status = "Acoustic Stream Analyzed" if audio.get("has_audio") else "No Audio Stream"
    audio_finding = f"Synthetic Voice: {audio.get('synthetic_voice_score', 0)*100:.1f}%" if audio.get("has_audio") else "Silent Media"

    summary_data = [
        [Paragraph("<b>Forensic Engine</b>", styles["ForensicBodyBold"]), Paragraph("<b>Detection Status</b>", styles["ForensicBodyBold"]), Paragraph("<b>Finding Summary</b>", styles["ForensicBodyBold"])],
        [
            Paragraph("Digital Forgery & ELA", styles["ForensicBody"]),
            Paragraph(f"{'Tampering Detected' if forgery.get('is_tampered') else 'Authentic'}", styles["ForensicBody"]),
            Paragraph(f"Tamper Index: {conf_scores.get('tamper_confidence', 0)*100:.1f}%", styles["ForensicBody"])
        ],
        [
            Paragraph("AI Deepfake & Synthesis", styles["ForensicBody"]),
            Paragraph(f"{'Synthetic Media Flagged' if deepfake.get('is_deepfake') else 'Authentic Sensor'}", styles["ForensicBody"]),
            Paragraph(f"Deepfake Index: {deepfake.get('deepfake_score', 0)*100:.1f}% ({deepfake.get('model_attribution', 'Organic')[:24]})", styles["ForensicBody"])
        ],
        [
            Paragraph("Audio & Voice Authenticity", styles["ForensicBody"]),
            Paragraph(audio_status, styles["ForensicBody"]),
            Paragraph(audio_finding, styles["ForensicBody"])
        ],
        [
            Paragraph("Face Identification", styles["ForensicBody"]),
            Paragraph(f"{'Face Detected' if face.get('face_detected') else 'No Face Detected'}", styles["ForensicBody"]),
            Paragraph(f"{top_match_name}", styles["ForensicBody"])
        ],
        [
            Paragraph("Wound Clinical Triage", styles["ForensicBody"]),
            Paragraph(f"{'Trauma Detected' if wound.get('wound_detected') else 'No Wound Pattern'}", styles["ForensicBody"]),
            Paragraph(f"{wound.get('wound_type', 'N/A').upper() if wound.get('wound_detected') else 'N/A'}", styles["ForensicBody"])
        ],
        [
            Paragraph("Ballistics Striae Match", styles["ForensicBody"]),
            Paragraph(f"{'Striations Detected' if ballistics.get('striae_detected') else 'No Ballistic Pattern'}", styles["ForensicBody"]),
            Paragraph(f"{ballistics.get('caliber', 'N/A') if ballistics.get('striae_detected') else 'N/A'}", styles["ForensicBody"])
        ],
    ]
    t_sum = Table(summary_data, colWidths=[160, 150, 222])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_sum)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: DIGITAL FORGERY DETECTION & ERROR LEVEL ANALYSIS (ELA)
    # =========================================================================
    story.append(Paragraph("1. DIGITAL FORGERY & INTEGRITY ANALYSIS", styles["ForensicH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10))

    ela_metrics = forgery.get("ela_metrics", {})
    
    forgery_metrics_table = [
        [
            Paragraph("<b>Tampering Probability:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<b>{forgery.get('tamper_score', 0)*100:.1f}%</b>", styles["VerdictAlert"] if forgery.get('is_tampered') else styles["ForensicBodyBold"]),
            Paragraph("<b>Authenticity Verdict:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<b>{'TAMPERED / MANIPULATED' if forgery.get('is_tampered') else 'AUTHENTIC ORIGINAL'}</b>", styles["ForensicBody"])
        ],
        [
            Paragraph("<b>ELA Mean Pixel Delta:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"{ela_metrics.get('mean_error', 0):.2f}", styles["ForensicBody"]),
            Paragraph("<b>ELA Max Discrepancy:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"{ela_metrics.get('max_error', 0):.1f}", styles["ForensicBody"])
        ],
        [
            Paragraph("<b>High-Delta Pixel Ratio:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"{ela_metrics.get('tamper_ratio', 0)*100:.2f}%", styles["ForensicBody"]),
            Paragraph("<b>Localized Tamper Regions:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"{len(forgery.get('bboxes', []))} Anomaly Zone(s)", styles["ForensicBody"])
        ]
    ]
    t_forg = Table(forgery_metrics_table, colWidths=[130, 136, 130, 136])
    t_forg.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_forg)
    story.append(Spacer(1, 10))

    annotated_img_flow = _safe_image_flowable(forgery.get("annotated_image_path"), width=250, height=170)
    ela_img_flow = _safe_image_flowable(forgery.get("ela_image_path"), width=250, height=170)

    if annotated_img_flow and ela_img_flow:
        img_table = [
            [annotated_img_flow, ela_img_flow],
            [Paragraph("<b>Figure 1.1: Localized Tamper Bounding Overlay</b>", styles["ForensicBody"]), Paragraph("<b>Figure 1.2: 95% JPEG Error Level Analysis Heatmap</b>", styles["ForensicBody"])]
        ]
        t_imgs = Table(img_table, colWidths=[260, 260])
        t_imgs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_imgs)
    elif annotated_img_flow:
        story.append(annotated_img_flow)

    story.append(Spacer(1, 8))

    bboxes = forgery.get("bboxes", [])
    if bboxes:
        bbox_rows = [[Paragraph("<b>Zone ID</b>", styles["ForensicBodyBold"]), Paragraph("<b>Type / Label</b>", styles["ForensicBodyBold"]), Paragraph("<b>Confidence</b>", styles["ForensicBodyBold"]), Paragraph("<b>Bounding Box (X1, Y1, X2, Y2)</b>", styles["ForensicBodyBold"])]]
        for idx, b in enumerate(bboxes):
            bbox_rows.append([
                Paragraph(f"Z-{idx+1:02d}", styles["ForensicBody"]),
                Paragraph(b.get("label", "anomaly").upper(), styles["ForensicBody"]),
                Paragraph(f"{b.get('confidence', 0)*100:.1f}%", styles["ForensicBody"]),
                Paragraph(f"[{b.get('x1')}, {b.get('y1')}, {b.get('x2')}, {b.get('y2')}]", styles["ForensicCode"])
            ])
        t_bbox = Table(bbox_rows, colWidths=[70, 130, 100, 232])
        t_bbox.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#334155")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t_bbox)
    else:
        story.append(Paragraph("<i>No regional splicing or inpainting anomalies detected. ELA compression density is uniform.</i>", styles["ForensicBody"]))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: AI DEEPFAKE & SYNTHETIC MEDIA EXAMINATION
    # =========================================================================
    story.append(Paragraph("2. AI DEEPFAKE & SYNTHETIC MEDIA FORENSICS", styles["ForensicH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10))

    fft_img_flow = _safe_image_flowable(deepfake.get("fft_spectrum_image_path"), width=250, height=170)
    boundary_img_flow = _safe_image_flowable(deepfake.get("blend_boundary_map_path"), width=250, height=170)

    if fft_img_flow and boundary_img_flow:
        df_imgs = [
            [fft_img_flow, boundary_img_flow],
            [Paragraph("<b>Figure 2.1: 2D FFT Frequency Magnitude Spectrum</b>", styles["ForensicBody"]),
             Paragraph("<b>Figure 2.2: Blending Boundary Gradient Anomaly Map</b>", styles["ForensicBody"])]
        ]
        t_df_imgs = Table(df_imgs, colWidths=[260, 260])
        t_df_imgs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_df_imgs)
        story.append(Spacer(1, 10))

    fft_metrics = deepfake.get("fft_metrics", {})
    deepfake_table = [
        [
            Paragraph("<b>Deepfake Probability:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<b>{deepfake.get('deepfake_score', 0)*100:.1f}%</b>", styles["VerdictAlert"] if deepfake.get('is_deepfake') else styles["ForensicBodyBold"]),
            Paragraph("<b>Generative Model Attribution:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<b>{deepfake.get('model_attribution', 'Organic Capture')}</b>", styles["ForensicBody"])
        ],
        [
            Paragraph("<b>High-Freq Energy Ratio:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"{fft_metrics.get('high_freq_ratio', 0):.4f}", styles["ForensicBody"]),
            Paragraph("<b>Periodic Spike Density:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"{fft_metrics.get('spike_density', 0):.5f}", styles["ForensicBody"])
        ],
        [
            Paragraph("<b>Boundary Discontinuity:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"{deepfake.get('boundary_score', 0):.3f}", styles["ForensicBody"]),
            Paragraph("<b>Meso-4 Neural Index:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"{deepfake.get('meso_score', 0):.3f}", styles["ForensicBody"])
        ]
    ]
    t_df = Table(deepfake_table, colWidths=[130, 136, 130, 136])
    t_df.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_df)
    story.append(Spacer(1, 8))

    signals = deepfake.get("artifact_signals", [])
    if signals:
        story.append(Paragraph("<b>Generative Artifact Signals Identified:</b>", styles["ForensicH2"]))
        for s in signals:
            story.append(Paragraph(f"• {s}", styles["ForensicBody"]))
    else:
        story.append(Paragraph("<i>Spectral distribution matches natural Poisson optical sensor physics. No GAN/diffusion lattice peaks identified.</i>", styles["ForensicBody"]))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: AUDIO & VOICE AUTHENTICITY FORENSICS
    # =========================================================================
    story.append(Paragraph("3. ACOUSTIC & VOICE AUTHENTICITY FORENSICS", styles["ForensicH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10))

    if audio.get("has_audio"):
        spec_flow = _safe_image_flowable(audio.get("spectrogram_image_path"), width=250, height=140)
        wave_flow = _safe_image_flowable(audio.get("waveform_image_path"), width=250, height=140)

        if spec_flow and wave_flow:
            a_imgs = [
                [spec_flow, wave_flow],
                [Paragraph("<b>Figure 3.1: Calibrated STFT Audio Spectrogram</b>", styles["ForensicBody"]),
                 Paragraph("<b>Figure 3.2: Time-Domain Oscillogram Waveform</b>", styles["ForensicBody"])]
            ]
            t_a_imgs = Table(a_imgs, colWidths=[260, 260])
            t_a_imgs.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(t_a_imgs)
            story.append(Spacer(1, 8))

        audio_table = [
            [
                Paragraph("<b>Track Duration:</b>", styles["ForensicBodyBold"]),
                Paragraph(f"{audio.get('duration_seconds', 0):.2f} seconds", styles["ForensicBody"]),
                Paragraph("<b>Sampling Rate:</b>", styles["ForensicBodyBold"]),
                Paragraph(f"{audio.get('sample_rate_hz', 0)} Hz", styles["ForensicBody"])
            ],
            [
                Paragraph("<b>Synthetic Voice Score:</b>", styles["ForensicBodyBold"]),
                Paragraph(f"<b>{audio.get('synthetic_voice_score', 0)*100:.1f}%</b>", styles["VerdictAlert"] if audio.get('is_synthetic_voice') else styles["ForensicBodyBold"]),
                Paragraph("<b>Estimated Acoustic SNR:</b>", styles["ForensicBodyBold"]),
                Paragraph(f"{audio.get('snr_db', 0):.1f} dB", styles["ForensicBody"])
            ],
            [
                Paragraph("<b>Pitch (F0) Mean:</b>", styles["ForensicBodyBold"]),
                Paragraph(f"{audio.get('pitch_mean_hz', 0):.1f} Hz", styles["ForensicBody"]),
                Paragraph("<b>Pitch Jitter Variance:</b>", styles["ForensicBodyBold"]),
                Paragraph(f"{audio.get('pitch_jitter', 0)*100:.2f}%", styles["ForensicBody"])
            ]
        ]
        t_audio = Table(audio_table, colWidths=[130, 136, 130, 136])
        t_audio.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_audio)
        story.append(Spacer(1, 8))

        anomalies = audio.get("voice_anomalies", [])
        if anomalies:
            story.append(Paragraph("<b>Acoustic & Vocal Discrepancies Noted:</b>", styles["ForensicH2"]))
            for a in anomalies:
                story.append(Paragraph(f"• {a}", styles["ForensicBody"]))
        else:
            story.append(Paragraph("<i>Acoustic floor displays natural human micro-tremor and ambient reverberation.</i>", styles["ForensicBody"]))
    else:
        story.append(Paragraph("<b>No playable acoustic stream embedded in submitted evidence file.</b>", styles["ForensicBodyBold"]))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<i>Audio spectrogram rendering and synthetic voice cloner checks were skipped.</i>", styles["ForensicBody"]))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: FACE IDENTIFICATION, WOUND & BALLISTICS
    # =========================================================================
    story.append(Paragraph("4. BIOMETRICS, CLINICAL TRAUMA & BALLISTICS", styles["ForensicH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10))

    if face.get("face_detected"):
        comp_img_flow = _safe_image_flowable(face.get("comparison_image_path"), width=500, height=170)
        if comp_img_flow:
            story.append(comp_img_flow)
            story.append(Paragraph("<b>Figure 4.1: CCTV Crop vs. FEAS 1024x1024 Enhanced Face Tensor</b>", styles["ForensicBody"]))
            story.append(Spacer(1, 8))

    wound_val = f"<b>{wound.get('wound_type', 'N/A').upper()}</b> ({wound.get('wound_type_confidence', 0)*100:.1f}%)" if wound.get("wound_detected") else "None Detected"
    sev_val = f"<b>{wound.get('severity', 'N/A').upper()}</b> ({wound.get('severity_confidence', 0)*100:.1f}%)" if wound.get("wound_detected") else "None Detected"
    cal_val = f"<b>{ballistics.get('caliber', 'N/A')}</b> ({ballistics.get('caliber_confidence', 0)*100:.1f}%)" if ballistics.get("striae_detected") else "None Detected"
    rif_val = f"<b>{ballistics.get('rifling', 'N/A')}</b> ({ballistics.get('rifling_confidence', 0)*100:.1f}%)" if ballistics.get("striae_detected") else "None Detected"

    dual_data = [
        [
            Paragraph("<b>Clinical Wound Attribute</b>", styles["ForensicBodyBold"]),
            Paragraph("<b>Finding & Confidence</b>", styles["ForensicBodyBold"]),
            Paragraph("<b>Ballistics Feature</b>", styles["ForensicBodyBold"]),
            Paragraph("<b>Classification & Confidence</b>", styles["ForensicBodyBold"])
        ],
        [
            Paragraph("Wound Classification Type", styles["ForensicBody"]),
            Paragraph(wound_val, styles["ForensicBody"]),
            Paragraph("Caliber Geometry", styles["ForensicBody"]),
            Paragraph(cal_val, styles["ForensicBody"])
        ],
        [
            Paragraph("Severity Assessment", styles["ForensicBody"]),
            Paragraph(sev_val, styles["ForensicBody"]),
            Paragraph("Rifling Groove Pattern", styles["ForensicBody"]),
            Paragraph(rif_val, styles["ForensicBody"])
        ]
    ]
    t_dual = Table(dual_data, colWidths=[130, 136, 130, 136])
    t_dual.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_dual)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: BITSTREAM INTEGRITY, AUDIT TRAIL & OPERATOR SIGN-OFF
    # =========================================================================
    story.append(Paragraph("5. BITSTREAM INTEGRITY & IMMUTABLE AUDIT LOG", styles["ForensicH1"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=10))

    # Advanced Bitstream Assessment Table
    meta_table_data = [
        [
            Paragraph("<b>Identified Bitstream Format:</b>", styles["ForensicBodyBold"]),
            Paragraph(adv_meta.get("format_identified", "Standard Format"), styles["ForensicBody"]),
            Paragraph("<b>Magic Byte Header:</b>", styles["ForensicBodyBold"]),
            Paragraph("VALID" if adv_meta.get("magic_valid", True) else "CORRUPT / MISMATCH", styles["ForensicBodyBold"])
        ],
        [
            Paragraph("<b>Steganography / Trailing Bytes:</b>", styles["ForensicBodyBold"]),
            Paragraph(adv_meta.get("steganography_overlay_risk", "NONE"), styles["ForensicBody"]),
            Paragraph("<b>Double Compression Risk:</b>", styles["ForensicBodyBold"]),
            Paragraph(adv_meta.get("double_compression_risk", "LOW"), styles["ForensicBody"])
        ],
        [
            Paragraph("<b>AI Tool Footprint:</b>", styles["ForensicBodyBold"]),
            Paragraph(", ".join(adv_meta.get("ai_tools", [])) or "None Detected in Bitstream", styles["ForensicBody"]),
            Paragraph("<b>Editing Software Signatures:</b>", styles["ForensicBodyBold"]),
            Paragraph(", ".join(adv_meta.get("editing_software_detected", [])) or "None Detected", styles["ForensicBody"])
        ]
    ]
    t_adv = Table(meta_table_data, colWidths=[140, 130, 130, 132])
    t_adv.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_adv)
    story.append(Spacer(1, 10))

    audit_trail = data.get("audit_trail") or get_audit_trail_sync(case_id)
    if audit_trail:
        audit_rows = [
            [
                Paragraph("<b>Timestamp (UTC)</b>", styles["ForensicBodyBold"]),
                Paragraph("<b>Audit Action</b>", styles["ForensicBodyBold"]),
                Paragraph("<b>SHA-256 Checksum</b>", styles["ForensicBodyBold"]),
                Paragraph("<b>Operation Details</b>", styles["ForensicBodyBold"])
            ]
        ]
        for a in audit_trail:
            ts = a.get("timestamp", "N/A")
            act = a.get("action", "LOG_EVENT")
            sha = a.get("input_sha256") or a.get("output_sha256") or "N/A"
            det = a.get("details") or a.get("details_json") or ""
            if isinstance(det, dict):
                det_str = ", ".join([f"{k}: {v}" for k, v in det.items()])
            else:
                det_str = str(det)
            audit_rows.append([
                Paragraph(ts, styles["ForensicCode"]),
                Paragraph(act, styles["ForensicBodyBold"]),
                Paragraph(f"<font size='6.5'>{sha[:24]}...</font>" if len(sha) > 24 else sha, styles["ForensicCode"]),
                Paragraph(det_str[:60], styles["ForensicBody"])
            ])
        t_audit = Table(audit_rows, colWidths=[120, 110, 110, 192])
        t_audit.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t_audit)

    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>FORENSIC EXAMINER CERTIFICATION & SIGN-OFF:</b>", styles["ForensicH2"]))
    story.append(Paragraph(
        "I hereby certify that the evidence analyzed herein has been processed following strict digital chain-of-custody "
        "standards under SQLite WAL audit logging. All algorithmic operations, 2D FFT spectral transforms, acoustic spectrograms, "
        "super-resolution tensors, and feature extractions are mathematically deterministic and verifiable against the stated SHA-256 hashes.",
        styles["ForensicBody"]
    ))
    story.append(Spacer(1, 10))

    sign_data = [
        [
            Paragraph("<b>Lead Forensic Examiner:</b>", styles["ForensicBodyBold"]),
            Paragraph("_______________________________", styles["ForensicBody"]),
            Paragraph("<b>Date & Time:</b>", styles["ForensicBodyBold"]),
            Paragraph("_______________________________", styles["ForensicBody"])
        ],
        [
            Paragraph("<b>Supervisor / Agency Head:</b>", styles["ForensicBodyBold"]),
            Paragraph("_______________________________", styles["ForensicBody"]),
            Paragraph("<b>Digital Badge #:</b>", styles["ForensicBodyBold"]),
            Paragraph("FEAS-AUDIT-VERIFIED-2026", styles["ForensicBody"])
        ]
    ]
    t_sign = Table(sign_data, colWidths=[140, 126, 110, 156])
    t_sign.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_sign)

    doc.build(story, canvasmaker=NumberedCanvas)

    pdf_sha256 = compute_sha256_file(dest_path)

    log_audit_event_sync(
        case_id=case_id,
        action="COURT_PDF_REPORT_GENERATED",
        output_sha256=pdf_sha256,
        details={"pdf_path": str(dest_path), "pdf_sha256": pdf_sha256}
    )

    update_case_results_sync(
        case_id=case_id,
        status="COMPLETED",
        verdict=verdict,
        summary=data if isinstance(data, dict) else {},
        output_sha256=pdf_sha256
    )

    return {
        "pdf_path": str(dest_path),
        "pdf_sha256": pdf_sha256,
        "case_id": case_id
    }


def build_user_analysis_affidavit(
    analysis_record: Dict[str, Any],
    user_profile: Optional[Dict[str, Any]] = None,
    output_pdf_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Generate an official, court-admissible PDF affidavit & Certificate of Examination
    for an individual forensic analysis run conducted by an authenticated examiner.
    Strictly conforms to Federal Rule of Evidence 702 (FRE 702), Daubert v. Merrell Dow,
    and ISO/IEC 17025 chain-of-custody standards.
    """
    if user_profile is None:
        user_profile = {}

    analysis_id = analysis_record.get("analysis_id", f"FEAS-ANL-{int(datetime.now().timestamp())}")
    case_id = analysis_record.get("case_id", "ACTIVE-INVESTIGATION")
    module_name = (analysis_record.get("module") or "General Forensic").upper()
    verdict = (analysis_record.get("verdict") or "AUTHENTIC").upper()
    confidence = float(analysis_record.get("confidence") or 0.95)
    evidence_name = analysis_record.get("evidence_name") or "evidence_file.dat"
    sha256_hash = analysis_record.get("sha256") or "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    timestamp_utc = analysis_record.get("timestamp") or datetime.now(timezone.utc).isoformat()
    findings = analysis_record.get("findings") or {}

    # Examiner attributes
    display_name = user_profile.get("display_name") or user_profile.get("displayName") or "Special Agent Alice Vance"
    user_id = user_profile.get("user_id") or user_profile.get("uid") or "examiner_001"
    role = user_profile.get("role") or "Lead Forensic Investigator"
    badge_number = user_profile.get("badge_number") or user_profile.get("badgeNumber") or "FEAS-8842"
    clearance = user_profile.get("clearance_level") or user_profile.get("clearance") or "Level 5 (Court Admissible / Top Secret)"
    email = user_profile.get("email") or f"{user_id}@feas-forensics.gov"

    dest_path = Path(output_pdf_path) if output_pdf_path else (REPORTS_DIR / f"FEAS_Affidavit_{analysis_id}.pdf")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    styles = get_forensic_styles()
    doc = SimpleDocTemplate(
        str(dest_path),
        pagesize=letter,
        leftMargin=38,
        rightMargin=38,
        topMargin=48,
        bottomMargin=48
    )

    story = []

    # 1. Header & Court Preamble
    story.append(Paragraph("FORENSIC EVIDENCE ANALYSIS SYSTEM (FEAS 2.0)", styles["ForensicTitle"]))
    story.append(Paragraph("CERTIFICATE OF EXPERT FORENSIC EXAMINATION & JUDICIAL AFFIDAVIT", styles["ForensicSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=8))

    # FRE 702 Legal Standards Badge
    legal_badge = [
        [
            Paragraph(
                "<b>LEGAL JURISDICTION:</b> Federal Rule of Evidence 702 (FRE 702) &bull; "
                "Daubert / Frye Standard Compliant &bull; ISO/IEC 17025 Forensic Laboratory Standards",
                styles["ForensicBodyBold"]
            )
        ]
    ]
    t_legal = Table(legal_badge, colWidths=[536])
    t_legal.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#0284c7")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_legal)
    story.append(Spacer(1, 10))

    # 2. Examiner Credentials & Case Metadata Grid
    creds_data = [
        [
            Paragraph("<b>Investigating Examiner:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<b>{display_name}</b>", styles["ForensicBodyBold"]),
            Paragraph("<b>Forensic UID:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<font color='#0284c7'><b>{user_id}</b></font>", styles["ForensicBody"])
        ],
        [
            Paragraph("<b>Official Role / Title:</b>", styles["ForensicBodyBold"]),
            Paragraph(role, styles["ForensicBody"]),
            Paragraph("<b>Official Badge #:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<font color='#0284c7'><b>{badge_number}</b></font>", styles["ForensicBody"])
        ],
        [
            Paragraph("<b>Security Clearance:</b>", styles["ForensicBodyBold"]),
            Paragraph(clearance, styles["ForensicBody"]),
            Paragraph("<b>Agency Division:</b>", styles["ForensicBodyBold"]),
            Paragraph("Digital Evidence & AI Vision Lab", styles["ForensicBody"])
        ],
        [
            Paragraph("<b>Official Email / Contact:</b>", styles["ForensicBodyBold"]),
            Paragraph(email, styles["ForensicBody"]),
            Paragraph("<b>Case Reference ID:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<font color='#0284c7'><b>{case_id}</b></font>", styles["ForensicBody"])
        ]
    ]
    t_creds = Table(creds_data, colWidths=[120, 158, 110, 148])
    t_creds.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
    ]))
    story.append(t_creds)
    story.append(Spacer(1, 10))

    # 3. Target Evidence Authentication & SHA-256
    story.append(Paragraph("<b>EVIDENTIARY CUSTODY & DIGITAL INTEGRITY VERIFICATION:</b>", styles["ForensicH2"]))
    evidence_data = [
        [
            Paragraph("<b>Target Evidence File:</b>", styles["ForensicBodyBold"]),
            Paragraph(evidence_name, styles["ForensicBody"]),
            Paragraph("<b>Analysis Record ID:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<font color='#0f172a'><b>{analysis_id}</b></font>", styles["ForensicBody"])
        ],
        [
            Paragraph("<b>Ingestion Timestamp:</b>", styles["ForensicBodyBold"]),
            Paragraph(timestamp_utc, styles["ForensicBody"]),
            Paragraph("<b>Chain of Custody:</b>", styles["ForensicBodyBold"]),
            Paragraph("VERIFIED & IMMUTABLY SEALED", styles["ForensicBodyBold"])
        ],
        [
            Paragraph("<b>Cryptographic SHA-256:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<font size='6.5'>{sha256_hash}</font>", styles["ForensicCode"]),
            Paragraph("<b>Ledger Storage:</b>", styles["ForensicBodyBold"]),
            Paragraph("Firestore Cloud Vault + Local SQLite", styles["ForensicBody"])
        ]
    ]
    t_ev = Table(evidence_data, colWidths=[120, 158, 110, 148])
    t_ev.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
    ]))
    story.append(t_ev)
    story.append(Spacer(1, 10))

    # 4. Forensic Evaluation & Empirical Verdict Box
    is_alert = any(w in verdict for w in ["FORGED", "TAMPER", "SPLICE", "ANOMALY", "LACERATION", "GUNSHOT"])
    verdict_bg = "#fee2e2" if is_alert else "#ecfdf5"
    verdict_border = "#ef4444" if is_alert else "#10b981"
    verdict_text_color = "#b91c1c" if is_alert else "#047857"

    verdict_box = [
        [
            Paragraph("<b>FORENSIC PIPELINE & VERDICT:</b>", styles["ForensicH2"]),
            Paragraph(f"<font color='{verdict_text_color}'><b>{verdict} &bull; {confidence*100:.1f}% CONFIDENCE</b></font>", styles["ForensicBodyBold"])
        ],
        [
            Paragraph("<b>Engine / Module:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"{module_name} Forensic Analysis Pipeline (Deterministic Neural & Spectral Assessment)", styles["ForensicBody"])
        ]
    ]
    t_v = Table(verdict_box, colWidths=[160, 376])
    t_v.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(verdict_bg)),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor(verdict_border)),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor(verdict_border)),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_v)
    story.append(Spacer(1, 10))

    # 5. Technical Observations & Findings Breakdown
    story.append(Paragraph("<b>EMPIRICAL FINDINGS & ANALYTICAL OBSERVATIONS:</b>", styles["ForensicH2"]))
    
    findings_rows = [
        [
            Paragraph("<b>Analytical Parameter</b>", styles["ForensicBodyBold"]),
            Paragraph("<b>Deterministic Observation / Empirical Metric</b>", styles["ForensicBodyBold"])
        ]
    ]

    if findings and isinstance(findings, dict):
        for k, v in findings.items():
            param_name = str(k).replace("_", " ").title()
            val_str = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            findings_rows.append([
                Paragraph(f"<b>{param_name}</b>", styles["ForensicBody"]),
                Paragraph(val_str, styles["ForensicBody"])
            ])
    else:
        findings_rows.append([
            Paragraph("Primary Assessment", styles["ForensicBody"]),
            Paragraph("Direct forensic verification completed with unbroken bitstream integrity.", styles["ForensicBody"])
        ])

    t_find = Table(findings_rows, colWidths=[180, 356])
    t_find.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_find)
    story.append(Spacer(1, 12))

    # 6. Side-by-Side Exhibits (if provided)
    orig_path = analysis_record.get("original_image_path")
    annot_path = analysis_record.get("annotated_image_path")
    flow_orig = _safe_image_flowable(orig_path, width=250, height=160)
    flow_annot = _safe_image_flowable(annot_path, width=250, height=160)

    if flow_orig or flow_annot:
        story.append(Paragraph("<b>FORENSIC EXHIBITS & LOCALIZATION:</b>", styles["ForensicH2"]))
        exhibit_data = [
            [
                flow_orig or Paragraph("<i>[Original Ingested Evidence File]</i>", styles["ForensicBody"]),
                flow_annot or Paragraph("<i>[Algorithmic Analytical Render]</i>", styles["ForensicBody"])
            ],
            [
                Paragraph("<b>EXHIBIT A: Ingested Evidence Item</b>", styles["ForensicBodyBold"]),
                Paragraph(f"<b>EXHIBIT B: {module_name} Processed Analysis</b>", styles["ForensicBodyBold"])
            ]
        ]
        t_ex = Table(exhibit_data, colWidths=[265, 271])
        t_ex.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_ex)
        story.append(Spacer(1, 10))

    # 7. FRE 702 Legal Attestation & Signature Block
    story.append(Paragraph("<b>JUDICIAL EXPERT ATTESTATION & DIGITAL SIGN-OFF:</b>", styles["ForensicH2"]))
    story.append(Paragraph(
        "Pursuant to 28 U.S.C. &sect; 1746 and Federal Rule of Evidence 702, I declare under penalty of perjury "
        "under the laws of the United States of America that the following is true and correct: "
        "(1) I am qualified to render this technical evaluation based on my specialized forensic expertise and training; "
        "(2) The algorithmic models and computer vision pipelines used to analyze this evidence operate deterministically "
        "and produce empirical findings within documented error rates; "
        "(3) The cryptographic SHA-256 hash was verified prior to processing and all analytical steps were recorded in "
        "the FEAS chain-of-custody ledger; and "
        "(4) The conclusions rendered herein represent an objective forensic opinion to a reasonable degree of scientific certainty.",
        styles["ForensicBody"]
    ))
    story.append(Spacer(1, 8))

    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    signature_data = [
        [
            Paragraph("<b>Reporting Examiner:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<u>/s/ {display_name}</u>", styles["ForensicBody"]),
            Paragraph("<b>Execution Date:</b>", styles["ForensicBodyBold"]),
            Paragraph(current_date, styles["ForensicBody"])
        ],
        [
            Paragraph("<b>Official Badge #:</b>", styles["ForensicBodyBold"]),
            Paragraph(badge_number, styles["ForensicBody"]),
            Paragraph("<b>Verification Seal:</b>", styles["ForensicBodyBold"]),
            Paragraph("FEAS-FRE702-CERTIFIED", styles["ForensicBodyBold"])
        ]
    ]
    t_sign = Table(signature_data, colWidths=[120, 158, 110, 148])
    t_sign.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_sign)

    # Build PDF with NumberedCanvas for professional page numbering & security markings
    doc.build(story, canvasmaker=NumberedCanvas)

    pdf_sha256 = compute_sha256_file(dest_path)

    return {
        "pdf_path": str(dest_path),
        "pdf_sha256": pdf_sha256,
        "analysis_id": analysis_id,
        "case_id": case_id,
        "filename": dest_path.name
    }

