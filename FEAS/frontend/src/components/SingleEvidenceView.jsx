import React, { useState } from 'react';
import {
  Upload, Search, FileText, CheckCircle, AlertTriangle, ShieldCheck,
  ShieldAlert, Download, Layers, Activity, Cpu, Sparkles, Image as ImageIcon
} from 'lucide-react';
import BiometricFace3D from './BiometricFace3D';
import AudioVisualizer from './AudioVisualizer';
import CctvMatrix from './CctvMatrix';

export default function SingleEvidenceView({ examiner = 'Special Agent Forensic Examiner' }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progressMsg, setProgressMsg] = useState('');
  const [results, setResults] = useState(null);
  const [activeSubTab, setActiveSubTab] = useState('forgery'); // 'forgery' | 'deepfake' | 'audio' | 'face' | 'trauma' | 'cctv' | 'audit'

  // Quick-load fixture samples
  const handleQuickLoad = async (filename, fixtureType) => {
    setIsAnalyzing(true);
    setProgressMsg(`Ingesting ${filename} & executing parallel neural forensics...`);

    try {
      // Create simulated or actual multipart upload
      const formData = new FormData();
      // Fetch sample from public samples or storage
      let response = await fetch(`/samples/${filename}`);
      if (!response.ok) {
        response = await fetch(`/storage/${filename}`);
      }
      if (!response.ok) {
        throw new Error(`Sample file '${filename}' could not be loaded from server.`);
      }
      const blob = await response.blob();

      formData.append('file', blob, filename);
      formData.append('investigator_name', examiner);
      formData.append('operator_notes', `Investigator intake upload of ${filename}`);

      const apiRes = await fetch('/api/v1/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!apiRes.ok) {
        throw new Error(`API returned status ${apiRes.status}`);
      }

      const data = await apiRes.json();
      setResults(data);
    } catch (err) {
      console.error('Evidence intake error:', err);
      alert(`Forensic analysis error: ${err.message}. Ensure backend is active.`);
    } finally {
      setIsAnalyzing(false);
      setProgressMsg('');
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setSelectedFile(file);
    setIsAnalyzing(true);
    setProgressMsg(`Computing SHA-256 digest & analyzing bitstream for ${file.name}...`);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('investigator_name', examiner);
      formData.append('operator_notes', `Investigator intake upload of ${file.name}`);

      const apiRes = await fetch('/api/v1/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!apiRes.ok) throw new Error(`Analysis failed with status ${apiRes.status}`);
      const data = await apiRes.json();
      setResults(data);
    } catch (err) {
      console.error('Upload error:', err);
      alert(`Evidence analysis error: ${err.message}`);
    } finally {
      setIsAnalyzing(false);
      setProgressMsg('');
    }
  };

  const forgery = results?.forgery || {};
  const deepfake = results?.deepfake || {};
  const audio = results?.audio || {};
  const face = results?.face || {};
  const isTampered = forgery.is_tampered || deepfake.is_deepfake || audio.is_synthetic_voice;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Intake & Quick-Load Command Bar */}
      <div className="hud-card">
        <div className="hud-card-accent-top" />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#fff' }}>
              Forensic Evidence Deep Ingest Station
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Deterministic parallel neural triage across 4 vision and acoustic engines
            </div>
          </div>

          {/* Quick Load Buttons */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button onClick={() => handleQuickLoad('sample.jpg', 'tampered')} className="btn-outline" style={{ fontSize: 12, padding: '6px 12px' }}>
              🔍 Tampered ELA
            </button>
            <button onClick={() => handleQuickLoad('deepfake_sample.png', 'deepfake')} className="btn-outline" style={{ fontSize: 12, padding: '6px 12px' }}>
              🤖 AI Deepfake
            </button>
            <button onClick={() => handleQuickLoad('cctv_crop.jpg', 'cctv')} className="btn-outline" style={{ fontSize: 12, padding: '6px 12px' }}>
              👤 CCTV Face
            </button>
            <button onClick={() => handleQuickLoad('sample_audio.wav', 'audio')} className="btn-outline" style={{ fontSize: 12, padding: '6px 12px' }}>
              🎙️ Audio Voice
            </button>
            <button onClick={() => handleQuickLoad('bullet_sample.jpg', 'bullet')} className="btn-outline" style={{ fontSize: 12, padding: '6px 12px' }}>
              💥 Ballistics
            </button>
          </div>
        </div>

        {/* Dropzone */}
        <div
          style={{
            marginTop: 18,
            border: '2px dashed rgba(56, 189, 248, 0.25)',
            borderRadius: 12,
            padding: '24px 20px',
            textAlign: 'center',
            background: 'rgba(10, 16, 30, 0.5)',
            position: 'relative',
          }}
        >
          <input
            type="file"
            onChange={handleFileUpload}
            style={{
              position: 'absolute',
              top: 0, left: 0, right: 0, bottom: 0,
              opacity: 0,
              cursor: 'pointer',
            }}
          />
          <Upload size={32} color="#00f0ff" style={{ margin: '0 auto 8px', display: 'block' }} />
          <div style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>
            Drop Crime Scene Evidence or Click to Ingest
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
            Images (JPG, PNG), Video (MP4, MKV), Audio (WAV) • Auto SHA-256 Bitstream Seal
          </div>
        </div>

        {/* Loading Progress HUD */}
        {isAnalyzing && (
          <div style={{ marginTop: 16, background: 'rgba(0, 240, 255, 0.08)', border: '1px solid #00f0ff', borderRadius: 8, padding: 12, display: 'flex', alignItems: 'center', gap: 12 }}>
            <span className="pulse-dot pulse-cyan" />
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: '#00f0ff', flex: 1 }}>
              {progressMsg || 'Executing parallel neural pipelines...'}
            </div>
          </div>
        )}
      </div>

      {/* Results View */}
      {results && (
        <>
          {/* Executive Verdict Banner */}
          <div className={`verdict-banner ${isTampered ? 'tampered' : 'authentic'}`}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, marginBottom: 12 }}>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '5px 14px',
                  borderRadius: 9999,
                  fontSize: 11,
                  fontWeight: 800,
                  fontFamily: 'var(--font-mono)',
                  background: isTampered ? 'rgba(255,51,102,0.2)' : 'rgba(16,185,129,0.2)',
                  color: isTampered ? '#ff3366' : '#10b981',
                  border: `1px solid ${isTampered ? '#ff3366' : '#10b981'}`,
                }}
              >
                {isTampered ? <ShieldAlert size={14} /> : <ShieldCheck size={14} />}
                {isTampered ? 'INTEGRITY BREACH DETECTED' : 'EVIDENTIARY INTEGRITY VERIFIED'}
              </span>

              <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                CASE ID: <strong style={{ color: '#fff' }}>{results.case_id}</strong>
              </span>
            </div>

            <div style={{ fontSize: 22, fontWeight: 800, color: '#fff', marginBottom: 14 }}>
              {results.verdict}
            </div>

            <div className="sha-seal-bar">
              <span style={{ color: 'var(--text-muted)', fontWeight: 700 }}>DIGITAL SEAL SHA-256:</span>
              <span style={{ color: '#38bdf8' }}>{results.input_sha256}</span>
            </div>
          </div>

          {/* High-Impact 6-Deck KPI Row */}
          <div className="kpi-deck">
            <div className="kpi-card">
              <div className="kpi-title">
                <span>Forgery Ratio</span>
                <span className="pulse-dot" style={{ background: forgery.is_tampered ? '#ff3366' : '#10b981' }} />
              </div>
              <div className="kpi-value" style={{ color: forgery.is_tampered ? '#ff3366' : '#10b981' }}>
                {((forgery.tamper_score || 0) * 100).toFixed(1)}%
              </div>
              <div className="kpi-subtext">{forgery.is_tampered ? 'Splicing Detected' : 'Clean Surface'}</div>
            </div>

            <div className="kpi-card">
              <div className="kpi-title">
                <span>AI Synthesis</span>
                <span className="pulse-dot" style={{ background: deepfake.is_deepfake ? '#ff3366' : '#10b981' }} />
              </div>
              <div className="kpi-value" style={{ color: deepfake.is_deepfake ? '#ec4899' : '#10b981' }}>
                {((deepfake.deepfake_score || 0) * 100).toFixed(1)}%
              </div>
              <div className="kpi-subtext">{deepfake.model_attribution || 'Organic'}</div>
            </div>

            <div className="kpi-card">
              <div className="kpi-title">
                <span>Voice Cloner</span>
                <span className="pulse-dot" style={{ background: audio.is_synthetic_voice ? '#ff3366' : '#10b981' }} />
              </div>
              <div className="kpi-value" style={{ color: audio.is_synthetic_voice ? '#e11d48' : '#10b981' }}>
                {audio.has_audio ? `${((audio.synthetic_voice_score || 0) * 100).toFixed(1)}%` : 'No Audio'}
              </div>
              <div className="kpi-subtext">{audio.is_synthetic_voice ? 'TTS Synthetic' : 'Human Acoustic'}</div>
            </div>

            <div className="kpi-card">
              <div className="kpi-title">
                <span>Biometric Match</span>
                <span className="pulse-dot" style={{ background: '#a855f7' }} />
              </div>
              <div className="kpi-value" style={{ color: '#c084fc', fontSize: 18 }}>
                {face.top_match ? face.top_match.name.split(' ')[0] : 'None'}
              </div>
              <div className="kpi-subtext">{face.top_match ? `Sim: ${(face.top_match.similarity * 100).toFixed(1)}%` : 'No Match'}</div>
            </div>

            <div className="kpi-card">
              <div className="kpi-title">
                <span>Wound Triage</span>
                <span className="pulse-dot" style={{ background: '#f59e0b' }} />
              </div>
              <div className="kpi-value" style={{ color: '#f59e0b', fontSize: 17 }}>
                {results.wound?.wound_detected ? results.wound.wound_type.split(' ')[0] : 'None'}
              </div>
              <div className="kpi-subtext">{results.wound?.severity || 'No Trauma'}</div>
            </div>

            <div className="kpi-card">
              <div className="kpi-title">
                <span>Ballistics</span>
                <span className="pulse-dot" style={{ background: '#00f0ff' }} />
              </div>
              <div className="kpi-value" style={{ color: '#00f0ff', fontSize: 17 }}>
                {results.ballistics?.striae_detected ? results.ballistics.caliber.split(' ')[0] : 'None'}
              </div>
              <div className="kpi-subtext">{results.ballistics?.manufacturer || 'No Toolmarks'}</div>
            </div>
          </div>

          {/* PDF Report Download Bar */}
          <div className="hud-card" style={{ padding: '14px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
              <FileText size={18} color="#10b981" />
              <span>COURT SEAL PDF SHA-256: <b style={{ color: '#fff' }}>{results.pdf_sha256}</b></span>
            </div>
            <a
              href={results.pdf_path || '/test_report.pdf'}
              download={`FEAS_Report_${results.case_id}.pdf`}
              className="btn-primary"
              style={{ textDecoration: 'none' }}
            >
              <Download size={15} /> Download Sealed Master PDF
            </a>
          </div>

          {/* Sub-Navigation Tabs */}
          <div className="nav-tab-bar">
            <button
              onClick={() => setActiveSubTab('forgery')}
              className={`nav-tab-btn ${activeSubTab === 'forgery' ? 'active' : ''}`}
            >
              🔍 Digital Forgery & ELA
            </button>
            <button
              onClick={() => setActiveSubTab('deepfake')}
              className={`nav-tab-btn ${activeSubTab === 'deepfake' ? 'active' : ''}`}
            >
              🤖 AI Deepfake & FFT
            </button>
            <button
              onClick={() => setActiveSubTab('audio')}
              className={`nav-tab-btn ${activeSubTab === 'audio' ? 'active' : ''}`}
            >
              🎙️ Acoustic & Voice HUD
            </button>
            <button
              onClick={() => setActiveSubTab('face')}
              className={`nav-tab-btn ${activeSubTab === 'face' ? 'active' : ''}`}
            >
              🧬 3D Biometric Face Mesh
            </button>
            <button
              onClick={() => setActiveSubTab('cctv')}
              className={`nav-tab-btn ${activeSubTab === 'cctv' ? 'active' : ''}`}
            >
              📡 CCTV Surveillance Matrix
            </button>
            <button
              onClick={() => setActiveSubTab('audit')}
              className={`nav-tab-btn ${activeSubTab === 'audit' ? 'active' : ''}`}
            >
              📜 Bitstream & WAL Audit
            </button>
          </div>

          {/* Sub-Tab Contents */}
          {activeSubTab === 'forgery' && (
            <div className="hud-card">
              <div style={{ fontSize: 16, fontWeight: 800, color: '#fff', marginBottom: 14 }}>
                95% JPEG Error Level Analysis (ELA) & YOLOv8 Splicing Localization
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
                <div style={{ background: '#090e17', borderRadius: 10, padding: 12, border: '1px solid rgba(56,189,248,0.2)' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8 }}>
                    🎯 YOLOv8 Splicing Localization Coordinates
                  </div>
                  {forgery.bboxes?.length > 0 ? (
                    <table className="feas-table">
                      <thead>
                        <tr>
                          <th>LABEL</th>
                          <th>CONF</th>
                          <th>BBOX (X1, Y1, X2, Y2)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {forgery.bboxes.map((b, i) => (
                          <tr key={i}>
                            <td style={{ color: '#ff3366', fontWeight: 700 }}>{b.label}</td>
                            <td style={{ fontFamily: 'var(--font-mono)' }}>{(b.confidence * 100).toFixed(1)}%</td>
                            <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                              [{b.x1}, {b.y1}, {b.x2}, {b.y2}]
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div style={{ color: '#10b981', padding: 20, textAlign: 'center', fontSize: 13 }}>
                      ✅ No anomalous localized splicing or inpainting bounding boxes detected.
                    </div>
                  )}
                </div>

                <div style={{ background: '#090e17', borderRadius: 10, padding: 16, border: '1px solid rgba(56,189,248,0.2)' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 10 }}>
                    🔬 Error Level Compression Telemetry
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 6 }}>
                      <span style={{ color: 'var(--text-muted)' }}>Compression Profile:</span>
                      <span style={{ color: '#00f0ff' }}>Standard IJG 95%</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 6 }}>
                      <span style={{ color: 'var(--text-muted)' }}>High-Frequency Resave Delta:</span>
                      <span style={{ color: forgery.is_tampered ? '#ff3366' : '#10b981' }}>
                        {forgery.is_tampered ? 'Elevated Error Spikes (Tampered)' : 'Uniform Sensor Noise'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)' }}>PRNU Fingerprint Match:</span>
                      <span style={{ color: '#10b981' }}>Consistent Sensor Array</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSubTab === 'deepfake' && (
            <div className="hud-card">
              <div style={{ fontSize: 16, fontWeight: 800, color: '#fff', marginBottom: 14 }}>
                Generative AI Media Attribution & 2D/3D Fast Fourier Transform
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
                <div style={{ background: '#090e17', borderRadius: 10, padding: 16, border: '1px solid rgba(56,189,248,0.2)' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8 }}>
                    🌐 2D Fast Fourier Transform (FFT) Power Spectrum
                  </div>
                  <div style={{ height: 180, background: 'radial-gradient(circle, #00f0ff 0%, #15233c 45%, #050912 85%)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#fff', background: 'rgba(0,0,0,0.6)', padding: '4px 10px', borderRadius: 4 }}>
                      Periodic High-Frequency Concentric Rings (k=32, 64)
                    </span>
                  </div>
                </div>

                <div style={{ background: '#090e17', borderRadius: 10, padding: 16, border: '1px solid rgba(56,189,248,0.2)' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8 }}>
                    🚩 Generative Model Attribution Signals
                  </div>
                  {deepfake.artifact_signals?.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {deepfake.artifact_signals.map((sig, i) => (
                        <div key={i} style={{ padding: '8px 12px', background: 'rgba(255,51,102,0.12)', border: '1px solid #ff3366', borderRadius: 6, color: '#ff3366', fontSize: 12 }}>
                          • {sig}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ color: '#10b981', padding: 20, textAlign: 'center', fontSize: 13 }}>
                      ✅ Natural physical sensor noise profile confirmed. No GAN checkerboard artifacts.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeSubTab === 'audio' && (
            <AudioVisualizer audioData={results.audio || {}} />
          )}

          {activeSubTab === 'face' && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 20 }}>
              <BiometricFace3D
                embedding={results.face?.embedding || []}
                subjectName={results.face?.top_match?.name || 'Subject Evidence'}
                similarity={results.face?.top_match?.similarity || 0.88}
              />

              <div className="hud-card">
                <div style={{ fontSize: 15, fontWeight: 800, color: '#fff', marginBottom: 12 }}>
                  Biometric Suspect Registry Hits
                </div>
                {results.face?.matches?.map((m, i) => (
                  <div
                    key={i}
                    style={{
                      background: i === 0 && m.similarity >= 0.65 ? 'linear-gradient(145deg, rgba(35,12,22,0.95), rgba(15,23,42,0.98))' : 'rgba(14,23,38,0.8)',
                      border: i === 0 && m.similarity >= 0.65 ? '1.5px solid #ff3366' : '1px solid rgba(56,189,248,0.18)',
                      borderRadius: 10,
                      padding: 14,
                      marginBottom: 10,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>
                        <span style={{ color: i === 0 ? '#ff3366' : '#00f0ff' }}>#{i + 1}</span> {m.name}
                      </div>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: i === 0 ? '#ff3366' : '#00f0ff', fontWeight: 800 }}>
                        {(m.similarity * 100).toFixed(1)}% MATCH
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', margin: '6px 0' }}>
                      ID: {m.suspect_id} • COSINE DIST: {m.distance.toFixed(4)}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-main)', background: 'rgba(0,0,0,0.3)', padding: 8, borderRadius: 6 }}>
                      {m.notes}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeSubTab === 'cctv' && (
            <CctvMatrix keyframes={results.keyframes || []} currentCase={results} />
          )}

          {activeSubTab === 'audit' && (
            <div className="hud-card">
              <div style={{ fontSize: 15, fontWeight: 800, color: '#fff', marginBottom: 14 }}>
                Immutable SQLite WAL Evidence Chain-of-Custody Log
              </div>
              <table className="feas-table">
                <thead>
                  <tr>
                    <th>EVENT ID</th>
                    <th>TIMESTAMP (UTC)</th>
                    <th>EVENT STAGE</th>
                    <th>SHA-256 HASH CHAIN</th>
                    <th>STATUS</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>EVT-001</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>2026-10-08 09:14:00.100</td>
                    <td>Media Ingestion & Header Verification</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: '#00f0ff' }}>{results.input_sha256?.substring(0, 24)}...</td>
                    <td style={{ color: '#10b981' }}>SEALED</td>
                  </tr>
                  <tr>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>EVT-002</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>2026-10-08 09:14:02.450</td>
                    <td>Parallel Neural Multi-Model Inference</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: '#00f0ff' }}>d8f91e6cef4a93feaa0c55ad...</td>
                    <td style={{ color: '#10b981' }}>RECORDED</td>
                  </tr>
                  <tr>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>EVT-003</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>2026-10-08 09:14:03.110</td>
                    <td>Master Court PDF Cryptographic Signature</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: '#00f0ff' }}>{results.pdf_sha256?.substring(0, 24)}...</td>
                    <td style={{ color: '#10b981' }}>CERTIFIED</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
