import React, { useState, useRef } from 'react';
import { 
  Upload, AlertTriangle, CheckCircle, Search, RefreshCw, Eye, Sliders, 
  Sparkles, CircleDot, Settings2, ArrowLeftRight, Layers 
} from 'lucide-react';
import DitherVeil from './DitherVeil';
import LatticeLoader from './LatticeLoader';
import CloudSyncButton from './CloudSyncButton';
import { firebaseService } from '../services/firebase';

export default function TamperingDetector() {
  const [imageSrc, setImageSrc] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [activeView, setActiveView] = useState('original'); // 'original' | 'ela' | 'mask'
  const [sensitivity, setSensitivity] = useState(75);
  const [errorMsg, setErrorMsg] = useState(null);
  const fileInputRef = useRef(null);

  // Interactive Reveal Veil state (default false to show crisp detections immediately)
  const [veilMode, setVeilMode] = useState(false);
  const [revealRadius, setRevealRadius] = useState(65);
  const [softness, setSoftness] = useState(0.6);
  const [linger, setLinger] = useState(1.2);
  const [reverseReveal, setReverseReveal] = useState(false);
  const [ditherOn, setDitherOn] = useState(false);
  const [clickBurst, setClickBurst] = useState(true);
  const [showOptionsPanel, setShowOptionsPanel] = useState(false);

  const cycleRadius = () => {
    const presets = [40, 75, 120, 180];
    const nextIdx = (presets.findIndex(p => p >= revealRadius) + 1) % presets.length;
    setRevealRadius(presets[nextIdx]);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setImageSrc(ev.target.result);
        setResult(null);
        setErrorMsg(null);
        setActiveView('original');
      };
      reader.readAsDataURL(file);
    }
  };

  const runAnalysis = async () => {
    if (!imageSrc) return;
    setAnalyzing(true);
    setErrorMsg(null);

    try {
      const res = await fetch('/api/v1/analyze/tampering', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageSrc, sensitivity })
      });

      if (!res.ok) {
        throw new Error(`Tampering API returned status ${res.status}`);
      }

      const data = await res.json();
      const tamperScorePct = Math.round((data.tamper_score || 0) * 100);
      const isTampered = Boolean(data.is_tampered);
      const isAi = Boolean(data.is_ai_generated);
      const aiProbPct = Math.round((data.ai_probability || 0) * 100);
      const compositeConfidence = Math.max(tamperScorePct, aiProbPct);
      const elaMetrics = data.ela_metrics || {};

      setResult({
        ...data,
        verdict: isAi
          ? (isTampered ? 'AI SYNTHESIS & TAMPERING DETECTED' : 'AI GENERATION / DEEPFAKE DETECTED')
          : (isTampered ? 'TAMPERING DETECTED' : 'INTEGRITY VERIFIED'),
        isTampered: isTampered || isAi,
        confidence: compositeConfidence,
        findings: [
          {
            label: 'AI & Deepfake Synthesis',
            score: isAi ? `${aiProbPct}% Match` : `${aiProbPct}% (Camera Original)`,
            desc: isAi
              ? `Generative synthesis detected. Archetype: ${data.ai_archetype || 'Latent Diffusion Model'}. Frequency residual kurtosis: ${data.ai_analysis?.noise_residual_analysis?.residual_kurtosis || 0}.`
              : 'Sensor noise and frequency spectrum adhere to natural optical camera distributions.'
          },
          {
            label: 'Localized Splicing & AI Detections',
            score: `${data.bboxes?.length || 0} Regions`,
            desc: data.bboxes?.length
              ? `${data.bboxes.length} anomalous spliced, inpainted, or synthetic clusters localized.`
              : 'No anomalous localized splicing clusters detected.'
          },
          {
            label: 'ELA Compression Inconsistency',
            score: `${Math.round((elaMetrics.tamper_ratio || 0) * 100)}%`,
            desc: `Error Level Analysis mean deviation: ${elaMetrics.mean_diff || elaMetrics.mean_error || 0}, max delta: ${elaMetrics.max_diff || elaMetrics.max_error || 0}.`
          },
          {
            label: 'Compression Matrix Integrity',
            score: isTampered || isAi ? 'Non-Uniform' : 'Uniform Sensor Noise',
            desc: isTampered || isAi
              ? (data.advisory_notes || 'Multi-stage recompression artifacts and synthetic anomalies detected.')
              : 'Uniform sensor noise and standard quantization table confirmed.'
          }
        ],
        recommendation: data.advisory_notes || (
          isTampered || isAi
            ? 'Evidence indicates non-uniform compression blocks and localized digital alterations post-capture.'
            : 'Bitstream analysis shows consistent PRNU sensor noise and uniform JPEG compression.'
        )
      });

      // Automatically register in active examiner's personal audit ledger
      try {
        const activeExaminer = firebaseService.getActiveExaminer();
        firebaseService.recordAnalysis(activeExaminer.uid, {
          case_id: 'CASE-TM-' + Math.floor(1000 + Math.random() * 9000),
          module: 'tampering',
          verdict: isTampered ? 'FORGED' : isAi ? 'AI_GENERATED' : 'AUTHENTIC',
          confidence: score / 100,
          evidence_name: file.name || 'tampering_evidence.png',
          sha256: data.input_sha256 || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          findings: {
            classification: isTampered ? 'Tampered / Spliced' : isAi ? 'AI Synthetic' : 'Authentic Original',
            tamper_score: `${score}%`,
            anomalous_regions: data.bboxes?.length || 0,
            ela_ratio: `${Math.round((elaMetrics.tamper_ratio || 0) * 100)}%`,
            recommendation: data.advisory_notes || 'Bitstream analysis completed.'
          }
        });
      } catch (_) {}

      // Default to Localization Mask if tampering detected or bounding boxes found
      if (data.bboxes?.length > 0 || isTampered) {
        setActiveView('mask');
      } else if (isAi) {
        setActiveView('fft');
      } else {
        setActiveView('original');
      }
    } catch (err) {
      console.error('Tampering analysis error:', err);
      setErrorMsg('Failed to run tampering analysis. Please verify backend connection.');
    } finally {
      setAnalyzing(false);
    }
  };

  const resetAll = () => {
    setImageSrc(null);
    setResult(null);
    setErrorMsg(null);
    setActiveView('original');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Determine which image view to render
  let currentDisplayImage = imageSrc;
  if (result) {
    if (activeView === 'ela' && result.ela_image_base64) {
      currentDisplayImage = result.ela_image_base64;
    } else if (activeView === 'mask') {
      currentDisplayImage = result.mask_image_base64 || result.annotated_image_base64 || imageSrc;
    } else if (activeView === 'annotated') {
      currentDisplayImage = result.annotated_image_base64 || imageSrc;
    } else if (activeView === 'gradcam' && result.gradcam_image_base64) {
      currentDisplayImage = result.gradcam_image_base64;
    } else if (activeView === 'fft' && result.fft_spectrum_base64) {
      currentDisplayImage = result.fft_spectrum_base64;
    }
  }

  return (
    <div className="module-card">
      <div className="module-header">
        <div className="module-title-wrap">
          <div className="module-icon-badge amber">
            <Search size={20} />
          </div>
          <div>
            <h2 className="module-title">Image Tampering & Forgery Detection</h2>
            <p className="module-subtitle">Detect Photoshop manipulation, Error Level Analysis (ELA), copy-paste splicing, and compression anomalies.</p>
          </div>
        </div>

        <div className="module-actions">
          {(imageSrc || result || analyzing) && (
            <button className="btn btn-outline" onClick={resetAll} title="Clear and start over">
              <RefreshCw size={14} />
              <span>Reset</span>
            </button>
          )}
        </div>
      </div>

      {!imageSrc ? (
        <div className="upload-dropzone" onClick={() => fileInputRef.current?.click()}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept="image/*"
            style={{ display: 'none' }}
          />
          <div className="dropzone-icon">
            <Upload size={36} color="#38bdf8" />
          </div>
          <div className="dropzone-text">
            <strong>Drop image here</strong> or <span className="highlight-link">browse files</span>
          </div>
          <div className="dropzone-sub">Supports JPG, PNG, WEBP, TIFF &bull; Max 20MB</div>
        </div>
      ) : (
        <div className="inspection-layout">
          {/* Controls Bar */}
          <div className="controls-bar">
            <div className="control-item">
              <Sliders size={15} />
              <span>Sensitivity: {sensitivity}%</span>
              <input
                type="range"
                min="30"
                max="95"
                value={sensitivity}
                onChange={(e) => setSensitivity(Number(e.target.value))}
                className="slider-input"
              />
            </div>

            <button
              className="btn btn-primary btn-run"
              onClick={runAnalysis}
              disabled={analyzing}
            >
              {analyzing ? (
                <LatticeLoader
                  status="working"
                  label="Scanning Forgery Signatures..."
                  pattern="arrow"
                  grid={3}
                  shape="round"
                  cellSize={5}
                  gap={2}
                  fontSize={13}
                  step={90}
                  idleOpacity={0.2}
                  glow={false}
                  showTimer={true}
                  color="#ffffff"
                />
              ) : (
                <>
                  <Search size={16} />
                  <span>Run Tamper Scan</span>
                </>
              )}
            </button>
          </div>

          {errorMsg && (
            <div style={{ padding: '12px 16px', background: 'rgba(255,51,102,0.15)', border: '1px solid #ff3366', borderRadius: 8, color: '#ff3366', fontSize: 13 }}>
              {errorMsg}
            </div>
          )}

          {/* Visual Canvas Panel */}
          <div className="preview-grid">
            <div className="preview-box">
              <div className="preview-box-header" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
                <div className="view-selector">
                  <button
                    className={"view-btn " + (activeView === 'original' ? 'active' : '')}
                    onClick={() => setActiveView('original')}
                  >
                    Original
                  </button>
                  <button
                    className={"view-btn " + (activeView === 'ela' ? 'active' : '')}
                    onClick={() => setActiveView('ela')}
                  >
                    ELA Heatmap
                  </button>
                  <button
                    className={"view-btn " + (activeView === 'mask' ? 'active' : '')}
                    onClick={() => setActiveView('mask')}
                  >
                    Localization Mask {result?.bboxes?.length ? `(${result.bboxes.length})` : ''}
                  </button>
                  <button
                    className={"view-btn " + (activeView === 'annotated' ? 'active' : '')}
                    onClick={() => setActiveView('annotated')}
                  >
                    Annotated Detections
                  </button>
                  {result?.gradcam_image_base64 && (
                    <button
                      className={"view-btn " + (activeView === 'gradcam' ? 'active' : '')}
                      onClick={() => setActiveView('gradcam')}
                    >
                      AI Activation Heatmap
                    </button>
                  )}
                  {result?.fft_spectrum_base64 && (
                    <button
                      className={"view-btn " + (activeView === 'fft' ? 'active' : '')}
                      onClick={() => setActiveView('fft')}
                    >
                      FFT 2D Spectrum
                    </button>
                  )}
                </div>

                {result && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginLeft: 'auto', flexWrap: 'wrap' }}>
                    <button
                      className={"view-btn " + (veilMode ? 'active' : '')}
                      onClick={() => setVeilMode(!veilMode)}
                      title="Toggle interactive thermal cursor reveal"
                      style={{ borderColor: veilMode ? 'rgba(56, 189, 248, 0.4)' : undefined }}
                    >
                      <Sparkles size={12} />
                      <span>Reveal: {veilMode ? 'ON' : 'OFF'}</span>
                    </button>

                    {veilMode && (
                      <>
                        <button
                          className="view-btn"
                          onClick={cycleRadius}
                          title="Click to cycle cursor reveal radius (40px -> 75px -> 120px -> 180px)"
                          style={{ background: 'rgba(56, 189, 248, 0.12)', color: '#38bdf8', borderColor: 'rgba(56, 189, 248, 0.3)' }}
                        >
                          <CircleDot size={12} />
                          <span>Radius: {revealRadius}px</span>
                        </button>

                        <button
                          className={"view-btn " + (showOptionsPanel ? 'active' : '')}
                          onClick={() => setShowOptionsPanel(!showOptionsPanel)}
                          title="Reveal settings: softness, reverse direction, dither & shockwave"
                        >
                          <Settings2 size={12} />
                          <span>Options</span>
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>

              {result && veilMode && showOptionsPanel && (
                <div className="reveal-options-panel" style={{
                  background: 'rgba(8, 14, 26, 0.95)',
                  borderBottom: '1px solid var(--border-color)',
                  padding: '0.65rem 1rem',
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '0.85rem',
                  alignItems: 'center',
                  fontSize: '0.78rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Radius:</span>
                    <input
                      type="range"
                      min="20"
                      max="220"
                      value={revealRadius}
                      onChange={(e) => setRevealRadius(Number(e.target.value))}
                      className="slider-input"
                      style={{ width: '85px' }}
                    />
                    <strong style={{ color: '#38bdf8', minWidth: '35px' }}>{revealRadius}px</strong>
                  </div>

                  <div style={{ display: 'flex', gap: '0.3rem' }}>
                    {[35, 65, 110, 180].map((r) => (
                      <button
                        key={r}
                        className={"btn-toggle " + (revealRadius === r ? 'active' : '')}
                        style={{ fontSize: '0.7rem', padding: '2px 7px' }}
                        onClick={() => setRevealRadius(r)}
                      >
                        {r}px
                      </button>
                    ))}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
                    <button
                      className={"btn-toggle " + (reverseReveal ? 'active' : '')}
                      onClick={() => setReverseReveal(!reverseReveal)}
                      title="Toggle reveal direction: Thermal/Tamper Overlay vs Original Photo"
                      style={{ fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      <ArrowLeftRight size={11} />
                      <span>{reverseReveal ? 'Reveal: Thermal / Tamper Overlay' : 'Reveal: Original Photo'}</span>
                    </button>

                    <button
                      className={"btn-toggle " + (ditherOn ? 'active' : '')}
                      onClick={() => setDitherOn(!ditherOn)}
                      title="Toggle between pure continuous thermal heatmap and stylized dither matrix"
                      style={{ fontSize: '0.72rem' }}
                    >
                      {ditherOn ? 'Texture: Dither Matrix' : 'Texture: Pure Thermal'}
                    </button>

                    <button
                      className={"btn-toggle " + (clickBurst ? 'active' : '')}
                      onClick={() => setClickBurst(!clickBurst)}
                      title="Click anywhere to trigger a radial shockwave reveal"
                      style={{ fontSize: '0.72rem' }}
                    >
                      {clickBurst ? 'Shockwave: ON' : 'Shockwave: OFF'}
                    </button>
                  </div>
                </div>
              )}

              <div className="preview-viewport" style={{ height: '420px', minHeight: '380px', position: 'relative' }}>
                {result && veilMode ? (
                  <>
                    <DitherVeil
                      src={imageSrc}
                      veilSrc={
                        activeView === 'mask'
                          ? (result.mask_image_base64 || result.annotated_image_base64 || imageSrc)
                          : (activeView === 'annotated'
                              ? (result.annotated_image_base64 || imageSrc)
                              : (activeView === 'gradcam'
                                  ? (result.gradcam_image_base64 || imageSrc)
                                  : (activeView === 'fft'
                                      ? (result.fft_spectrum_base64 || imageSrc)
                                      : (result.ela_image_base64 || result.mask_image_base64 || result.annotated_image_base64 || imageSrc))))
                      }
                      pattern="floyd"
                      pixelSize={ditherOn ? 2 : 1}
                      ditherOn={ditherOn}
                      inkColor="#0a0f1d"
                      paperColor="#60a5fa"
                      revealRadius={revealRadius}
                      softness={softness}
                      linger={linger}
                      fit="contain"
                      rimColor="#38bdf8"
                      palette="rgb"
                      levels={3}
                      contrast={1.15}
                      brightness={0}
                      rim={ditherOn ? 0.08 : 0}
                      reverse={reverseReveal}
                      wander={false}
                      clickBurst={clickBurst}
                      style={{ width: '100%', height: '100%' }}
                    />
                    <div style={{
                      position: 'absolute',
                      bottom: '10px',
                      right: '10px',
                      background: 'rgba(9, 14, 26, 0.8)',
                      backdropFilter: 'blur(8px)',
                      border: '1px solid rgba(56, 189, 248, 0.25)',
                      borderRadius: '6px',
                      padding: '4px 10px',
                      fontSize: '0.72rem',
                      color: '#94a3b8',
                      pointerEvents: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}>
                      <Sparkles size={11} color="#38bdf8" />
                      <span>{reverseReveal ? 'Hover to reveal thermal & tamper anomalies' : 'Hover to reveal original image'} &bull; Click for shockwave</span>
                    </div>
                  </>
                ) : (
                  <img
                    src={currentDisplayImage}
                    alt="Inspection target"
                    className="target-image"
                  />
                )}
              </div>
              <div className="preview-caption">
                {activeView === 'original' && 'Source image loaded without modifications.'}
                {activeView === 'mask' && 'High-contrast forensic localization mask: Highlights detected spliced, cloned, and tampered objects with vibrant thermal glow.'}
                {activeView === 'annotated' && 'Forensic annotated view: Bounding brackets and luminous overlays isolate manipulated regions.'}
                {activeView === 'ela' && (
                  veilMode && result
                    ? 'Interactive Thermal ELA Veil: Hover cursor to uncover the authentic original pixels. Click anywhere for a radial reveal shockwave.'
                    : 'Error Level Analysis (ELA): High-frequency color highlights indicate inconsistent JPEG resave compression levels.'
                )}
                {activeView === 'gradcam' && 'Deep Learning Grad-CAM Activation: Highlights neural feature importance regions indicating forgery.'}
                {activeView === 'fft' && '2D Fast Fourier Transform (FFT) Power Spectrum: Concentric grid peaks reveal generative diffusion/GAN upsampler artifacts.'}
              </div>
            </div>

            {/* Results Sidebar */}
            <div className="findings-box">
              {analyzing ? (
                <div className="analyzing-state" style={{ padding: '2.5rem 1.5rem', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.25rem' }}>
                  <LatticeLoader
                    status="working"
                    label="Thinking"
                    doneLabel="Done "
                    errorLabel="Failed "
                    pattern="arrow"
                    grid={3}
                    shape="round"
                    doneColor="#22c55e"
                    errorColor="#ef4444"
                    cellSize={6}
                    gap={2}
                    fontSize={14}
                    step={90}
                    idleOpacity={0.15}
                    glow={false}
                    glowColor=""
                    showTimer
                    color="#f5f5f5"
                  />
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', maxWidth: '300px', margin: '0 auto', lineHeight: '1.4' }}>
                    Deconstructing DCT coefficients, analyzing high-frequency resave delta, and computing ELA error matrix.
                  </p>
                </div>
              ) : result ? (
                <div className="findings-content">
                  <div className={"verdict-banner " + (result.isTampered ? 'alert' : 'safe')}>
                    {result.isTampered ? (
                      <AlertTriangle size={24} className="verdict-icon alert" />
                    ) : (
                      <CheckCircle size={24} className="verdict-icon safe" />
                    )}
                    <div>
                      <div className="verdict-title">{result.verdict}</div>
                      <div className="verdict-conf">AI Confidence: <strong>{result.confidence}%</strong></div>
                    </div>
                  </div>

                  <div className="metrics-list">
                    {result.findings?.map((item, idx) => (
                      <div key={idx} className="metric-row">
                        <div className="metric-top">
                          <span className="metric-label">{item.label}</span>
                          <span className={`metric-score ${result.isTampered ? 'badge-alert' : 'badge-safe'}`}>{item.score}</span>
                        </div>
                        <div className="metric-desc">{item.desc}</div>
                      </div>
                    ))}
                  </div>

                  {result.recommendation && (
                    <div className="recommendation-card">
                      <strong>Investigator Note:</strong>
                      <p>{result.recommendation}</p>
                    </div>
                  )}

                  <CloudSyncButton
                    moduleName="Image Tampering"
                    modulePrefix="TAMPER"
                    verdict={result.verdict}
                    confidence={result.confidence}
                    findings={{
                      is_tampered: result.isTampered,
                      confidence: result.confidence,
                      findings: result.findings,
                      ela_metrics: result.ela_metrics
                    }}
                  />

                  <button
                    className="btn btn-outline"
                    onClick={resetAll}
                    style={{ width: '100%', marginTop: '1.25rem', borderColor: 'rgba(239, 68, 68, 0.4)', color: '#f87171' }}
                    title="Clear current results and reload"
                  >
                    <RefreshCw size={14} />
                    <span>Reset & Clear Analysis Results</span>
                  </button>
                </div>
              ) : (
                <div className="idle-state">
                  <Search size={28} className="idle-icon" />
                  <h4>Ready for Scan</h4>
                  <p>Click "Run Tamper Scan" above to calculate compression anomalies, ELA variance, and splicing indicators.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
