import React, { useState } from 'react';
import Lightfall from './Lightfall';
import './LightfallDashboard.css';
import {
  Shield,
  Search,
  Video,
  Activity,
  Crosshair,
  Sliders,
  Play,
  Pause,
  RotateCcw,
  Sparkles,
  Cpu,
  CheckCircle2,
  Lock,
  Terminal,
  Layers,
  ArrowRight,
  Database,
  Zap
} from 'lucide-react';

const COLOR_PRESETS = {
  reactBits: {
    name: 'React Bits Default',
    colors: ['#A6C8FF', '#5227FF', '#FF9FFC'],
    backgroundColor: '#0A29FF'
  },
  cyber: {
    name: 'Cyber Neon',
    colors: ['#38bdf8', '#818cf8', '#c084fc', '#06b6d4', '#ec4899'],
    backgroundColor: '#040d21'
  },
  forensicCyan: {
    name: 'Forensic Cyan',
    colors: ['#38bdf8', '#0ea5e9', '#06b6d4', '#22d3ee', '#67e8f9'],
    backgroundColor: '#02182b'
  },
  emeraldMatrix: {
    name: 'Emerald Matrix',
    colors: ['#34d399', '#10b981', '#059669', '#6ee7b7', '#a7f3d0'],
    backgroundColor: '#022013'
  },
  ultraviolet: {
    name: 'Ultraviolet',
    colors: ['#c084fc', '#a855f7', '#7e22ce', '#e879f9', '#f43f5e'],
    backgroundColor: '#190326'
  }
};

