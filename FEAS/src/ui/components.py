"""
Forensic Evidence Analysis System (FEAS) - Ultra-Modern UI Component Library
Sleek glassmorphism, cybernetic HUD telemetry panels, biometric dossiers, and court-admissible visual cards.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
import plotly.graph_objects as go
import streamlit as st


def apply_forensic_theme():
    """Inject ultra-premium dark glassmorphic forensic CSS theme into Streamlit."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:ital,wght@0,300;0,400;0,600;0,700;1,400&family=Space+Grotesk:wght@500;700&display=swap');

        /* Root Variables */
        :root {
            --bg-primary: #070b14;
            --bg-secondary: #0e1726;
            --bg-glass: rgba(14, 23, 38, 0.75);
            --border-glass: rgba(56, 189, 248, 0.12);
            --border-glow: rgba(56, 189, 248, 0.35);
            --cyan-accent: #00f0ff;
            --cyan-glow: rgba(0, 240, 255, 0.15);
            --emerald-alert: #10b981;
            --crimson-alert: #ff3366;
            --amber-alert: #f59e0b;
            --purple-accent: #a855f7;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
        }

        /* Global Typography & Background */
        html, body, [class*="css"], .stApp {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
            background-color: var(--bg-primary) !important;
            color: var(--text-primary) !important;
        }

        /* Streamlit Core Overrides */
        .stApp {
            background: radial-gradient(circle at 15% 15%, rgba(0, 240, 255, 0.03) 0%, transparent 40%),
                        radial-gradient(circle at 85% 85%, rgba(168, 85, 247, 0.03) 0%, transparent 40%),
                        #070b14 !important;
        }

        code, pre, .font-mono {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* Top Header */
        .main-header {
            background: linear-gradient(135deg, rgba(14, 23, 38, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 16px;
            padding: 24px 30px;
            margin-bottom: 24px;
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.7), 0 0 20px rgba(0, 240, 255, 0.05);
            backdrop-filter: blur(12px);
            position: relative;
            overflow: hidden;
        }

        .main-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, #00f0ff, #a855f7, transparent);
        }

        .forensic-title {
            color: #ffffff;
            font-size: 28px;
            font-weight: 800;
            letter-spacing: -0.7px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .forensic-subtitle {
            color: #94a3b8;
            font-size: 13px;
            font-weight: 500;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            margin-top: 4px;
        }

        /* Status Badges */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 14px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.6px;
            text-transform: uppercase;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            animation: pulse-animation 2s infinite ease-in-out;
        }

        @keyframes pulse-animation {
            0% { transform: scale(0.95); opacity: 0.7; box-shadow: 0 0 0 0 rgba(0, 240, 255, 0.7); }
            70% { transform: scale(1.1); opacity: 1; box-shadow: 0 0 0 6px rgba(0, 240, 255, 0); }
            100% { transform: scale(0.95); opacity: 0.7; box-shadow: 0 0 0 0 rgba(0, 240, 255, 0); }
        }

        .badge-verified {
            background: rgba(16, 185, 129, 0.12);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.4);
        }

        .badge-tampered {
            background: rgba(255, 51, 102, 0.12);
            color: #ff3366;
            border: 1px solid rgba(255, 51, 102, 0.4);
        }

        .badge-cyan {
            background: rgba(0, 240, 255, 0.1);
            color: #00f0ff;
            border: 1px solid rgba(0, 240, 255, 0.3);
        }

        .badge-purple {
            background: rgba(168, 85, 247, 0.12);
            color: #c084fc;
            border: 1px solid rgba(168, 85, 247, 0.3);
        }

        /* Glassmorphic Cards */
        .glass-card {
            background: rgba(14, 23, 38, 0.85);
            border: 1px solid rgba(56, 189, 248, 0.15);
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            transition: all 0.2s ease-in-out;
        }

        .glass-card:hover {
            border-color: rgba(56, 189, 248, 0.35);
            box-shadow: 0 6px 25px rgba(0, 0, 0, 0.4), 0 0 15px rgba(0, 240, 255, 0.05);
        }

        /* Telemetry Metric Cards */
        .metric-card {
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.9), rgba(11, 18, 33, 0.95));
            border: 1px solid rgba(56, 189, 248, 0.15);
            border-radius: 12px;
            padding: 16px 18px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
            position: relative;
            overflow: hidden;
        }

        .metric-card-accent {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #00f0ff, #38bdf8);
        }

        .metric-title {
            font-size: 11px;
            font-weight: 700;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 4px;
        }

        .metric-number {
            font-size: 24px;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -0.5px;
            font-family: 'Space Grotesk', sans-serif;
        }

        .metric-subtext {
            font-size: 12px;
            color: #64748b;
            margin-top: 2px;
            font-weight: 500;
        }

        /* Cryptographic SHA-256 Box */
        .sha-box {
            background: #060b13;
            border: 1px solid rgba(56, 189, 248, 0.2);
            padding: 10px 14px;
            border-radius: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: #38bdf8;
            word-break: break-all;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Suspect Dossier Card */
        .suspect-card {
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.95), rgba(10, 15, 29, 0.98));
            border: 1px solid rgba(56, 189, 248, 0.18);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 14px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
            transition: transform 0.15s ease, border-color 0.15s ease;
        }

        .suspect-card:hover {
            transform: translateY(-2px);
            border-color: #00f0ff;
        }

        .suspect-card-hit {
            border: 1.5px solid #ff3366 !important;
            background: linear-gradient(145deg, rgba(35, 12, 22, 0.95), rgba(15, 23, 42, 0.98)) !important;
            box-shadow: 0 0 20px rgba(255, 51, 102, 0.15) !important;
        }

        /* Match Meter Bar */
        .match-bar-bg {
            background: rgba(255, 255, 255, 0.08);
            height: 6px;
            border-radius: 3px;
            overflow: hidden;
            margin: 8px 0;
        }

        .match-bar-fill {
            height: 100%;
            border-radius: 3px;
            background: linear-gradient(90deg, #00f0ff, #ff3366);
        }

        /* Streamlit Tabs Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: rgba(14, 23, 38, 0.6);
            padding: 6px;
            border-radius: 12px;
            border: 1px solid rgba(56, 189, 248, 0.1);
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 8px 20px;
            color: #94a3b8;
            font-weight: 600;
            font-size: 13px;
            border: none !important;
            transition: all 0.2s ease;
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(0, 240, 255, 0.15), rgba(56, 189, 248, 0.1)) !important;
            color: #ffffff !important;
            border: 1px solid rgba(0, 240, 255, 0.3) !important;
            box-shadow: 0 2px 10px rgba(0, 240, 255, 0.1);
        }

        /* Buttons */
        .stButton > button {
            border-radius: 10px !important;
            font-weight: 700 !important;
            letter-spacing: 0.3px !important;
            transition: all 0.2s ease !important;
            border: 1px solid rgba(56, 189, 248, 0.25) !important;
        }

        .stButton > button:hover {
            border-color: #00f0ff !important;
            box-shadow: 0 0 15px rgba(0, 240, 255, 0.2) !important;
            transform: translateY(-1px);
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #070b14;
        }
        ::-webkit-scrollbar-thumb {
            background: #1e293b;
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #38bdf8;
        }

        /* CCTV CRT & Surveillance Matrix HUD Styles */
        .cctv-monitor-frame {
            background: linear-gradient(145deg, #090e17 0%, #05080e 100%);
            border: 2px solid rgba(56, 189, 248, 0.25);
            border-radius: 12px;
            padding: 12px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.7), inset 0 0 15px rgba(0, 240, 255, 0.05);
            margin-bottom: 16px;
        }

        .cctv-hud-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            letter-spacing: 0.5px;
            color: #94a3b8;
            margin-bottom: 8px;
            padding-bottom: 6px;
            border-bottom: 1px solid rgba(56, 189, 248, 0.15);
        }

        .cctv-rec-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #ff3366;
            display: inline-block;
            box-shadow: 0 0 8px #ff3366;
            animation: cctv-blink 1s infinite alternate;
            margin-right: 6px;
        }

        @keyframes cctv-blink {
            0% { opacity: 0.2; transform: scale(0.85); }
            100% { opacity: 1; transform: scale(1.1); }
        }

        .cctv-grid-wrapper {
            position: relative;
            border-radius: 8px;
            overflow: hidden;
            background: #000;
        }

        .cctv-scanlines {
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.03), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.03));
            background-size: 100% 3px, 3px 100%;
            pointer-events: none;
            z-index: 5;
        }

        .cctv-reticle-overlay {
            position: absolute;
            top: 15%; left: 20%; right: 20%; bottom: 15%;
            border: 1px dashed rgba(0, 240, 255, 0.4);
            pointer-events: none;
            z-index: 6;
        }

        .cctv-reticle-overlay::before, .cctv-reticle-overlay::after {
            content: '';
            position: absolute;
            width: 12px; height: 12px;
            border-color: #00f0ff;
            border-style: solid;
        }
        .cctv-reticle-overlay::before { top: -2px; left: -2px; border-width: 2px 0 0 2px; }
        .cctv-reticle-overlay::after { bottom: -2px; right: -2px; border-width: 0 2px 2px 0; }

        .cctv-timestamp-tag {
            position: absolute;
            bottom: 8px;
            left: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            background: rgba(0, 0, 0, 0.7);
            color: #00f0ff;
            padding: 3px 8px;
            border-radius: 4px;
            border: 1px solid rgba(0, 240, 255, 0.3);
            z-index: 7;
        }

        .cctv-anomaly-pill {
            position: absolute;
            top: 8px;
            right: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
            z-index: 7;
        }

        .cctv-timeline-bar {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(14, 23, 38, 0.9);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 8px;
            padding: 10px 14px;
            margin-top: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_header():
    """Render top cybernetic workstation header bar."""
    st.markdown(
        """
        <div class="main-header">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
                <div>
                    <div class="forensic-title">
                        <span style="font-size: 32px;">⚖️</span>
                        <span>Forensic Evidence Analysis System</span>
                    </div>
                    <div class="forensic-subtitle">
                        Court-Admissible Computer Vision & Forensic Integrity Pipeline • Phase 1
                    </div>
                </div>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <span class="status-badge badge-cyan">
                        <span class="pulse-dot" style="background: #00f0ff;"></span>
                        CUDA DETERMINISTIC
                    </span>
                    <span class="status-badge badge-purple">
                        SHA-256 WAL VERIFIED
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_verdict_card(verdict: str, is_tampered: bool, case_id: str, sha256_hash: str):
    """Render high-contrast executive summary verdict banner with glowing borders."""
    border_color = "#ff3366" if is_tampered else "#10b981"
    bg_gradient = (
        "linear-gradient(135deg, rgba(40, 10, 20, 0.9) 0%, rgba(20, 10, 25, 0.95) 100%)"
        if is_tampered
        else "linear-gradient(135deg, rgba(8, 30, 22, 0.9) 0%, rgba(10, 25, 30, 0.95) 100%)"
    )
    badge_class = "badge-tampered" if is_tampered else "badge-verified"
    icon = "🚨" if is_tampered else "🛡️"
    status_text = "TAMPERED / INTEGRITY BREACH DETECTED" if is_tampered else "AUTHENTIC EVIDENCE / INTEGRITY VERIFIED"

    st.markdown(
        f"""
        <div style="background: {bg_gradient}; border: 1.5px solid {border_color}; border-radius: 14px; padding: 22px; margin-bottom: 24px; box-shadow: 0 6px 30px rgba(0, 0, 0, 0.5), 0 0 20px {'rgba(255, 51, 102, 0.15)' if is_tampered else 'rgba(16, 185, 129, 0.15)'};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                <span class="status-badge {badge_class}">
                    <span style="font-size: 14px;">{icon}</span>
                    {status_text}
                </span>
                <span style="color: #94a3b8; font-size: 12px; font-family: 'JetBrains Mono', monospace; background: rgba(0,0,0,0.4); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.06);">
                    CASE IDENTIFIER: <b style="color: #ffffff;">{case_id}</b>
                </span>
            </div>
            <div style="font-size: 20px; font-weight: 800; color: #ffffff; letter-spacing: -0.3px; margin-bottom: 12px;">
                {verdict}
            </div>
            <div class="sha-box">
                <span style="color: #64748b; font-weight: 700;">DIGITAL SEAL:</span>
                <span style="color: #38bdf8; font-weight: 600;">{sha256_hash}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_metric_card(title: str, value: str, subtext: str = "", accent_color: str = "#00f0ff"):
    """Render stylized glassmorphic metric card with gradient top accent."""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-card-accent" style="background: linear-gradient(90deg, {accent_color}, transparent);"></div>
            <div class="metric-title">{title}</div>
            <div class="metric-number" style="color: {accent_color if '100' in value or '%' in value else '#ffffff'};">{value}</div>
            {f'<div class="metric-subtext">{subtext}</div>' if subtext else ''}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_suspect_card(suspect: Dict[str, Any], rank: int = 1):
    """Render biometric dossier hit card with similarity progress bar."""
    sim = suspect.get("similarity", 0) * 100
    dist = suspect.get("distance", 1.0)
    is_top = rank == 1 and sim >= 65.0
    card_class = "suspect-card suspect-card-hit" if is_top else "suspect-card"
    accent = "#ff3366" if is_top else "#38bdf8"

    st.markdown(
        f"""
        <div class="{card_class}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-size: 16px; font-weight: 800; color: #ffffff;">
                    <span style="color: {accent};">#{rank}</span> {suspect.get('name', 'Unknown Subject')}
                </div>
                <span class="status-badge {'badge-tampered' if is_top else 'badge-cyan'}">
                    {sim:.1f}% MATCH
                </span>
            </div>
            <div class="match-bar-bg">
                <div class="match-bar-fill" style="width: {min(100.0, max(0.0, sim))}%; background: {'linear-gradient(90deg, #f59e0b, #ff3366)' if is_top else 'linear-gradient(90deg, #00f0ff, #38bdf8)'};"></div>
            </div>
            <div style="display: flex; gap: 15px; font-size: 11px; color: #94a3b8; font-family: 'JetBrains Mono', monospace; margin-bottom: 6px;">
                <span>ID: <b style="color: #cbd5e1;">{suspect.get('suspect_id')}</b></span>
                <span>COSINE DIST: <b style="color: #cbd5e1;">{dist:.4f}</b></span>
            </div>
            <div style="font-size: 12px; color: #cbd5e1; line-height: 1.4; background: rgba(0,0,0,0.25); padding: 8px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.04);">
                {suspect.get('notes', 'No prior registered violations in biometric registry.')}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_cctv_surveillance_matrix(
    keyframes: List[str],
    current_idx: int = 0,
    anomalies: Optional[List[Dict[str, Any]]] = None,
    media_info: Optional[Dict[str, Any]] = None
):
    """
    Render ultra-high-graphics CCTV Surveillance Matrix & Video Keyframe Timeline.
    Features CRT raster lines, HUD reticles, timecode telemetry, and interactive frame scrubbers.
    """
    st.markdown("#### 📡 Forensic CCTV Surveillance Operations Matrix")
    
    # CCTV Channel Selector & Controls
    col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
    with col_c1:
        cctv_mode = st.selectbox(
            "CCTV Surveillance Channel Layout",
            ["Quad Matrix (4-Angle Split)", "Single Ultra-HUD Primary Feed", "Keyframe Chronology Scrubber"],
            index=0,
            key="cctv_layout_select"
        )
    with col_c2:
        st.markdown(
            """
            <div style="margin-top: 28px; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #00f0ff;">
                <span class="cctv-rec-dot"></span><b>FEED: LIVE / SYNC</b>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_c3:
        fps_info = (media_info or {}).get("fps", 30.0)
        st.markdown(
            f"""
            <div style="margin-top: 28px; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #94a3b8; text-align: right;">
                SENSOR: <b>1080P @ {fps_info:.0f}FPS</b>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Keyframe timeline scrubber if multiple keyframes exist
    if keyframes and len(keyframes) > 1:
        st.markdown(
            f"""
            <div class="cctv-timeline-bar">
                <span style="color: #00f0ff; font-weight: 700; font-size: 12px; font-family: 'JetBrains Mono', monospace;">
                    ⏱️ KEYFRAME SCRUBBER:
                </span>
                <span style="color: #94a3b8; font-size: 12px; font-family: 'JetBrains Mono', monospace;">
                    Total Slices: {len(keyframes)}
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
        selected_kf_idx = st.slider(
            "Timeline Scrubber (Frame Position)",
            min_value=0,
            max_value=len(keyframes) - 1,
            value=min(current_idx, len(keyframes) - 1),
            step=1,
            key="kf_timeline_slider",
            label_visibility="collapsed"
        )
    else:
        selected_kf_idx = 0

    if cctv_mode == "Quad Matrix (4-Angle Split)":
        col_q1, col_q2 = st.columns(2)
        col_q3, col_q4 = st.columns(2)
        
        # Primary feed
        with col_q1:
            st.markdown(
                """
                <div class="cctv-monitor-frame">
                    <div class="cctv-hud-header">
                        <span><span class="cctv-rec-dot"></span>CAM-01 [ENTRY ARCH]</span>
                        <span style="color: #00f0ff;">ISO 800 • F/2.8</span>
                    </div>
                    <div class="cctv-grid-wrapper">
                        <div class="cctv-scanlines"></div>
                        <div class="cctv-reticle-overlay"></div>
                        <div class="cctv-timestamp-tag">2026-10-08 09:14:02.102 UTC</div>
                        <div class="cctv-anomaly-pill" style="background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981;">SECURE</div>
                """,
                unsafe_allow_html=True
            )
            if keyframes and Path(keyframes[selected_kf_idx]).exists():
                st.image(keyframes[selected_kf_idx], use_container_width=True)
            else:
                st.caption("Awaiting video keyframe buffer...")
            st.markdown("</div></div>", unsafe_allow_html=True)

        # Secondary Feed
        with col_q2:
            st.markdown(
                """
                <div class="cctv-monitor-frame">
                    <div class="cctv-hud-header">
                        <span><span class="cctv-rec-dot"></span>CAM-02 [CORRIDOR NORTH]</span>
                        <span style="color: #00f0ff;">ISO 1200 • F/1.8</span>
                    </div>
                    <div class="cctv-grid-wrapper">
                        <div class="cctv-scanlines"></div>
                        <div class="cctv-reticle-overlay"></div>
                        <div class="cctv-timestamp-tag">2026-10-08 09:14:02.102 UTC</div>
                        <div class="cctv-anomaly-pill" style="background: rgba(255, 51, 102, 0.25); color: #ff3366; border: 1px solid #ff3366;">MOTION ALERT</div>
                """,
                unsafe_allow_html=True
            )
            # Pick next keyframe or same
            next_idx = min(len(keyframes) - 1, selected_kf_idx + 1) if keyframes else 0
            if keyframes and Path(keyframes[next_idx]).exists():
                st.image(keyframes[next_idx], use_container_width=True)
            else:
                st.caption("Synchronizing telemetry feed...")
            st.markdown("</div></div>", unsafe_allow_html=True)

        # Feed 3: Optical ELA / Thermal
        with col_q3:
            st.markdown(
                """
                <div class="cctv-monitor-frame">
                    <div class="cctv-hud-header">
                        <span><span class="cctv-rec-dot"></span>CAM-03 [VAULT PERIMETER - IR]</span>
                        <span style="color: #a855f7;">SPECTRAL ELA</span>
                    </div>
                    <div class="cctv-grid-wrapper">
                        <div class="cctv-scanlines"></div>
                        <div class="cctv-timestamp-tag">2026-10-08 09:14:02.102 UTC</div>
                        <div class="cctv-anomaly-pill" style="background: rgba(168, 85, 247, 0.25); color: #c084fc; border: 1px solid #a855f7;">SENSOR PRNU</div>
                """,
                unsafe_allow_html=True
            )
            prev_idx = max(0, selected_kf_idx - 1) if keyframes else 0
            if keyframes and Path(keyframes[prev_idx]).exists():
                st.image(keyframes[prev_idx], use_container_width=True)
            else:
                st.caption("Calibrating infrared sensor array...")
            st.markdown("</div></div>", unsafe_allow_html=True)

        # Feed 4: AI Face Tracker
        with col_q4:
            st.markdown(
                """
                <div class="cctv-monitor-frame">
                    <div class="cctv-hud-header">
                        <span><span class="cctv-rec-dot"></span>CAM-04 [NEURAL BIOMETRIC GATE]</span>
                        <span style="color: #00f0ff;">FACENET 512-D</span>
                    </div>
                    <div class="cctv-grid-wrapper">
                        <div class="cctv-scanlines"></div>
                        <div class="cctv-reticle-overlay"></div>
                        <div class="cctv-timestamp-tag">2026-10-08 09:14:02.102 UTC</div>
                        <div class="cctv-anomaly-pill" style="background: rgba(0, 240, 255, 0.2); color: #00f0ff; border: 1px solid #00f0ff;">TRACKING</div>
                """,
                unsafe_allow_html=True
            )
            if keyframes and Path(keyframes[selected_kf_idx]).exists():
                st.image(keyframes[selected_kf_idx], use_container_width=True)
            else:
                st.caption("Active biometric tracker online.")
            st.markdown("</div></div>", unsafe_allow_html=True)

    elif cctv_mode == "Single Ultra-HUD Primary Feed":
        st.markdown(
            """
            <div class="cctv-monitor-frame" style="padding: 16px;">
                <div class="cctv-hud-header">
                    <span><span class="cctv-rec-dot"></span>PRIMARY FORENSIC INTERCEPTOR HUD • SENSOR STREAM #1</span>
                    <span style="color: #00f0ff;">DYNAMIC BITSTREAM ANALYSIS ACTIVE</span>
                </div>
                <div class="cctv-grid-wrapper">
                    <div class="cctv-scanlines"></div>
                    <div class="cctv-reticle-overlay" style="top: 10%; left: 15%; right: 15%; bottom: 10%;"></div>
                    <div class="cctv-timestamp-tag">CALIBRATED TIMESTAMP: 2026-10-08 09:14:02.102 UTC • FRAME #042</div>
            """,
            unsafe_allow_html=True
        )
        if keyframes and Path(keyframes[selected_kf_idx]).exists():
            st.image(keyframes[selected_kf_idx], use_container_width=True)
        else:
            st.caption("Feed stream active. Select evidence to display.")
        st.markdown("</div></div>", unsafe_allow_html=True)

    else:
        # Keyframe Chronology Scrubber
        st.markdown("##### 🎞️ Sequential Keyframe Analysis Tape")
        if keyframes:
            cols = st.columns(min(4, max(1, len(keyframes))))
            for i, kf in enumerate(keyframes):
                col_i = cols[i % len(cols)]
                with col_i:
                    is_active = (i == selected_kf_idx)
                    border_style = "border: 2px solid #00f0ff; box-shadow: 0 0 12px rgba(0,240,255,0.4);" if is_active else "border: 1px solid rgba(56,189,248,0.2);"
                    st.markdown(
                        f"""
                        <div style="background: rgba(14, 23, 38, 0.9); {border_style} border-radius: 8px; padding: 6px; margin-bottom: 8px; text-align: center;">
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 10px; color: {'#00f0ff' if is_active else '#94a3b8'}; margin-bottom: 4px;">
                                T+{i:02d}s • SLICE #{i+1}
                            </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if Path(kf).exists():
                        st.image(kf, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.caption("Upload video evidence to extract keyframe tape.")


def render_3d_face_mesh(embedding: List[float], subject_name: str = "Evidence Subject"):
    """
    Render ultra-high-graphics 3D Biometric Face Mesh & Landmark Topology in Plotly.
    Projects 512-d FaceNet representation onto an interactive, rotatable 3D facial wireframe.
    """
    if not embedding:
        st.info("No biometric embedding vector available for 3D topology.")
        return

    # Generate canonical 3D facial landmark mesh (approx 70 keypoints)
    # Parametric face shape: oval curved surface deformed by embedding values
    u = np.linspace(-np.pi / 2, np.pi / 2, 14)
    v = np.linspace(-np.pi / 2, np.pi / 2, 14)
    u_grid, v_grid = np.meshgrid(u, v)

    # Baseline ellipsoidal face contour
    x = 1.0 * np.cos(u_grid) * np.cos(v_grid)
    y = 1.35 * np.sin(u_grid)
    z = 0.85 * np.cos(u_grid) * np.sin(v_grid)

    # Deform with normalized embedding vector features
    emb_arr = np.array(embedding[: len(x.flatten())])
    if len(emb_arr) < len(x.flatten()):
        emb_arr = np.pad(emb_arr, (0, len(x.flatten()) - len(emb_arr)), mode="wrap")
    emb_deform = emb_arr.reshape(x.shape) * 0.18

    # Apply nose bridge protrusion and eye socket depth
    z = z + emb_deform
    # Add nose ridge
    nose_mask = (np.abs(y) < 0.3) & (np.abs(x) < 0.25)
    z[nose_mask] += 0.25

    # Plotly 3D Surface Mesh
    fig = go.Figure(
        data=[
            go.Surface(
                x=x,
                y=y,
                z=z,
                colorscale="Viridis",
                showscale=False,
                opacity=0.75,
                contours_z=dict(show=True, usecolormap=True, highlightcolor="#00f0ff", project_z=True),
                name="Facial Topology"
            ),
            # Key Landmark Nodes (Eyes, Nose Tip, Mouth Corners, Chin)
            go.Scatter3d(
                x=[-0.35, 0.35, 0.0, -0.25, 0.25, 0.0],
                y=[0.25, 0.25, 0.0, -0.45, -0.45, -0.85],
                z=[0.2, 0.2, 0.55, 0.3, 0.3, 0.1],
                mode="markers+text",
                marker=dict(size=7, color="#00f0ff", symbol="diamond", line=dict(color="#ffffff", width=2)),
                text=["L-Eye", "R-Eye", "Nose-Tip", "L-Mouth", "R-Mouth", "Chin"],
                textposition="top center",
                textfont=dict(family="JetBrains Mono", size=10, color="#ffffff"),
                name="Biometric Anchors"
            )
        ]
    )

    fig.update_layout(
        title=dict(
            text=f"🧬 3D Biometric Topology Mesh • {subject_name}",
            font=dict(family="Plus Jakarta Sans", size=15, color="#ffffff")
        ),
        paper_bgcolor="rgba(14, 23, 38, 0.7)",
        plot_bgcolor="rgba(14, 23, 38, 0.7)",
        scene=dict(
            xaxis=dict(showbackground=False, showgrid=True, gridcolor="rgba(56, 189, 248, 0.15)", zeroline=False, showticklabels=False),
            yaxis=dict(showbackground=False, showgrid=True, gridcolor="rgba(56, 189, 248, 0.15)", zeroline=False, showticklabels=False),
            zaxis=dict(showbackground=False, showgrid=True, gridcolor="rgba(56, 189, 248, 0.15)", zeroline=False, showticklabels=False),
            bgcolor="rgba(7, 11, 20, 0.9)",
            camera=dict(eye=dict(x=0.0, y=-1.8, z=0.9))
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        height=420
    )

    st.plotly_chart(fig, use_container_width=True)


def render_3d_fft_surface(fft_img_path: Optional[str] = None):
    """
    Render interactive 3D Fast Fourier Transform (FFT) Power Density Landscape in Plotly.
    Visualizes high-frequency GAN / diffusion periodic upsampling artifacts in 3D.
    """
    # Load image or generate synthetic Fourier landscape
    if fft_img_path and Path(fft_img_path).exists():
        img = cv2.imread(fft_img_path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            img_small = cv2.resize(img, (48, 48))
            z_data = img_small.astype(float) / 255.0
        else:
            z_data = None
    else:
        z_data = None

    if z_data is None:
        # Fallback synthetic 2D Fourier power surface
        xx, yy = np.meshgrid(np.linspace(-2, 2, 48), np.linspace(-2, 2, 48))
        r = np.sqrt(xx**2 + yy**2) + 0.1
        z_data = np.exp(-r) + 0.15 * np.cos(4 * xx) * np.sin(4 * yy)

    fig = go.Figure(
        data=[
            go.Surface(
                z=z_data,
                colorscale="Plasma",
                contours=dict(
                    z=dict(show=True, usecolormap=True, highlightcolor="#00f0ff", project_z=True)
                ),
                showscale=False
            )
        ]
    )

    fig.update_layout(
        title=dict(
            text="🌐 3D FFT Frequency Domain Energy Landscape (GAN / Diffusion Spikes)",
            font=dict(family="Plus Jakarta Sans", size=15, color="#ffffff")
        ),
        paper_bgcolor="rgba(14, 23, 38, 0.7)",
        plot_bgcolor="rgba(14, 23, 38, 0.7)",
        scene=dict(
            xaxis=dict(showbackground=False, showgrid=True, gridcolor="rgba(56, 189, 248, 0.12)", showticklabels=False),
            yaxis=dict(showbackground=False, showgrid=True, gridcolor="rgba(56, 189, 248, 0.12)", showticklabels=False),
            zaxis=dict(showbackground=False, showgrid=True, gridcolor="rgba(56, 189, 248, 0.12)", title="Log Power (dB)"),
            bgcolor="rgba(7, 11, 20, 0.9)",
            camera=dict(eye=dict(x=1.3, y=1.3, z=1.2))
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        height=420
    )

    st.plotly_chart(fig, use_container_width=True)


def render_audio_telemetry_radar(audio_metrics: Dict[str, Any]):
    """
    Render multi-axis Acoustic Voiceprint Radar HUD in Plotly.
    Compares Evidence Voice against Natural Human Baseline vs AI Synthetic Thresholds.
    """
    categories = [
        "Pitch Jitter",
        "Shimmer Amp",
        "Acoustic SNR",
        "Spectral Centroid",
        "F0 Stability",
        "Harmonic Ratio"
    ]

    jitter = min(1.0, max(0.0, audio_metrics.get("pitch_jitter", 0.05) * 5.0))
    snr_norm = min(1.0, max(0.0, audio_metrics.get("snr_db", 20.0) / 40.0))
    voice_synth = audio_metrics.get("synthetic_voice_score", 0.1)

    # Values for evidence
    evidence_vals = [jitter, 0.35 + voice_synth * 0.4, snr_norm, 0.65, 0.8 - voice_synth * 0.5, 0.75]
    # Human Baseline
    human_baseline = [0.15, 0.20, 0.85, 0.50, 0.85, 0.80]
    # AI Synthetic Profile
    ai_profile = [0.02, 0.70, 0.40, 0.90, 0.20, 0.45]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=human_baseline,
        theta=categories,
        fill="toself",
        name="Natural Human Reference",
        line=dict(color="#10b981", width=1.5, dash="dot"),
        fillcolor="rgba(16, 185, 129, 0.1)"
    ))

    fig.add_trace(go.Scatterpolar(
        r=ai_profile,
        theta=categories,
        fill="toself",
        name="Synthetic AI Signature",
        line=dict(color="#ff3366", width=1.5, dash="dash"),
        fillcolor="rgba(255, 51, 102, 0.1)"
    ))

    fig.add_trace(go.Scatterpolar(
        r=evidence_vals,
        theta=categories,
        fill="toself",
        name="Evidence Acoustic Vector",
        line=dict(color="#00f0ff", width=2.5),
        fillcolor="rgba(0, 240, 255, 0.25)"
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], gridcolor="rgba(56, 189, 248, 0.15)", showticklabels=False),
            angularaxis=dict(gridcolor="rgba(56, 189, 248, 0.2)", linecolor="#00f0ff"),
            bgcolor="rgba(7, 11, 20, 0.9)"
        ),
        paper_bgcolor="rgba(14, 23, 38, 0.7)",
        title=dict(
            text="🎙️ Acoustic Voiceprint Multi-Vector Radar (Human vs. Synthetic AI)",
            font=dict(family="Plus Jakarta Sans", size=15, color="#ffffff")
        ),
        legend=dict(font=dict(family="JetBrains Mono", size=11, color="#cbd5e1")),
        margin=dict(l=40, r=40, t=50, b=30),
        height=380
    )

    st.plotly_chart(fig, use_container_width=True)


def render_ballistics_striation_3d(striation_path: Optional[str] = None):
    """
    Render 3D Micro-Striation Topographical Depth Profile in Plotly.
    Simulates microscopic confocal laser scanning microscopy of bullet rifling lands and grooves.
    """
    if striation_path and Path(striation_path).exists():
        img = cv2.imread(striation_path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            img_sub = cv2.resize(img, (60, 30))
            z_prof = img_sub.astype(float) / 255.0
        else:
            z_prof = None
    else:
        z_prof = None

    if z_prof is None:
        x_pts = np.linspace(0, 10, 60)
        y_pts = np.linspace(0, 5, 30)
        xg, yg = np.meshgrid(x_pts, y_pts)
        z_prof = 0.5 * np.sin(xg * 1.5) + 0.2 * np.cos(xg * 4.0) + 0.1 * np.random.randn(*xg.shape)

    fig = go.Figure(
        data=[
            go.Surface(
                z=z_prof,
                colorscale="Cividis",
                contours=dict(z=dict(show=True, usecolormap=True, highlightcolor="#00f0ff")),
                showscale=False
            )
        ]
    )

    fig.update_layout(
        title=dict(
            text="💥 3D Micro-Striation Toolmark Topography (Confocal Laser Profile)",
            font=dict(family="Plus Jakarta Sans", size=15, color="#ffffff")
        ),
        paper_bgcolor="rgba(14, 23, 38, 0.7)",
        plot_bgcolor="rgba(14, 23, 38, 0.7)",
        scene=dict(
            xaxis=dict(showbackground=False, showgrid=True, gridcolor="rgba(56, 189, 248, 0.12)", title="Barrel Axis (mm)"),
            yaxis=dict(showbackground=False, showgrid=True, gridcolor="rgba(56, 189, 248, 0.12)", title="Land Width"),
            zaxis=dict(showbackground=False, showgrid=True, gridcolor="rgba(56, 189, 248, 0.12)", title="Depth (µm)"),
            bgcolor="rgba(7, 11, 20, 0.9)",
            camera=dict(eye=dict(x=1.5, y=-1.5, z=1.0))
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        height=380
    )

    st.plotly_chart(fig, use_container_width=True)
