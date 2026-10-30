"""
Forensic Evidence Analysis System (FEAS) - Batch Triage PDF Report Generator
Produces court-ready consolidated multi-evidence summary and triage reports.
"""

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle
)

from src.config import REPORTS_DIR
from src.db.audit import log_audit_event_sync
from src.reports.template import NumberedCanvas, get_forensic_styles


def build_batch_pdf(batch_data: Dict[str, Any], output_path: str = None) -> Dict[str, Any]:
    """
    Generate an official consolidated batch forensic triage PDF report.
    """
    batch_id = batch_data.get("batch_id", "BATCH-UNKNOWN")
    investigator = batch_data.get("investigator_name", "Forensic Examiner")
    summary = batch_data.get("summary", {})
    items = batch_data.get("items", [])

    if not output_path:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(REPORTS_DIR / f"FEAS_Batch_Triage_{batch_id}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=54
    )

    styles = get_forensic_styles()
    story = []

    # =========================================================================
    # PAGE 1: CONSOLIDATED BATCH TRIAGE SUMMARY
    # =========================================================================
    story.append(Paragraph("FORENSIC EVIDENCE ANALYSIS SYSTEM", styles["ForensicTitle"]))
    story.append(Paragraph(
        "<b>CONSOLIDATED MULTI-EVIDENCE TRIAGE & INTEGRITY REPORT</b>",
        styles["ForensicSubtitle"]
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0f172a"), spaceAfter=12))

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Metadata Header Table
    meta_table_data = [
        [
            Paragraph("<b>Batch Reference ID:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<b>{batch_id}</b>", styles["ForensicCode"]),
            Paragraph("<b>Intake Timestamp:</b>", styles["ForensicBodyBold"]),
            Paragraph(now_utc, styles["ForensicBody"])
        ],
        [
            Paragraph("<b>Lead Examiner:</b>", styles["ForensicBodyBold"]),
            Paragraph(investigator, styles["ForensicBody"]),
            Paragraph("<b>Total Files Processed:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<b>{summary.get('total_files', len(items))} item(s)</b>", styles["ForensicBodyBold"])
        ],
        [
            Paragraph("<b>Tampering Flagged:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<b>{summary.get('tampered_count', 0)} ({summary.get('tamper_rate', 0)*100:.1f}%)</b>", styles["VerdictAlert"] if summary.get('tampered_count', 0) > 0 else styles["ForensicBody"]),
            Paragraph("<b>Suspect Hits:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"<b>{summary.get('suspect_hits_count', 0)} match(es)</b>", styles["ForensicBodyBold"])
        ],
        [
            Paragraph("<b>Trauma / Wounds:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"{summary.get('wound_alerts_count', 0)} detected", styles["ForensicBody"]),
            Paragraph("<b>Ballistics Striae:</b>", styles["ForensicBodyBold"]),
            Paragraph(f"{summary.get('ballistics_alerts_count', 0)} identified", styles["ForensicBody"])
        ]
    ]
    t_meta = Table(meta_table_data, colWidths=[125, 145, 125, 145])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 14))

    # Master Triage Matrix Table
    story.append(Paragraph("<b>Consolidated Evidence Triage Matrix</b>", styles["ForensicH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=8))

    matrix_rows = [
        [
            Paragraph("<b>Case ID / File</b>", styles["ForensicBodyBold"]),
            Paragraph("<b>SHA-256 Digest</b>", styles["ForensicBodyBold"]),
            Paragraph("<b>Forgery / ELA</b>", styles["ForensicBodyBold"]),
            Paragraph("<b>Face / Suspect</b>", styles["ForensicBodyBold"]),
            Paragraph("<b>Trauma / Ballistics</b>", styles["ForensicBodyBold"]),
            Paragraph("<b>Verdict</b>", styles["ForensicBodyBold"])
        ]
    ]

    for item in items:
        cid = item.get("case_id", "N/A")
        fn = item.get("filename") or (item.get("media_info") or {}).get("filename", "evidence")
        sha = item.get("input_sha256", "N/A")
        
        forgery = item.get("forgery") or {}
        is_tamp = forgery.get("is_tampered", False)
        tamp_str = f"TAMPERED ({forgery.get('tamper_score', 0)*100:.0f}%)" if is_tamp else f"Authentic ({forgery.get('tamper_score', 0)*100:.0f}%)"
        
        face = item.get("face") or {}
        if face.get("face_detected"):
            top_m = face.get("top_match") or {}
            face_str = f"Match: {top_m.get('name', 'Known')} ({top_m.get('similarity', 0)*100:.0f}%)" if top_m.get("name") else "Face (No Match)"
        else:
            face_str = "No Face"
            
        wound = item.get("wound") or {}
        ballistics = item.get("ballistics") or {}
        diag_parts = []
        if wound.get("wound_detected"):
            diag_parts.append(f"Wound: {wound.get('wound_type', '').upper()}")
        if ballistics.get("striae_detected"):
            diag_parts.append(f"Cal: {ballistics.get('caliber', '')}")
        diag_str = " | ".join(diag_parts) if diag_parts else "None"

        verdict = item.get("verdict", "AUTHENTIC")

        matrix_rows.append([
            Paragraph(f"<b>{cid}</b><br/><font size='7' color='#475569'>{fn[:20]}</font>", styles["ForensicBody"]),
            Paragraph(f"<font size='6.5'>{sha[:18]}...</font>", styles["ForensicCode"]),
            Paragraph(f"<font color='{'#991b1b' if is_tamp else '#1e293b'}'><b>{tamp_str}</b></font>", styles["ForensicBody"]),
            Paragraph(face_str, styles["ForensicBody"]),
            Paragraph(diag_str, styles["ForensicBody"]),
            Paragraph(f"<b>{verdict}</b>", styles["VerdictAlert"] if is_tamp else styles["ForensicBodyBold"])
        ])

    t_matrix = Table(matrix_rows, colWidths=[95, 95, 95, 95, 95, 65])
    t_matrix.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_matrix)
    story.append(Spacer(1, 15))

    # Examiner Sign-Off
    story.append(KeepTogether([
        Paragraph("<b>BATCH TRIAGE CERTIFICATION & CHAIN-OF-CUSTODY:</b>", styles["ForensicH2"]),
        Paragraph(
            "I hereby verify that the above batch of forensic evidence has been processed under deterministic "
            "Level-1 integrity controls. All individual SHA-256 stream hashes have been verified against the master SQLite WAL ledger.",
            styles["ForensicBody"]
        ),
        Spacer(1, 12),
        Table([
            [Paragraph("<b>Lead Examiner Signature:</b> ___________________________", styles["ForensicBody"]), Paragraph("<b>Date / UTC:</b> " + now_utc[:10], styles["ForensicBody"])]
        ], colWidths=[340, 200])
    ]))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)

    # Compute PDF SHA-256
    hasher = hashlib.sha256()
    with open(output_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    pdf_sha256 = hasher.hexdigest()

    return {
        "pdf_path": output_path,
        "pdf_sha256": pdf_sha256,
        "batch_id": batch_id
    }
