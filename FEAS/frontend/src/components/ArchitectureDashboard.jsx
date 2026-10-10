import React, { useState } from 'react';
import {
  ShieldCheck,
  FileCheck,
  FileText,
  Download,
  Play,
  RotateCcw,
  Sparkles,
  Cpu,
  Layers,
  ArrowRight,
  ArrowDown,
  CheckCircle2,
  AlertTriangle,
  Eye,
  Activity,
  Box,
  Rotate3d,
  Sliders,
  Check,
  Scan,
  Database
} from 'lucide-react';
import Forensic3DLab from './Forensic3DLab';

export default function ArchitectureDashboard({ examiner = 'Special Agent Forensic Examiner', onOpen3D }) {
  // Pipeline simulation state
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineProgress, setPipelineProgress] = useState(100); // 0 to 100
  const [activeStage, setActiveStage] = useState('completed'); // 'idle' | 'preprocessing' | 'analyzing' | 'fusion' | 'completed'

  // Input selection & preview states
  const [selectedLandscape, setSelectedLandscape] = useState('tampered'); // 'tampered' | 'clean'
  const [faceSplitPos, setFaceSplitPos] = useState(50); // Face SR comparison slider 0-100
  const [showPixelGrid, setShowPixelGrid] = useState(true);
  const [show3DModal, setShow3DModal] = useState(false);
  const [modal3DMode, setModal3DMode] = useState('architecture');
  const [activeTamperBox, setActiveTamperBox] = useState(null);

  // Wound classification state (reactive)
  const [woundType, setWoundType] = useState('Burn');
  const [woundSeverity, setWoundSeverity] = useState('Moderate');
  const [woundAge, setWoundAge] = useState('2-3 Days');

  // Trigger simulated end-to-end pipeline run with animated scanlines
  const runPipeline = () => {
    setPipelineRunning(true);
    setPipelineProgress(10);
    setActiveStage('preprocessing');

    setTimeout(() => {
      setPipelineProgress(45);
      setActiveStage('analyzing');
    }, 900);

    setTimeout(() => {
      setPipelineProgress(80);
      setActiveStage('fusion');
    }, 2000);

    setTimeout(() => {
      setPipelineProgress(100);
      setActiveStage('completed');
      setPipelineRunning(false);
    }, 2800);
  };

  const handleDownloadReport = () => {
    // Generate text/PDF artifact or trigger native download
    const reportData = `
================================================================================
DEEP LEARNING FORENSIC INVESTIGATOR - OFFICIAL SYSTEM DOSSIER
AI-Based Forgery Detection, Face Authentication and Wound Classification
================================================================================
EXAMINER: ${examiner}
DATE: ${new Date().toUTCString()}
AUTHENTICATION HASH: 7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069
COURT ADMISSIBILITY: CERTIFIED UNDER FRE RULE 902(14)

1. FORGERY LOCALIZATION MODULE (VGG16 + YOLOv8)
--------------------------------------------------------------------------------
- Primary Target: Suspected Alpine Landscape
- Splicing Anomaly Detected: TRUE
- Region #1: Mountain Apex (Bounding Box [X:680, Y:120, W:280, H:190]) - Conf: 97.4%
- Region #2: Lake Water Inpainting (Bounding Box [X:590, Y:620, W:340, H:220]) - Conf: 92.1%
- Forgery Verdict: TAMPERED / COMPOSITE SPLICING DETECTED

2. DIFFUSION FACE SR & AUTHENTICATION MODULE (Diffusers + FaceNet)
--------------------------------------------------------------------------------
- Input: 32x32 Low-Resolution Surveillance Crop
- Super-Resolution: 32x Stable Diffusion Inpainting Reconstruction
- Biometric Embedding: 512-Dimensional L2 Normalized Vector
- Target Match: Subject ID #01 (Citizen Registry LFW)
- Cosine Similarity: 0.9942 (Distance: 0.28 < Threshold 0.60)
- Biometric Verdict: IDENTITY MATCHED (CONFIDENCE: 99.4%)

3. ADVANCED WOUND CLASSIFICATION MODULE (EfficientNet-B4)
--------------------------------------------------------------------------------
- Input: High-Resolution Clinical Trauma Photography
- Wound Classification: Burn (Confidence: 96.8%)
- Tissue Severity: Moderate (Confidence: 91.2%)
- Estimated Post-Trauma Age: 2-3 Days (Confidence: 89.5%)
- Tissue Infiltration: Sub-epidermal Erythema with Central Laceration Bed

DECISION FUSION & AUDIT SUMMARY
--------------------------------------------------------------------------------
Composite Evidentiary Integrity Score: 94.2%
Immutable SQLite WAL Record ID: FEAS-EV-2026-88192
================================================================================
    `;

    const blob = new Blob([reportData], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `FEAS_Forensic_Report_${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const open3DViewer = (mode = 'architecture') => {
    setModal3DMode(mode);
    setShow3DModal(true);
  };

  return (
    <div className="arch-blueprint-page">
      {/* =====================================================================
          SYSTEM TITLE HEADER BANNER (Faithful to Image Header)
          ===================================================================== */}
      <section className="arch-header-banner">
        <div className="arch-header-title-box">
          <div className="arch-system-badge">
            <span className="pulse-dot pulse-cyan" />
            <span>NEURAL FORENSIC ARCHITECTURE SPECIFICATION v2.4</span>
          </div>
          <h1 className="arch-main-title">
            DEEP LEARNING FORENSIC INVESTIGATOR – SYSTEM ARCHITECTURE
          </h1>
          <p className="arch-subtitle">
            AI-Based Forgery Detection, Face Authentication and Wound Classification
          </p>
        </div>

        {/* Global Toolbar Actions */}
        <div className="arch-toolbar-actions">
          <button
            onClick={runPipeline}
            disabled={pipelineRunning}
            className="action-btn-primary"
            title="Execute synchronous multi-engine evaluation"
          >
            {pipelineRunning ? <RotateCcw size={16} className="spin-icon" /> : <Play size={16} />}
            <span>{pipelineRunning ? `ANALYZING (${activeStage.toUpperCase()})...` : 'RUN END-TO-END PIPELINE'}</span>
          </button>

          <button
            onClick={() => {
              if (onOpen3D) onOpen3D('architecture');
              open3DViewer('architecture');
            }}
            className="action-btn-3d"
            title="Open 3D Spatial Interactive Interface"
          >
            <Rotate3d size={16} />
            <span>3D INTERACTIVE LAB</span>
          </button>

          <button
            onClick={handleDownloadReport}
            className="action-btn-secondary"
            title="Export court-admissible PDF dossier"
          >
            <Download size={16} />
            <span>EXPORT REPORT (PDF)</span>
          </button>
        </div>
      </section>

      {/* Progress Scanning Laser Bar */}
      {pipelineRunning && (
        <div className="pipeline-scan-bar-container">
          <div className="pipeline-scan-bar" style={{ width: `${pipelineProgress}%` }}>
            <span className="scan-glow" />
          </div>
        </div>
      )}

      {/* =====================================================================
          MAIN ARCHITECTURAL PIPELINE GRID (Matching the 5 Diagram Sections)
          1. INPUT LAYER
          2. PREPROCESSING MODULE
          3. CORE FORENSIC ANALYSIS MODULES (Forgery, Face SR, Wound)
          4. DECISION FUSION & REPORT GENERATION
          5. OUTPUT & RESULTS
          ===================================================================== */}
      <div className="arch-pipeline-container">
        
        {/* ===================================================================
            SECTION 1: INPUT LAYER
            =================================================================== */}
        <div className="pipeline-col col-input">
          <div className="pipeline-col-header bg-navy">
            <Layers size={16} />
            <span>INPUT LAYER</span>
          </div>

          <div className="pipeline-col-body">
            {/* Input 1: Suspected Image */}
            <div className="input-card">
              <div className="input-card-title">
                <span>Suspected Image</span>
                <span className="card-badge">LANDSCAPE</span>
              </div>
              <div className="input-card-media-wrapper">
                <img
                  src="/assets/landscape_sample.jpg"
                  alt="Suspected mountain landscape"
                  className="input-card-img"
                />
                <div className="media-overlay-tag">RGB 2560×1440</div>
              </div>
              <div className="input-card-footer">
                <button
                  onClick={() => setSelectedLandscape(selectedLandscape === 'tampered' ? 'clean' : 'tampered')}
                  className="mini-toggle-btn"
                >
                  Source: {selectedLandscape === 'tampered' ? 'CASIAv2 Spliced' : 'Clean Reference'}
                </button>
              </div>
            </div>

            {/* Input 2: Low Quality Face Image */}
            <div className="input-card">
              <div className="input-card-title">
                <span>Low Quality Face Image</span>
                <span className="card-badge badge-blue">32 × 32</span>
              </div>
              <div className="input-card-media-wrapper face-pixel-box">
                <img
                  src="/assets/face_sample.jpg"
                  alt="32x32 Low Quality Face"
                  className={`input-card-img pixelated-img ${showPixelGrid ? 'with-grid' : ''}`}
                />
                <div className="pixel-overlay-label">32 x 32 px</div>
              </div>
              <div className="input-card-footer">
                <button
                  onClick={() => setShowPixelGrid(!showPixelGrid)}
                  className="mini-toggle-btn"
                >
                  Grid: {showPixelGrid ? 'ON' : 'OFF'}
                </button>
              </div>
            </div>

            {/* Input 3: Wound Image */}
            <div className="input-card">
              <div className="input-card-title">
                <span>Wound Image</span>
                <span className="card-badge badge-purple">TRAUMA</span>
              </div>
              <div className="input-card-media-wrapper wound-preview-box">
                <img
                  src="/assets/wound_sample.svg"
                  alt="Clinical Wound Trauma Sample"
                  className="input-card-img"
                />
                <div className="media-overlay-tag">CLINICAL MACRO</div>
              </div>
              <div className="input-card-footer">
                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                  Tissue: Erythema + Laceration
                </span>
              </div>
            </div>

            {/* Input 4: Supported Formats */}
            <div className="supported-formats-card">
              <div className="formats-title">Supported Formats</div>
              <div className="formats-chips">
                <span className="format-chip active-format">
                  <FileText size={12} /> JPG, PNG, JPEG
                </span>
                <span className="format-chip future-format">
                  MP4 (Future Scope)
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Dynamic Connector Arrow 1 -> 2 */}
        <div className="pipeline-flow-connector">
          <div className="connector-line">
            <span className={`flow-pulse ${pipelineRunning ? 'pulsing' : ''}`} />
          </div>
          <ArrowRight className="connector-arrow" size={20} />
        </div>

        {/* ===================================================================
            SECTION 2: PREPROCESSING MODULE
            =================================================================== */}
        <div className="pipeline-col col-preprocessing">
          <div className="pipeline-col-header bg-darkgreen">
            <Sliders size={16} />
            <span>PREPROCESSING MODULE</span>
          </div>

          <div className="pipeline-col-body preprocess-steps-list">
            <div className="preprocess-step-item">
              <div className="step-icon-box">
                <Scan size={18} color="#10b981" />
              </div>
              <div className="step-info">
                <div className="step-name">Image Resizing</div>
                <div className="step-desc">Adaptive bicubic tensor scaling to 224×224 / 512×512</div>
              </div>
              <CheckCircle2 size={16} color="#10b981" />
            </div>

            <div className="preprocess-step-arrow"><ArrowDown size={14} /></div>

            <div className="preprocess-step-item">
              <div className="step-icon-box">
                <Sparkles size={18} color="#10b981" />
              </div>
              <div className="step-info">
                <div className="step-name">Noise Removal</div>
                <div className="step-desc">Bilateral filtering & high-frequency sensor suppression</div>
              </div>
              <CheckCircle2 size={16} color="#10b981" />
            </div>

            <div className="preprocess-step-arrow"><ArrowDown size={14} /></div>

            <div className="preprocess-step-item">
              <div className="step-icon-box">
                <Activity size={18} color="#10b981" />
              </div>
              <div className="step-info">
                <div className="step-name">Normalization</div>
                <div className="step-desc">Zero-mean & unit-variance ImageNet calibration</div>
              </div>
              <CheckCircle2 size={16} color="#10b981" />
            </div>

            <div className="preprocess-step-arrow"><ArrowDown size={14} /></div>

            <div className="preprocess-step-item">
              <div className="step-icon-box">
                <Layers size={18} color="#10b981" />
              </div>
              <div className="step-info">
                <div className="step-name">Data Augmentation</div>
                <div className="step-desc">Affine invariance, elastic distortions & jitter</div>
              </div>
              <CheckCircle2 size={16} color="#10b981" />
            </div>

            <div className="preprocess-step-arrow"><ArrowDown size={14} /></div>

            <div className="preprocess-step-item">
              <div className="step-icon-box">
                <FileCheck size={18} color="#10b981" />
              </div>
              <div className="step-info">
                <div className="step-name">Format Conversion</div>
                <div className="step-desc">PyTorch FP32 Tensor CHW mapping & memory pinning</div>
              </div>
              <CheckCircle2 size={16} color="#10b981" />
            </div>

            <div className="preprocess-footer-telemetry">
              <span>Latency: &le; 18ms</span>
              <span>Deterministic SEED: 42</span>
            </div>
          </div>
        </div>

        {/* Dynamic Connector Arrow 2 -> 3 */}
        <div className="pipeline-flow-connector">
          <div className="connector-line">
            <span className={`flow-pulse ${pipelineRunning ? 'pulsing' : ''}`} />
          </div>
          <ArrowRight className="connector-arrow" size={20} />
        </div>

        {/* ===================================================================
            SECTION 3: CORE FORENSIC ANALYSIS MODULES + DECISION FUSION
            =================================================================== */}
        <div className="pipeline-col-large col-core-modules">
          <div className="core-modules-master-header">
            <Cpu size={18} color="#00f0ff" />
            <span>CORE FORENSIC ANALYSIS MODULES</span>
            <span className="badge-mono" style={{ marginLeft: 'auto', background: 'rgba(0,240,255,0.15)', color: '#00f0ff' }}>
              PARALLEL INFERENCE THREADS [3/3]
            </span>
          </div>

          {/* Parallel 3 Sub-Modules Container */}
          <div className="core-submodules-grid">
            
            {/* ---------------------------------------------------------------
                SUB-MODULE 1: FORGERY LOCALIZATION (Red Theme)
                --------------------------------------------------------------- */}
            <div className="submodule-card module-forgery">
              <div className="submodule-header bg-crimson">
                <span className="module-num">1.</span>
                <span>FORGERY LOCALIZATION</span>
              </div>

              <div className="submodule-body">
                {/* Step 1: Feature Extraction (VGG16) */}
                <div className="neural-step-box">
                  <div className="neural-step-title">Feature Extraction (VGG16)</div>
                  <div className="vgg-diagram">
                    <div className="vgg-block vgg-1">CONV1-2</div>
                    <div className="vgg-arrow">&rarr;</div>
                    <div className="vgg-block vgg-2">POOL</div>
                    <div className="vgg-arrow">&rarr;</div>
                    <div className="vgg-block vgg-3">CONV3-5</div>
                  </div>
                </div>

                <div className="step-arrow-down"><ArrowDown size={14} /></div>

                {/* Step 2: Object Detection (YOLOv8) */}
                <div className="neural-step-box">
                  <div className="neural-step-title">Object Detection (YOLOv8)</div>
                  <div className="yolo-diagram">
                    <div className="yolo-grid-box" />
                    <span className="yolo-caption">Spatial Anchorless Head</span>
                    <div className="yolo-bbox-icon" />
                  </div>
                </div>

                <div className="step-arrow-down"><ArrowDown size={14} /></div>

                {/* Step 3: Forgery Localization (Red Bounding Boxes) */}
                <div className="localization-result-box">
                  <div className="neural-step-title" style={{ color: '#ff3366', fontWeight: 800 }}>
                    Forgery Localization (Red Bounding Boxes)
                  </div>

                  <div className="tamper-bounding-preview">
                    <img
                      src="/assets/landscape_sample.jpg"
                      alt="Tampered Localization Result"
                      className="tamper-preview-img"
                    />

                    {/* Red Bounding Box 1: Mountain Peak Splicing */}
                    <div
                      className={`tamper-box box-mountain ${activeTamperBox === 1 ? 'selected' : ''}`}
                      onClick={() => setActiveTamperBox(activeTamperBox === 1 ? null : 1)}
                      title="Tampered Region #1: Spliced mountain peak (CASIAv2)"
                    >
                      <span className="tamper-box-label">SPLICING 97.4%</span>
                    </div>

                    {/* Red Bounding Box 2: Lake Reflection Alteration */}
                    <div
                      className={`tamper-box box-reflection ${activeTamperBox === 2 ? 'selected' : ''}`}
                      onClick={() => setActiveTamperBox(activeTamperBox === 2 ? null : 2)}
                      title="Tampered Region #2: Inpainted water surface"
                    >
                      <span className="tamper-box-label">INPAINTING 92.1%</span>
                    </div>
                  </div>

                  <button
                    onClick={() => open3DViewer('tamper')}
                    className="inspect-3d-btn btn-red"
                  >
                    <Box size={13} />
                    <span>Inspect 3D Tamper Elevation</span>
                  </button>
                </div>
              </div>
            </div>

            {/* ---------------------------------------------------------------
                SUB-MODULE 2: DIFFUSION FACE SR + AUTHENTICATION (Blue Theme)
                --------------------------------------------------------------- */}
            <div className="submodule-card module-face">
              <div className="submodule-header bg-blue">
                <span className="module-num">2.</span>
                <span>DIFFUSION FACE SR + AUTHENTICATION</span>
              </div>

              <div className="submodule-body">
                {/* Step 1: Low Resolution Face Input */}
                <div className="neural-step-box">
                  <div className="neural-step-title">Low Resolution Face Input</div>
                  <div className="face-lowres-display">
                    <img
                      src="/assets/face_sample.jpg"
                      alt="32x32 Low Res Face"
                      className="face-thumb-32"
                    />
                    <span className="badge-mono" style={{ background: '#07152b', color: '#00f0ff' }}>
                      32 x 32
                    </span>
                  </div>
                </div>

                <div className="step-arrow-down"><ArrowDown size={14} /></div>

                {/* Step 2: Stable Diffusion Inpainting (Super Resolution) */}
                <div className="neural-step-box">
                  <div className="neural-step-title">Stable Diffusion Inpainting (Super Resolution)</div>
                  <div className="diffusion-steps-bar">
                    <div className="diffusion-node active">T=50</div>
                    <div className="diffusion-line" />
                    <div className="diffusion-node active">T=25</div>
                    <div className="diffusion-line" />
                    <div className="diffusion-node active">T=0</div>
                  </div>
                </div>

                <div className="step-arrow-down"><ArrowDown size={14} /></div>

                {/* Step 3: Upscaled Face (x32) */}
                <div className="neural-step-box">
                  <div className="neural-step-title">Upscaled Face ( x32 )</div>
                  <div className="face-sr-slider-container">
                    <div className="face-sr-image-wrapper">
                      <img
                        src="/assets/face_sample.jpg"
                        alt="High Res Reconstructed Face"
                        className="face-sr-img-high"
                      />
                      <div
                        className="face-sr-img-low-overlay"
                        style={{ clipPath: `inset(0 ${100 - faceSplitPos}% 0 0)` }}
                      >
                        <img
                          src="/assets/face_sample.jpg"
                          alt="Low Res Face Overlay"
                          className="pixelated-img"
                        />
                      </div>
                      <div className="slider-divider-line" style={{ left: `${faceSplitPos}%` }} />
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={faceSplitPos}
                      onChange={(e) => setFaceSplitPos(Number(e.target.value))}
                      className="face-slider-input"
                    />
                    <div className="slider-legend">
                      <span>32x32 Low Res</span>
                      <span>x32 Diffusion SR</span>
                    </div>
                  </div>
                </div>

                <div className="step-arrow-down"><ArrowDown size={14} /></div>

                {/* Step 4: Face Authentication (FaceNet) */}
                <div className="neural-step-box">
                  <div className="neural-step-title">Face Authentication (FaceNet)</div>
                  <div className="facenet-vector-display">
                    <div className="vector-bars">
                      <span style={{ height: '70%' }} />
                      <span style={{ height: '90%' }} />
                      <span style={{ height: '40%' }} />
                      <span style={{ height: '85%' }} />
                      <span style={{ height: '60%' }} />
                      <span style={{ height: '95%' }} />
                    </div>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>512-D L2 Cosine</span>
                    <div className="vector-bars">
                      <span style={{ height: '72%' }} />
                      <span style={{ height: '88%' }} />
                      <span style={{ height: '42%' }} />
                      <span style={{ height: '84%' }} />
                      <span style={{ height: '58%' }} />
                      <span style={{ height: '96%' }} />
                    </div>
                  </div>
                </div>

                <div className="step-arrow-down"><ArrowDown size={14} /></div>

                {/* Step 5: Identity Matched */}
                <div className="identity-match-banner">
                  <CheckCircle2 size={18} color="#10b981" />
                  <div>
                    <div style={{ fontWeight: 800, color: '#10b981', fontSize: 13 }}>Identity Matched</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Similarity: 99.4% (L2 Dist: 0.28)</div>
                  </div>
                </div>

                <button
                  onClick={() => open3DViewer('biometrics')}
                  className="inspect-3d-btn btn-blue"
                  style={{ marginTop: 8 }}
                >
                  <Eye size={13} />
                  <span>Inspect 3D Facial Mesh</span>
                </button>
              </div>
            </div>

            {/* ---------------------------------------------------------------
                SUB-MODULE 3: ADVANCED WOUND CLASSIFICATION (Purple Theme)
                --------------------------------------------------------------- */}
            <div className="submodule-card module-wound">
              <div className="submodule-header bg-purple">
                <span className="module-num">3.</span>
                <span>ADVANCED WOUND CLASSIFICATION</span>
              </div>

              <div className="submodule-body">
                {/* Step 1: Wound Image Input */}
                <div className="neural-step-box">
                  <div className="neural-step-title">Wound Image Input</div>
                  <div className="wound-thumb-display">
                    <img
                      src="/assets/wound_sample.svg"
                      alt="Wound Input thumbnail"
                      className="wound-thumb-img"
                    />
                  </div>
                </div>

                <div className="step-arrow-down"><ArrowDown size={14} /></div>

                {/* Step 2: Feature Extraction (EfficientNet-B4) */}
                <div className="neural-step-box">
                  <div className="neural-step-title">Feature Extraction (EfficientNet-B4)</div>
                  <div className="effnet-diagram">
                    <div className="effnet-box">MBConv1</div>
                    <div className="effnet-arrow">&rarr;</div>
                    <div className="effnet-box">MBConv6</div>
                    <div className="effnet-arrow">&rarr;</div>
                    <div className="effnet-box">GAP</div>
                  </div>
                </div>

                <div className="step-arrow-down"><ArrowDown size={14} /></div>

                {/* Step 3: Multi-label Classification (Type / Severity / Age) */}
                <div className="multilabel-checklist-box">
                  <div className="multilabel-header">
                    Multi-label Classification (Type / Severity / Age)
                  </div>

                  {/* Type Checkboxes */}
                  <div className="checklist-group">
                    <div className="group-label">
                      <span className="custom-check checked"><Check size={11} /></span>
                      <span className="label-text">Type (Cut / Burn / Bruise / Laceration)</span>
                    </div>
                    <div className="sub-pills">
                      {['Cut', 'Burn', 'Bruise', 'Laceration'].map((t) => (
                        <button
                          key={t}
                          onClick={() => setWoundType(t)}
                          className={`pill-option ${woundType === t ? 'active' : ''}`}
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Severity Checkboxes */}
                  <div className="checklist-group">
                    <div className="group-label">
                      <span className="custom-check checked"><Check size={11} /></span>
                      <span className="label-text">Severity (Mild / Moderate / Severe)</span>
                    </div>
                    <div className="sub-pills">
                      {['Mild', 'Moderate', 'Severe'].map((s) => (
                        <button
                          key={s}
                          onClick={() => setWoundSeverity(s)}
                          className={`pill-option ${woundSeverity === s ? 'active' : ''}`}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Age Checkboxes */}
                  <div className="checklist-group">
                    <div className="group-label">
                      <span className="custom-check checked"><Check size={11} /></span>
                      <span className="label-text">Age (New / 1-2 Days / 2-5 Days / Old)</span>
                    </div>
                    <div className="sub-pills">
                      {['New', '1-2 Days', '2-3 Days', 'Old'].map((a) => (
                        <button
                          key={a}
                          onClick={() => setWoundAge(a)}
                          className={`pill-option ${woundAge === a ? 'active' : ''}`}
                        >
                          {a}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="step-arrow-down"><ArrowDown size={14} /></div>

                {/* Step 4: Prediction Output Card */}
                <div className="prediction-output-card">
                  <div className="pred-title">Prediction Output</div>
                  <div className="pred-rows">
                    <div className="pred-row">
                      <span className="pred-key">Type</span>
                      <span className="pred-dots">:</span>
                      <span className="pred-val val-type">{woundType}</span>
                    </div>
                    <div className="pred-row">
                      <span className="pred-key">Severity</span>
                      <span className="pred-dots">:</span>
                      <span className="pred-val val-sev">{woundSeverity}</span>
                    </div>
                    <div className="pred-row">
                      <span className="pred-key">Age</span>
                      <span className="pred-dots">:</span>
                      <span className="pred-val val-age">{woundAge}</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => open3DViewer('wound')}
                  className="inspect-3d-btn btn-purple"
                  style={{ marginTop: 8 }}
                >
                  <Activity size={13} />
                  <span>Inspect 3D Trauma Topology</span>
                </button>
              </div>
            </div>

          </div>

          {/* =================================================================
              DECISION FUSION & REPORT GENERATION (Bottom of Core Modules)
              ================================================================= */}
          <div className="decision-fusion-banner">
            <div className="fusion-banner-title">
              <Database size={15} color="#f59e0b" />
              <span>DECISION FUSION & REPORT GENERATION</span>
            </div>

            <div className="fusion-steps-flow">
              <div className="fusion-step">
                <div className="fusion-step-icon">
                  <Database size={16} />
                </div>
                <span>Results Aggregation from All Modules</span>
              </div>

              <div className="fusion-arrow">&rarr;</div>

              <div className="fusion-step">
                <div className="fusion-step-icon">
                  <ShieldCheck size={16} color="#10b981" />
                </div>
                <span>Confidence Scoring & Validation</span>
              </div>

              <div className="fusion-arrow">&rarr;</div>

              <div className="fusion-step">
                <div className="fusion-step-icon">
                  <FileText size={16} color="#38bdf8" />
                </div>
                <span>Forensic Report Generation</span>
              </div>

              <div className="fusion-arrow">&rarr;</div>

              <div className="fusion-step" onClick={handleDownloadReport} style={{ cursor: 'pointer' }}>
                <div className="fusion-step-icon" style={{ background: 'rgba(56,189,248,0.2)' }}>
                  <Download size={16} color="#00f0ff" />
                </div>
                <span style={{ color: '#00f0ff', fontWeight: 700 }}>Save / Export Report</span>
              </div>
            </div>
          </div>

        </div>

        {/* Dynamic Connector Arrow 3 -> 4 */}
        <div className="pipeline-flow-connector">
          <div className="connector-line">
            <span className={`flow-pulse ${pipelineRunning ? 'pulsing' : ''}`} />
          </div>
          <ArrowRight className="connector-arrow" size={20} />
        </div>

        {/* ===================================================================
            SECTION 4: OUTPUT & RESULTS
            =================================================================== */}
        <div className="pipeline-col col-output">
          <div className="pipeline-col-header bg-navy">
            <CheckCircle2 size={16} />
            <span>OUTPUT & RESULTS</span>
          </div>

          <div className="pipeline-col-body">
            {/* Output 1: Forgery Detection Result */}
            <div className="output-result-card">
              <div className="output-card-title">Forgery Detection Result</div>
              <div className="output-icon-visual">
                <div className="tamper-icon-badge">
                  <AlertTriangle size={28} color="#ff3366" />
                </div>
                <div className="output-card-desc">
                  Tampered Regions Highlighted with Red Boxes
                </div>
              </div>
              <div className="output-verdict-pill verdict-danger">
                SPLICING VERIFIED [CONF: 97.4%]
              </div>
            </div>

            {/* Output 2: Face Authentication Result */}
            <div className="output-result-card">
              <div className="output-card-title">Face Authentication Result</div>
              <div className="output-icon-visual">
                <div className="biometric-icon-badge">
                  <ShieldCheck size={28} color="#10b981" />
                </div>
                <div className="output-card-desc">
                  Identity Matched with Confidence Score
                </div>
              </div>
              <div className="output-verdict-pill verdict-success">
                MATCH: SUBJECT #01 [99.4%]
              </div>
            </div>

            {/* Output 3: Wound Analysis Result */}
            <div className="output-result-card">
              <div className="output-card-title">Wound Analysis Result</div>
              <div className="output-icon-visual">
                <div className="wound-icon-badge">
                  <Activity size={28} color="#a855f7" />
                </div>
                <div className="output-card-desc">
                  Type, Severity and Age Predicted
                </div>
              </div>
              <div className="output-verdict-pill verdict-purple">
                {woundType.toUpperCase()} • {woundSeverity.toUpperCase()} • {woundAge.toUpperCase()}
              </div>
            </div>

            {/* Output 4: Forensic Report Generation (PDF Export) */}
            <div className="output-result-card pdf-card">
              <div className="output-card-title">Forensic Report Generation</div>
              <div className="output-icon-visual">
                <div className="pdf-icon-badge">
                  <FileText size={28} color="#ef4444" />
                  <span className="pdf-tag">PDF</span>
                </div>
                <div className="output-card-desc">
                  Auto-generated Report (PDF)
                </div>
              </div>
              <button
                onClick={handleDownloadReport}
                className="pdf-download-btn"
              >
                <Download size={14} />
                <span>DOWNLOAD CERTIFIED DOSSIER</span>
              </button>
            </div>
          </div>
        </div>

      </div>

      {/* =====================================================================
          BOTTOM METADATA PANELS (Faithful to Image Footer)
          - Left: DATASETS USED
          - Right: TECHNOLOGIES USED
          ===================================================================== */}
      <div className="arch-bottom-metadata-grid">
        {/* DATASETS USED */}
        <div className="meta-card datasets-card">
          <div className="meta-card-header">
            <Database size={15} color="#10b981" />
            <span>DATASETS USED</span>
          </div>
          <div className="meta-card-content">
            <div className="dataset-item">
              <span className="dataset-icon casia-icon">CASIA</span>
              <div className="dataset-details">
                <span className="dataset-name">CASIAv2 Dataset</span>
                <span className="dataset-usage">(For Forgery Detection)</span>
              </div>
            </div>

            <div className="dataset-item">
              <span className="dataset-icon lfw-icon">LFW</span>
              <div className="dataset-details">
                <span className="dataset-name">LFW Dataset</span>
                <span className="dataset-usage">(For Face Authentication)</span>
              </div>
            </div>

            <div className="dataset-item">
              <span className="dataset-icon wound-icon">MED</span>
              <div className="dataset-details">
                <span className="dataset-name">Custom Wound Dataset</span>
                <span className="dataset-usage">(For Wound Classification)</span>
              </div>
            </div>
          </div>
        </div>

        {/* TECHNOLOGIES USED */}
        <div className="meta-card tech-card">
          <div className="meta-card-header">
            <Cpu size={15} color="#00f0ff" />
            <span>TECHNOLOGIES USED</span>
          </div>
          <div className="meta-card-content tech-pills-wrap">
            <div className="tech-badge">
              <span className="tech-dot tech-pytorch" />
              <span>PyTorch</span>
            </div>
            <div className="tech-badge">
              <span className="tech-dot tech-diffusers" />
              <span>Diffusers</span>
            </div>
            <div className="tech-badge">
              <span className="tech-dot tech-yolo" />
              <span>YOLOv8 (Ultralytics)</span>
            </div>
            <div className="tech-badge">
              <span className="tech-dot tech-effnet" />
              <span>EfficientNet-B4</span>
            </div>
            <div className="tech-badge">
              <span className="tech-dot tech-facenet" />
              <span>FaceNet</span>
            </div>
            <div className="tech-badge">
              <span className="tech-dot tech-streamlit" />
              <span>Streamlit</span>
            </div>
            <div className="tech-badge">
              <span className="tech-dot tech-opencv" />
              <span>OpenCV</span>
            </div>
            <div className="tech-badge">
              <span className="tech-dot tech-pandas" />
              <span>Pandas</span>
            </div>
            <div className="tech-badge">
              <span className="tech-dot tech-numpy" />
              <span>NumPy</span>
            </div>
          </div>
        </div>
      </div>

      {/* =====================================================================
          3D INTERACTIVE INTERFACE MODAL / DEDICATED EMBEDDED LAB
          ===================================================================== */}
      {show3DModal && (
        <div className="modal-3d-backdrop" onClick={() => setShow3DModal(false)}>
          <div className="modal-3d-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-3d-topbar">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Rotate3d size={18} color="#00f0ff" />
                <span style={{ fontWeight: 800, color: '#fff', fontSize: 15 }}>
                  3D INTERACTIVE FORENSIC INTERFACE
                </span>
                <span className="badge-mono" style={{ background: 'rgba(0,240,255,0.15)', color: '#00f0ff' }}>
                  MODE: {modal3DMode.toUpperCase()}
                </span>
              </div>
              <button
                onClick={() => setShow3DModal(false)}
                className="modal-close-btn"
              >
                &times;
              </button>
            </div>

            <div className="modal-3d-canvas-wrap">
              <Forensic3DLab
                initialMode={modal3DMode}
                onSelectModule={(modId) => {
                  console.log('Selected 3D node:', modId);
                }}
              />
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
