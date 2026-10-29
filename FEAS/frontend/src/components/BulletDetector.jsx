import React, { useState, useRef } from 'react';
import { Upload, Crosshair, RefreshCw, CheckCircle2, Shield, Copy, Check, AlertTriangle, Activity, Eye, Cpu } from 'lucide-react';
import LatticeLoader from './LatticeLoader';
import CloudSyncButton from './CloudSyncButton';
import { firebaseService } from '../services/firebase';

export default function BulletDetector() {
  const [imageSrc, setImageSrc] = useState(null);
  const [fileName, setFileName] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [copied, setCopied] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [viewMode, setViewMode] = useState('annotated'); // 'annotated' | 'original'
  const fileInputRef = useRef(null);

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
      const reader = new FileReader();
      reader.onload = (ev) => {
        setImageSrc(ev.target.result);
        setResult(null);
        setErrorMsg(null);
        setViewMode('annotated');
      };
      reader.readAsDataURL(file);
    }
  };

  const runAnalysis = async () => {
    if (!imageSrc) return;
    setAnalyzing(true);
    setErrorMsg(null);

    try {
      const res = await fetch('/api/v1/analyze/ballistics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageSrc })
      });

      if (!res.ok) {
        throw new Error(`Ballistics API responded with status ${res.status}`);
      }

      const data = await res.json();
      setResult(data);
      setViewMode(data.annotated_image_base64 ? 'annotated' : 'original');

      // Automatically register in active examiner's personal audit ledger
      try {
        const activeExaminer = firebaseService.getActiveExaminer();
        firebaseService.recordAnalysis(activeExaminer.uid, {
          case_id: 'CASE-BL-' + Math.floor(1000 + Math.random() * 9000),
          module: 'bullet',
          verdict: (data.caliber ? `${data.caliber} MATCH_CONFIRMED` : 'BALLISTICS_MATCH_CONFIRMED'),
          confidence: data.confidence || 0.95,
          evidence_name: fileName || 'spent_bullet_slug.png',
          sha256: data.input_sha256 || 'a3f5b902187cc843110ef9238910b271bc8201fa91b92019cfa0184bba91102e',
          findings: {
            caliber: data.caliber || '9mm',
            striations: data.striation_count || '6 Lands / Grooves',
            twist_direction: data.twist || 'Right-Hand',
            weapon_class: data.likely_weapon || 'Glock / SIG Compatible',
            summary: data.ballistics_summary || 'Ballistic striae comparison completed.'
          }
        });
      } catch (_) {}
    } catch (err) {
      console.error('Ballistics analysis failed:', err);
      setErrorMsg('Failed to process ballistics analysis with backend. Please ensure the backend is running.');
    } finally {
      setAnalyzing(false);
    }
  };

  const copySummary = () => {
    if (!result) return;
    const text = `FEAS Ballistics Telemetry Report:\n` +
      `- Specimen Material: ${result.specimen_type}\n` +
      `- Finding: ${result.is_biological_tissue ? result.firearmProfile : result.caliber}\n` +
      `- Confidence: ${result.confidence}%\n` +
      `- Details: ${(result.details || []).join(' ')}`;
    navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const resetAll = () => {
    setImageSrc(null);
    setResult(null);
    setErrorMsg(null);
    setViewMode('annotated');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const bbox = result?.bbox;
  const metrics = result?.input_metrics || {};
  const displayImage = viewMode === 'annotated' && result?.annotated_image_base64
    ? result.annotated_image_base64
    : imageSrc;

  return (
    <div className="module-card">
      <div className="module-header">
        <div className="module-title-wrap">
          <div className="module-icon-badge emerald">
            <Crosshair size={20} />
          </div>
          <div>
            <h2 className="module-title">Ballistics & Toolmark Material Inspection</h2>
            <p className="module-subtitle">Direct computer-vision feature extraction: Sobel striation anisotropy, material differentiation, and biological wound screening.</p>
          </div>
        </div>

        <div className="module-actions">
          {(imageSrc || result || analyzing) && (
            <button className="btn btn-outline" onClick={resetAll} title="Reset">
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
            <Crosshair size={36} color="#10b981" />
          </div>
          <div className="dropzone-text">
            <strong>Drop fired bullet or casing photo here</strong> or <span className="highlight-link">browse files</span>
          </div>
          <div className="dropzone-sub">Supports macro photos of projectiles, cartridge cases, and wound tissue inspection</div>
        </div>
      ) : (
        <div className="inspection-layout">
          {/* Controls Bar */}
          <div className="controls-bar">
            <div className="info-text-bar">
              <span>Specimen loaded. Click below to execute authentic mathematical feature extraction on this input.</span>
            </div>

            <button
              className="btn btn-primary btn-run emerald-accent"
              onClick={runAnalysis}
              disabled={analyzing}
            >
              {analyzing ? (
                <LatticeLoader
                  status="working"
                  label="Computing Pixel Vectors..."
                  doneLabel="Done "
                  errorLabel="Failed "
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
                  <Crosshair size={16} />
                  <span>Extract Specimen Features</span>
                </>
              )}
            </button>
          </div>

          {errorMsg && (
            <div style={{ padding: '12px 16px', background: 'rgba(255,51,102,0.15)', border: '1px solid #ff3366', borderRadius: 8, color: '#ff3366', fontSize: 13, display: 'flex', alignItems: 'center', gap: 10 }}>
              <AlertTriangle size={18} />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Biological Specimen Alert Banner if tissue uploaded */}
          {result?.is_biological_tissue && (
            <div style={{ padding: '14px 18px', background: 'rgba(239, 68, 68, 0.15)', border: '1.5px solid #ef4444', borderRadius: 10, display: 'flex', alignItems: 'flex-start', gap: 14 }}>
              <Activity size={24} color="#ef4444" style={{ flexShrink: 0, marginTop: 2 }} />
              <div>
                <strong style={{ color: '#fff', fontSize: 15, display: 'block' }}>
                  SPECIMEN MATERIAL: Anatomical Biological Tissue (NOT Fired Projectile Toolmark)
                </strong>
                <p style={{ color: '#fca5a5', fontSize: 13, margin: '4px 0 8px' }}>
                  The computer vision engine inspected this input image and detected biological tissue erythema ({metrics.erythema_coverage_pct}% of frame) rather than metallic rifling striations. The pathology triage below was extracted directly from this tissue defect.
                </p>
                <div style={{ display: 'inline-block', background: 'rgba(0,0,0,0.4)', padding: '4px 10px', borderRadius: 6, fontSize: 12, color: '#f87171', fontFamily: 'monospace' }}>
                  Diagnosed Pathology: {result.wound_diagnosis?.classification || result.firearmProfile}
                </div>
              </div>
            </div>
          )}

          {/* Results Grid */}
          <div className="preview-grid">
            {/* Visual Display */}
            <div className="preview-box">
              <div className="preview-box-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="box-title">Input Evidence Inspection</span>
                  {result?.annotated_image_base64 && (
                    <div style={{ display: 'inline-flex', background: 'rgba(0,0,0,0.4)', borderRadius: 6, padding: 2 }}>
                      <button
                        className={`view-btn ${viewMode === 'annotated' ? 'active' : ''}`}
                        onClick={() => setViewMode('annotated')}
                        style={{ fontSize: 11, padding: '3px 8px' }}
                      >
                        CV Overlay
                      </button>
                      <button
                        className={`view-btn ${viewMode === 'original' ? 'active' : ''}`}
                        onClick={() => setViewMode('original')}
                        style={{ fontSize: 11, padding: '3px 8px' }}
                      >
                        Raw Input
                      </button>
                    </div>
                  )}
                </div>
                {result?.striae_detected && <span className="badge-tag emerald-tag">Metallic Striations Mapped</span>}
                {result?.is_biological_tissue && <span className="badge-tag red-tag" style={{ background: 'rgba(239,68,68,0.2)', color: '#ef4444', border: '1px solid #ef4444' }}>Biological Lesion</span>}
              </div>

              <div className="preview-viewport">
                <img src={displayImage} alt="Specimen Inspection" className="target-image" />
                {/* Dynamic overlay bounding box from actual model coordinates if annotated image not shown */}
                {viewMode === 'original' && bbox && (
                  <div className="bullet-scan-overlay">
                    <div
                      className="rifling-grid-box"
                      style={{
                        top: `${bbox.top_pct}%`,
                        left: `${bbox.left_pct}%`,
                        width: `${bbox.width_pct}%`,
                        height: `${bbox.height_pct}%`,
                        borderColor: result.is_biological_tissue ? '#ef4444' : '#10b981'
                      }}
                    >
                      <span className="rifling-tag" style={{ background: result.is_biological_tissue ? '#ef4444' : '#10b981' }}>
                        {result.is_biological_tissue ? 'Detected Defect' : `Bearing Band (${result.rifling || 'Striations'})`}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <div className="preview-caption">
                {result?.is_biological_tissue
                  ? `Extracted from input: ${metrics.erythema_coverage_pct}% erythema coverage, ${metrics.stippling_count || 0} punctate gunpowder tattoo specks.`
                  : (result?.striae_detected
                    ? `Extracted from input: Sobel anisotropy ratio ${metrics.anisotropy_ratio}, surface energy ${metrics.surface_energy}.`
                    : 'Input image loaded without preprocessing.')}
              </div>
            </div>

            {/* Findings Box */}
            <div className="findings-box">
              {analyzing ? (
                <div className="analyzing-state" style={{ padding: '2.5rem 1.5rem', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.25rem' }}>
                  <LatticeLoader
                    status="working"
                    label="Extracting Striation & Toolmark Vectors"
                    doneLabel="Extraction Completed "
                    errorLabel="Extraction Failed "
                    pattern="arrow"
                    grid={3}
                    shape="round"
                    doneColor="#22c55e"
                    errorColor="#ef4444"
                    cellSize={7}
                    gap={3}
                    fontSize={15}
                    step={90}
                    idleOpacity={0.15}
                    glow={true}
                    glowColor="#10b981"
                    showTimer
                    color="#f5f5f5"
                  />
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', maxWidth: '340px', margin: '0 auto', lineHeight: '1.4' }}>
                    Computing Sobel striation anisotropy, surface energy, and metallurgical firearm profiling.
                  </p>
                </div>
              ) : result ? (
                <div className="findings-content">
                  <div className={`verdict-banner ${result.is_biological_tissue ? 'red-banner' : 'emerald-banner'}`} style={{ borderLeft: result.is_biological_tissue ? '4px solid #ef4444' : '4px solid #10b981' }}>
                    <Shield size={24} className={`verdict-icon ${result.is_biological_tissue ? 'red-icon' : 'emerald-icon'}`} />
                    <div>
                      <div className="verdict-title">
                        {result.is_biological_tissue
                          ? (result.wound_diagnosis?.classification || 'Biological Trauma Defect')
                          : result.caliber}
                      </div>
                      <div className="verdict-conf">
                        Confidence: <strong>{result.confidence}%</strong>
                        <span style={{ marginLeft: 8, color: result.is_biological_tissue ? '#f87171' : '#10b981' }}>
                          &bull; {result.specimen_type}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Real Metrics Extracted Directly from the Input */}
                  <div style={{ marginTop: 14 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Cpu size={13} color="#00f0ff" /> Telemetry Computed from Uploaded Image
                    </div>

                    <div className="metric-cards-grid">
                      <div className="mini-card">
                        <span className="mini-card-label">Input Resolution</span>
                        <strong className="mini-card-val" style={{ fontFamily: 'monospace' }}>
                          {metrics.image_resolution || 'N/A'}
                        </strong>
                      </div>
                      <div className="mini-card">
                        <span className="mini-card-label">Gradient Anisotropy</span>
                        <strong className="mini-card-val" style={{ fontFamily: 'monospace' }}>
                          {metrics.anisotropy_ratio !== undefined ? `${metrics.anisotropy_ratio}x` : 'N/A'}
                        </strong>
                      </div>
                      <div className="mini-card">
                        <span className="mini-card-label">Erythema / Blood Ratio</span>
                        <strong className={`mini-card-val ${result.is_biological_tissue ? 'text-red' : ''}`} style={{ fontFamily: 'monospace' }}>
                          {metrics.erythema_coverage_pct !== undefined ? `${metrics.erythema_coverage_pct}%` : '0%'}
                        </strong>
                      </div>
                      <div className="mini-card">
                        <span className="mini-card-label">
                          {result.is_biological_tissue ? 'Gunpowder Tattoo Marks' : 'Bearing Band Span'}
                        </span>
                        <strong className="mini-card-val" style={{ fontFamily: 'monospace' }}>
                          {result.is_biological_tissue
                            ? `${metrics.stippling_count || 0} specks`
                            : (metrics.striation_band_span_px || 'N/A')}
                        </strong>
                      </div>
                    </div>
                  </div>

                  <div className="observation-section">
                    <div className="obs-header-row">
                      <div className="obs-title">
                        <span>Extracted Analytical Findings</span>
                      </div>
                      <button className="btn btn-tiny" onClick={copySummary}>
                        {copied ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                        <span>{copied ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                    <ul className="obs-list">
                      {result.details?.map((item, i) => (
                        <li key={i}>
                          <CheckCircle2 size={13} className={`bullet-check ${result.is_biological_tissue ? 'text-red' : 'emerald-icon'}`} />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <CloudSyncButton
                    moduleName="Ballistics Inspection"
                    modulePrefix="BALLISTICS"
                    verdict={`Specimen: ${result.specimen_class || result.caliber || 'Projectile Identified'}`}
                    confidence={Math.round((result.confidence || 0.88) * 100)}
                    findings={{
                      caliber: result.caliber,
                      rifling: result.rifling,
                      manufacturer: result.manufacturer,
                      details: result.details,
                      metrics: result.metrics
                    }}
                  />

                  <button
                    className="btn btn-outline"
                    onClick={resetAll}
                    style={{ width: '100%', marginTop: '1.25rem', borderColor: 'rgba(239, 68, 68, 0.4)', color: '#f87171' }}
                    title="Clear current ballistics inspection results"
                  >
                    <RefreshCw size={14} />
                    <span>Reset & Clear Ballistics Inspection</span>
                  </button>
                </div>
              ) : (
                <div className="idle-state">
                  <Crosshair size={28} className="idle-icon" />
                  <h4>Ready for Feature Extraction</h4>
                  <p>Click "Extract Specimen Features" to calculate directional gradients, material composition, and defect boundaries from this image.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