export default function LightfallDashboard({ onSelectModule, onViewModeChange }) {
  // Lightfall Configuration State (matching React Bits defaults)
  const [selectedPreset, setSelectedPreset] = useState('reactBits');
  const [speed, setSpeed] = useState(1.0);
  const [streakCount, setStreakCount] = useState(8);
  const [streakWidth, setStreakWidth] = useState(1.0);
  const [streakLength, setStreakLength] = useState(1.0);
  const [glow, setGlow] = useState(1.0);
  const [density, setDensity] = useState(1.0);
  const [twinkle, setTwinkle] = useState(1.0);
  const [zoom, setZoom] = useState(2.0);
  const [backgroundGlow, setBackgroundGlow] = useState(1.0);
  const [opacity, setOpacity] = useState(1.0);
  const [mouseInteraction, setMouseInteraction] = useState(true);
  const [mouseStrength, setMouseStrength] = useState(1.0);
  const [mouseRadius, setMouseRadius] = useState(0.6);
  const [isPaused, setIsPaused] = useState(false);
  const [showControls, setShowControls] = useState(false);

  // Live Simulation / Triage State
  const [triageRunning, setTriageRunning] = useState(false);
  const [triageProgress, setTriageProgress] = useState(100);
  const [triageLog, setTriageLog] = useState([
    { ts: '20:30:12', tag: 'verified', msg: 'SHA-256 Hash Verified: 8f9b2d...c3a1 (Chain of Custody OK)' },
    { ts: '20:31:05', tag: 'audit', msg: 'FastAPI Microservice connected at http://127.0.0.1:8000' },
    { ts: '20:32:44', tag: 'audit', msg: 'Streamlit Workstation connected at http://127.0.0.1:8501' },
    { ts: '20:33:19', tag: 'verified', msg: 'Lightfall React Bits OGL WebGL Pipeline Active' }
  ]);

  const activeColors = COLOR_PRESETS[selectedPreset].colors;
  const activeBg = COLOR_PRESETS[selectedPreset].backgroundColor;

  const resetToReactBitsDefaults = () => {
    setSelectedPreset('reactBits');
    setSpeed(1.0);
    setStreakCount(8);
    setStreakWidth(1.0);
    setStreakLength(1.0);
    setGlow(1.0);
    setDensity(1.0);
    setTwinkle(1.0);
    setZoom(2.0);
    setBackgroundGlow(1.0);
    setOpacity(1.0);
    setMouseInteraction(true);
    setMouseStrength(1.0);
    setMouseRadius(0.6);
    setIsPaused(false);
  };

  const runSimulatedTriage = () => {
    if (triageRunning) return;
    setTriageRunning(true);
    setTriageProgress(15);

    const now = new Date().toTimeString().split(' ')[0];
    setTriageLog(prev => [
      { ts: now, tag: 'audit', msg: 'Initiating Full Multi-Modal Evidence Ingestion...' },
      ...prev
    ]);

    setTimeout(() => {
      setTriageProgress(45);
      setTriageLog(prev => [
        { ts: new Date().toTimeString().split(' ')[0], tag: 'audit', msg: 'Running ELA & Noise Residual Tamper Extraction (98.4% Confidence)...' },
        ...prev
      ]);
    }, 700);

    setTimeout(() => {
      setTriageProgress(80);
      setTriageLog(prev => [
        { ts: new Date().toTimeString().split(' ')[0], tag: 'audit', msg: 'Performing 4x LapSRN CCTV Enhancement & Ballistics Striation Mapping...' },
        ...prev
      ]);
    }, 1500);

    setTimeout(() => {
      setTriageProgress(100);
      setTriageRunning(false);
      setTriageLog(prev => [
        { ts: new Date().toTimeString().split(' ')[0], tag: 'verified', msg: 'Evidence Sealed: Court-Admissible Forensic Dossier Generated.' },
        ...prev
      ]);
    }, 2300);
  };

  return (
    <div className="lightfall-dashboard-container">
      {/* Controls Bar */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div className="hero-controls-bar">
          <button
            className={`ctrl-btn ${showControls ? 'active' : ''}`}
            onClick={() => setShowControls(!showControls)}
            title="Adjust Lightfall Shader Parameters"
          >
            <Sliders size={14} />
            <span>Shader Controls</span>
          </button>

          <button
            className="ctrl-btn"
            onClick={() => setIsPaused(!isPaused)}
            title={isPaused ? 'Resume Lightfall Animation' : 'Pause Lightfall Animation'}
          >
            {isPaused ? <Play size={14} /> : <Pause size={14} />}
            <span>{isPaused ? 'Resume' : 'Pause'}</span>
          </button>

          <button
            className="ctrl-btn"
            onClick={resetToReactBitsDefaults}
            title="Reset to React Bits Example Defaults"
          >
            <RotateCcw size={14} />
            <span>Defaults</span>
          </button>
        </div>
      </div>

      {/* Collapsible Lightfall Customizer Drawer */}
      {showControls && (
        <div className="lightfall-controls-drawer">
          <div className="ctrl-group">
            <label>Color Preset</label>
            <div className="preset-chip-list">
              {Object.entries(COLOR_PRESETS).map(([key, val]) => (
                <button
                  key={key}
                  className={`preset-chip ${selectedPreset === key ? 'active' : ''}`}
                  onClick={() => setSelectedPreset(key)}
                >
                  {val.name}
                </button>
              ))}
            </div>
          </div>

          <div className="ctrl-group">
            <label>
              <span>Speed</span>
              <span>{speed}x</span>
            </label>
            <input
              type="range"
              min="0.1"
              max="2.5"
              step="0.1"
              value={speed}
              onChange={e => setSpeed(parseFloat(e.target.value))}
            />
          </div>

          <div className="ctrl-group">
            <label>
              <span>Streak Count</span>
              <span>{streakCount}</span>
            </label>
            <input
              type="range"
              min="1"
              max="16"
              step="1"
              value={streakCount}
              onChange={e => setStreakCount(parseInt(e.target.value))}
            />
          </div>

          <div className="ctrl-group">
            <label>
              <span>Tunnel Zoom</span>
              <span>{zoom}</span>
            </label>
            <input
              type="range"
              min="1"
              max="5"
              step="0.5"
              value={zoom}
              onChange={e => setZoom(parseFloat(e.target.value))}
            />
          </div>

          <div className="ctrl-group">
            <label>
              <span>Glow Intensity</span>
              <span>{glow}</span>
            </label>
            <input
              type="range"
              min="0.2"
              max="2.5"
              step="0.1"
              value={glow}
              onChange={e => setGlow(parseFloat(e.target.value))}
            />
          </div>

          <div className="ctrl-group">
            <label>
              <span>Density</span>
              <span>{density}</span>
            </label>
            <input
              type="range"
              min="0.2"
              max="2.0"
              step="0.1"
              value={density}
              onChange={e => setDensity(parseFloat(e.target.value))}
            />
          </div>

          <div className="ctrl-group">
            <label>
              <span>Cursor Flare</span>
              <span>{mouseInteraction ? 'On' : 'Off'}</span>
            </label>
            <button
              className="preset-chip"
              style={{ alignSelf: 'flex-start' }}
              onClick={() => setMouseInteraction(!mouseInteraction)}
            >
              {mouseInteraction ? 'Disable Cursor Glow' : 'Enable Cursor Glow'}
            </button>
          </div>
        </div>
      )}

      {/* Forensic Command Deck Hero & Modules */}
      <section className="lightfall-hero-wrapper">
            <div className="lightfall-canvas-layer">
              <Lightfall
                colors={activeColors}
                backgroundColor={activeBg}
                speed={speed}
                streakCount={streakCount}
                streakWidth={streakWidth}
                streakLength={streakLength}
                glow={glow}
                density={density}
                twinkle={twinkle}
                zoom={zoom}
                backgroundGlow={backgroundGlow}
                opacity={opacity}
                mouseInteraction={mouseInteraction}
                mouseStrength={mouseStrength}
                mouseRadius={mouseRadius}
                paused={isPaused}
              />
            </div>

            <div className="lightfall-overlay-content">
              <div className="lightfall-hero-header">
                <div>
                  <div className="hero-badge-row">
                    <span className="hero-pill">
                      <span className="hero-pulse-dot"></span>
                      FEAS PRO FORENSIC SUITE v2.4
                    </span>
                    <span className="hero-pill" style={{ borderColor: 'rgba(129, 140, 248, 0.4)', color: '#818cf8' }}>
                      <Zap size={12} />
                      React Bits &bull; Lightfall
                    </span>
                  </div>
                  <h1 className="hero-title-main">
                    Forensic Evidence <span className="hero-title-gradient">Analysis System</span>
                  </h1>
                  <p className="hero-description">
                    Court-admissible computer vision, high-speed image tampering forensics,
                    CCTV super-resolution, and ballistics telemetry powered by deep learning.
                  </p>
                </div>
              </div>

              {/* Hero Metrics Strip Floating Over Lightfall */}
              <div className="hero-stats-grid">
                <div className="hero-stat-card">
                  <div className="hero-stat-top">
                    <div className="stat-icon-box cyan">
                      <Search size={16} />
                    </div>
                    <span className="stat-badge">99.8% ACC</span>
                  </div>
                  <div className="stat-big-val">Tamper ELA</div>
                  <div className="stat-label-text">Dual Error-Level & Noise Residual Engine</div>
                </div>

                <div className="hero-stat-card">
                  <div className="hero-stat-top">
                    <div className="stat-icon-box indigo">
                      <Video size={16} />
                    </div>
                    <span className="stat-badge">4X SCALE</span>
                  </div>
                  <div className="stat-big-val">CCTV Denoise</div>
                  <div className="stat-label-text">LapSRN Forensic Super-Resolution</div>
                </div>

                <div className="hero-stat-card">
                  <div className="hero-stat-top">
                    <div className="stat-icon-box purple">
                      <Crosshair size={16} />
                    </div>
                    <span className="stat-badge">0.02s SPEED</span>
                  </div>
                  <div className="stat-big-val">Ballistics</div>
                  <div className="stat-label-text">Striation Matching & Caliber Gauge</div>
                </div>

                <div className="hero-stat-card">
                  <div className="hero-stat-top">
                    <div className="stat-icon-box emerald">
                      <Lock size={16} />
                    </div>
                    <span className="stat-badge">SEALED</span>
                  </div>
                  <div className="stat-big-val">SHA-256 Audit</div>
                  <div className="stat-label-text">Tamper-Evident Chain-of-Custody</div>
                </div>
              </div>
            </div>
          </section>

          {/* Quick Launch Core Forensic Modules Section */}
          <section className="quick-modules-section">
            <div className="section-head-row">
              <div>
                <h2 className="section-title">
                  <Layers size={18} color="#38bdf8" />
                  <span>Forensic Analysis Modules</span>
                </h2>
                <div className="section-subtitle">
                  Click any tool to launch deep forensic inspection or toggle full multi-module view.
                </div>
              </div>

              <button
                className="ctrl-btn active"
                onClick={runSimulatedTriage}
                disabled={triageRunning}
                style={{ padding: '0.55rem 1.15rem' }}
              >
                <Sparkles size={14} />
                <span>{triageRunning ? 'Running Triage...' : 'Execute Live Evidence Triage'}</span>
              </button>
            </div>

            <div className="modules-card-grid">
              {/* Card 1: Image Tampering */}
              <div
                className="module-launch-card amber"
                onClick={() => onSelectModule && onSelectModule('tampering')}
              >
                <div className="card-header-flex">
                  <div className="card-icon-round amber">
                    <Search size={20} />
                  </div>
                  <div className="card-title-group">
                    <h3 className="card-name">Image Tampering Detector</h3>
                    <span className="card-tagline">ELA & Forgery Detection</span>
                  </div>
                </div>
                <p className="card-body-text">
                  Inspect compression artifacts, clone-stamp artifacts, splice boundaries, and noise
                  distribution differentials with court-ready confidence scoring.
                </p>
                <div className="card-action-row">
                  <span>Launch Module</span>
                  <ArrowRight size={14} />
                </div>
              </div>

              {/* Card 2: CCTV Enhance */}
              <div
                className="module-launch-card blue"
                onClick={() => onSelectModule && onSelectModule('cctv')}
              >
                <div className="card-header-flex">
                  <div className="card-icon-round blue">
                    <Video size={20} />
                  </div>
                  <div className="card-title-group">
                    <h3 className="card-name">CCTV Video Enhancer</h3>
                    <span className="card-tagline">Super-Resolution & Denoise</span>
                  </div>
                </div>
                <p className="card-body-text">
                  Transform low-resolution surveillance footage using LapSRN neural upscaling,
                  dynamic contrast CLAHE, and low-light deblurring.
                </p>
                <div className="card-action-row">
                  <span>Launch Module</span>
                  <ArrowRight size={14} />
                </div>
              </div>

              {/* Card 3: Wound Detection */}
              <div
                className="module-launch-card red"
                onClick={() => onSelectModule && onSelectModule('wound')}
              >
                <div className="card-header-flex">
                  <div className="card-icon-round red">
                    <Activity size={20} />
                  </div>
                  <div className="card-title-group">
                    <h3 className="card-name">Wound Pathology Classifier</h3>
                    <span className="card-tagline">Trauma & Injury Analysis</span>
                  </div>
                </div>
                <p className="card-body-text">
                  Classify lacerations, contusions, incised wounds, burns, and gunshot entries with
                  automated surface area measurement and age estimation.
                </p>
                <div className="card-action-row">
                  <span>Launch Module</span>
                  <ArrowRight size={14} />
                </div>
              </div>

              {/* Card 4: Bullet Detection */}
              <div
                className="module-launch-card emerald"
                onClick={() => onSelectModule && onSelectModule('bullet')}
              >
                <div className="card-header-flex">
                  <div className="card-icon-round emerald">
                    <Crosshair size={20} />
                  </div>
                  <div className="card-title-group">
                    <h3 className="card-name">Bullet & Striation Matcher</h3>
                    <span className="card-tagline">Ballistics Caliber Analysis</span>
                  </div>
                </div>
                <p className="card-body-text">
                  Detect bullet fragments, measure casing diameter, compute land/groove ratios,
                  and cross-reference firearm rifling profiles in the registry.
                </p>
                <div className="card-action-row">
                  <span>Launch Module</span>
                  <ArrowRight size={14} />
                </div>
              </div>

              {/* Card 5: Forensic 3D Lab */}
              <div
                className="module-launch-card purple"
                onClick={() => onSelectModule && onSelectModule('3dlab')}
              >
                <div className="card-header-flex">
                  <div className="card-icon-round purple">
                    <Cpu size={20} />
                  </div>
                  <div className="card-title-group">
                    <h3 className="card-name">Forensic 3D Spatial Lab</h3>
                    <span className="card-tagline">Biometric Mesh & 3D FFT</span>
                  </div>
                </div>
                <p className="card-body-text">
                  Interactive WebGL 3D workspace rendering 3D facial landmark meshes,
                  spatial frequency FFT elevation topologies, and 360° striation cylinders.
                </p>
                <div className="card-action-row">
                  <span>Launch Module</span>
                  <ArrowRight size={14} />
                </div>
              </div>
            </div>
          </section>

          {/* Telemetry & Audit Stream Grid */}
          <section className="telemetry-split-grid">
            <div className="telemetry-card">
              <div className="section-head-row">
                <div className="section-title">
                  <Terminal size={16} color="#38bdf8" />
                  <span>Live Forensic Audit & Ingestion Stream</span>
                </div>
                <span className="stat-badge">LIVE MONITOR</span>
              </div>

              <div className="telemetry-terminal-box">
                {triageLog.map((item, idx) => (
                  <div key={idx} className="log-entry-line">
                    <span className="log-ts">[{item.ts}]</span>
                    <span className={`log-tag ${item.tag}`}>{item.tag.toUpperCase()}</span>
                    <span className="log-msg">{item.msg}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="telemetry-card">
              <div className="section-head-row">
                <div className="section-title">
                  <Database size={16} color="#10b981" />
                  <span>Chain of Custody</span>
                </div>
                <span className="stat-badge">VERIFIED</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                <div className="chain-item">
                  <div>
                    <div className="chain-title">Active Case Docket</div>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>CID-2026-FEAS-881</div>
                  </div>
                  <CheckCircle2 size={16} color="#10b981" />
                </div>

                <div className="chain-item">
                  <div>
                    <div className="chain-title">Cryptographic Seal</div>
                    <div className="chain-hash">e3b0c44298fc1c149afb...</div>
                  </div>
                  <Lock size={15} color="#38bdf8" />
                </div>

                <div className="chain-item">
                  <div>
                    <div className="chain-title">Examiner Credentials</div>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Special Agent Senior Examiner</div>
                  </div>
                  <Shield size={16} color="#38bdf8" />
                </div>
              </div>
            </div>
      </section>
    </div>
  );
}
