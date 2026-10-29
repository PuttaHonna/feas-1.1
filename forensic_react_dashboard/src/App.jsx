import React, { useState } from "react";
import {
  Search,
  ScanFace,
  Stethoscope,
  Sparkles,
  Mic,
  Video,
  Crosshair,
  ShieldCheck,
  FileText,
  Upload,
  Activity,
  Image as ImageIcon,
  AlertTriangle,
  X,
  CheckCircle2,
  Lock,
  Cpu,
} from "lucide-react";
import { jsPDF } from "jspdf";
import ForensicScene3D from "./components/ForensicScene3D";

const modules = [
  ["tampering", "Image Tampering", Search, "Tampering & Forgery Localization (CASIA/CoMoFoD)"],
  ["cctv", "CCTV Surveillance", ScanFace, "Video Enhancement & 10-Class COCO Object Tracking"],
  ["wound", "Wound Research", Stethoscope, "Ethically-Gated Wound Image Classification (Research-Only)"],
  ["ballistics", "Toolmark Retrieval", Crosshair, "512-D Latent Feature Similarity Retrieval"],
  ["deepfake", "AI Deepfake Review", Sparkles, "Synthetic Generation Artifact Analysis"],
  ["audio", "Acoustic Integrity", Mic, "Audio Spectral Hash & Discontinuity Check"],
  ["video", "Keyframe Analyzer", Video, "1fps Keyframe Sequence Quality Inspection"],
];

function Lightfall() {
  return (
    <div className="lightfall">
      <i className="beam one" />
      <i className="beam two" />
      <i className="beam three" />
      <i className="glow" />
    </div>
  );
}

export default function App() {
  const [selected, setSelected] = useState("tampering");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [mode, setMode] = useState("Live Real Model");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [consentAcknowledged, setConsentAcknowledged] = useState(false);

  const activeModule = modules.find((m) => m[0] === selected) || modules[0];

  function chooseModule(mod) {
    setSelected(mod[0]);
    setResult(null);
  }

  function triggerFilePicker() {
    document.getElementById("file-input")?.click();
  }

  function handleFileChange(e) {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      if (f.type.startsWith("image/")) {
        setPreview(URL.createObjectURL(f));
      } else {
        setPreview("");
      }
      setResult(null);
    }
  }

  async function analyze() {
    if (!file) {
      triggerFilePicker();
      return;
    }

    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("investigator_name", "Forensic Examiner");
      fd.append("module", selected);

      const res = await fetch("http://localhost:8000/api/v1/analyze", {
        method: "POST",
        body: fd,
      });

      if (res.ok) {
        const data = await res.json();
        const entry = {
          id: Date.now(),
          module: activeModule[1],
          file: file.name,
          mode: "Live Neural Verification",
          status: data.verdict || "ANALYSIS COMPLETED",
          sha256: data.input_sha256,
          workingSha256: data.working_sha256,
          caseId: data.case_id,
          elapsed: data.elapsed_seconds,
          qualityPassed: data.quality_passed,
          details: data.details || {},
          disclaimer: data.disclaimer,
          time: new Date().toLocaleString(),
        };
        setResult(entry);
        setHistory((h) => [entry, ...h]);
      } else {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server responded with ${res.status}`);
      }
    } catch (err) {
      // Graceful verified fallback notice
      const fallbackEntry = {
        id: Date.now(),
        module: activeModule[1],
        file: file?.name || "Evidence File",
        mode: "Connection Issue",
        status: "BACKEND NOT REACHED",
        sha256: "Pending local computation",
        note: `Could not connect to FastAPI at http://localhost:8000 (${err.message}). Ensure backend daemon is active.`,
        disclaimer: "Experimental output — requires qualified human review.",
        time: new Date().toLocaleString(),
      };
      setResult(fallbackEntry);
      setHistory((h) => [fallbackEntry, ...h]);
    } finally {
      setBusy(false);
    }
  }

  function exportPdfReport() {
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text("DEEP LEARNING FORENSICS INVESTIGATOR", 14, 18);
    doc.setFontSize(10);
    doc.text("Automated Technical Inspection Report", 14, 25);
    doc.setFontSize(8);
    doc.setTextColor(120);
    doc.text(
      "CONFIDENTIAL & EXPERIMENTAL — Not court-admissible alone. Requires certified forensic examiner sign-off.",
      14,
      31
    );
    doc.setTextColor(0);

    let y = 42;
    const entries = history.length ? history : result ? [result] : [];
    if (!entries.length) {
      doc.text("No evidentiary analysis records in current session.", 14, y);
    }

    entries.forEach((r, idx) => {
      if (y > 250) {
        doc.addPage();
        y = 20;
      }
      doc.setFontSize(11);
      doc.text(`${idx + 1}. [${r.module}] ${r.status}`, 14, y);
      y += 6;
      doc.setFontSize(9);
      const textLines = [
        `Target File: ${r.file}`,
        `Original SHA-256: ${r.sha256 || "N/A"}`,
        `Working Copy SHA-256: ${r.workingSha256 || "N/A"}`,
        `Timestamp: ${r.time} | Execution Time: ${r.elapsed ? r.elapsed + "s" : "N/A"}`,
        `Quality Gate: ${r.qualityPassed !== undefined ? (r.qualityPassed ? "PASSED" : "FLAGGED / LOW QUALITY") : "N/A"}`,
        `Mandatory Disclaimer: ${r.disclaimer || "Experimental model output — requires qualified human review."}`,
      ];
      const splitLines = doc.splitTextToSize(textLines.join("\n"), 180);
      doc.text(splitLines, 14, y);
      y += splitLines.length * 5 + 8;
    });

    doc.save("forensic-investigation-technical-report.pdf");
  }

  return (
    <div className="app">
      <Lightfall />
      <header>
        <div className="brand">
          <ShieldCheck size={20} />
        </div>
        <div className="brandcopy">
          <b>
            FORENSIC<span>LAB</span> 2.0
          </b>
          <small>DEEP LEARNING FORENSICS INVESTIGATOR</small>
        </div>
        <aside>
          <i /> API RUNNING (PORT 8000) <em>React 19 + Three.js</em>
        </aside>
      </header>

      <main>
        <section className="hero">
          <label>— SCIENTIFIC DIGITAL FORENSICS ENGINE</label>
          <h1>
            Investigate with <span>verifiable integrity.</span>
          </h1>
          <p>
            Cryptographic SHA-256 vault intake, tamper detection, deterministic CCTV tracking, and 512-D latent feature retrieval.
          </p>
        </section>

        {/* Interactive Three.js 3D Viewport */}
        <ForensicScene3D
          activeMode={selected === "ballistics" ? "latent" : selected === "cctv" ? "scanner" : "vault"}
          statusText={file ? `EVIDENCE LOADED: ${file.name.toUpperCase()}` : "CRYPTOGRAPHIC VAULT READY"}
        />

        <div className="grid">
          {/* Module Selector Panel */}
          <section className="panel">
            <div className="heading">
              <div>
                <h2>
                  <strong>ϟ</strong> Forensic Analysis Modules
                </h2>
                <p>Select a specialized computer-vision analysis pipeline.</p>
              </div>
              <small className="badge">{modules.length} PIPELINES</small>
            </div>

            <div className="assets">
              {modules.map(([id, label, Icon, desc]) => (
                <button
                  key={id}
                  className={`${id === "video" ? "wide" : ""} ${selected === id ? "active" : ""}`}
                  onClick={() => chooseModule(modules.find((m) => m[0] === id))}
                  title={desc}
                >
                  <Icon size={15} />
                  {label}
                </button>
              ))}
            </div>

            <input
              id="file-input"
              type="file"
              hidden
              accept="image/*,video/*"
              onChange={handleFileChange}
            />

            <div style={{ marginTop: "14px" }}>
              <button
                className="export"
                style={{ width: "100%", justifyContent: "center" }}
                onClick={triggerFilePicker}
              >
                <Upload size={14} /> Browse Evidence File...
              </button>
            </div>

            <p className="hint">
              ✦ Uploaded evidence is strictly hashed with SHA-256 and locked read-only (0o444) in the audit vault.
            </p>
          </section>

          {/* Analysis Console */}
          <section className="panel">
            <div className="heading">
              <div>
                <h2>
                  <Activity size={17} /> Analysis Console
                </h2>
                <p>Configure and trigger verified neural inference.</p>
              </div>
              <small className="mode">LIVE MODEL</small>
            </div>

            <label className="field">INFERENCE PIPELINE</label>
            <div style={{ fontSize: "12px", color: "#93c5fd", marginBottom: "10px", fontWeight: "600" }}>
              {activeModule[3]}
            </div>

            {selected === "wound" && (
              <div style={{
                background: "rgba(239, 68, 68, 0.12)",
                border: "1px solid rgba(239, 68, 68, 0.35)",
                borderRadius: "8px",
                padding: "10px",
                marginBottom: "12px"
              }}>
                <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11px", color: "#fca5a5", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={consentAcknowledged}
                    onChange={(e) => setConsentAcknowledged(e.target.checked)}
                  />
                  <span>Confirm research-only use &amp; patient consent adherence.</span>
                </label>
              </div>
            )}

            <div className="selected">
              <div className="selicon">
                {React.createElement(activeModule[2], { size: 20 })}
              </div>
              <div>
                <b>{activeModule[1]}</b>
                <small>{file ? `${file.name} (${(file.size / 1024).toFixed(1)} KB)` : "No evidence file chosen yet."}</small>
              </div>
              {file && (
                <button
                  className="remove"
                  onClick={() => {
                    setFile(null);
                    setPreview("");
                    setResult(null);
                  }}
                  title="Remove File"
                >
                  <X size={15} />
                </button>
              )}
            </div>

            {preview && (
              <div className="preview">
                <img src={preview} alt="Evidence preview" />
              </div>
            )}

            <button
              className="primary"
              disabled={busy || (selected === "wound" && !consentAcknowledged)}
              onClick={analyze}
            >
              <Cpu size={15} />
              {busy ? "Running Neural Inference…" : file ? "Execute Forensic Analysis" : "Browse & Load Evidence"}
            </button>

            <p className="warning">
              <AlertTriangle size={14} /> Mandatory Standard: Experimental model output — requires qualified human review.
            </p>
          </section>
        </div>

        {/* Results & Audit Trail */}
        <section className="panel results">
          <div className="heading">
            <div>
              <h2>
                <Activity size={17} /> Verified Findings &amp; Evidence Audit Trail
              </h2>
              <p>Cryptographic hash verification and neural model metrics.</p>
            </div>
            <button className="export" onClick={exportPdfReport}>
              <FileText size={14} /> Export Forensic PDF Report
            </button>
          </div>

          {result && (
            <article style={{ background: "rgba(15, 23, 42, 0.8)", border: "1px solid rgba(56, 189, 248, 0.3)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <b>
                  <CheckCircle2 size={14} style={{ display: "inline", marginRight: "6px", color: "#34d399" }} />
                  {result.module} — {result.status}
                </b>
                <small style={{ color: "#38bdf8", fontFamily: "monospace" }}>
                  {result.elapsed ? `${result.elapsed}s` : ""}
                </small>
              </div>

              {result.sha256 && (
                <div style={{ fontSize: "10px", color: "#94a3b8", fontFamily: "monospace", margin: "6px 0", wordBreak: "break-all" }}>
                  <Lock size={11} style={{ display: "inline", marginRight: "4px", color: "#38bdf8" }} />
                  <strong>Original SHA-256:</strong> {result.sha256}
                </div>
              )}

              {result.workingSha256 && (
                <div style={{ fontSize: "10px", color: "#94a3b8", fontFamily: "monospace", margin: "6px 0", wordBreak: "break-all" }}>
                  <Lock size={11} style={{ display: "inline", marginRight: "4px", color: "#34d399" }} />
                  <strong>Working Copy SHA-256:</strong> {result.workingSha256}
                </div>
              )}

              {result.details && Object.keys(result.details).length > 0 && (
                <div style={{ background: "rgba(0,0,0,0.3)", padding: "8px", borderRadius: "6px", margin: "8px 0", fontSize: "10px" }}>
                  {result.details.prediction && (
                    <div>Prediction: <strong>{result.details.prediction}</strong> (Confidence: {(result.details.confidence * 100).toFixed(1)}%)</div>
                  )}
                  {result.details.quality_metrics && (
                    <div>Quality Gate: Blur Score = {result.details.quality_metrics.blur_score?.toFixed(1) || "N/A"}, Exposure = {result.details.quality_metrics.mean_exposure?.toFixed(1) || "N/A"}</div>
                  )}
                  {result.details.warning && (
                    <div style={{ color: "#f59e0b" }}>⚠️ Warning: {result.details.warning}</div>
                  )}
                </div>
              )}

              {result.note && <p>{result.note}</p>}

              <footer style={{ marginTop: "10px", borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "6px" }}>
                <span>File: {result.file}</span> · <span>Time: {result.time}</span>
                <div style={{ fontSize: "9px", color: "#f59e0b", marginTop: "4px" }}>
                  {result.disclaimer || "Experimental model output — requires qualified human review."}
                </div>
              </footer>
            </article>
          )}

          {history.length === 0 && !result ? (
            <div className="empty">
              <FileText size={22} />
              <b>No analysis entries yet</b>
              <span>Choose an evidence file and run the analysis workflow to record verified findings.</span>
            </div>
          ) : (
            history.slice(0, 5).map((h) => (
              <div className="history" key={h.id}>
                <b>{h.module}</b>
                <span>{h.status}</span>
                <small>
                  {h.file} · SHA: {h.sha256 ? h.sha256.substring(0, 16) + "…" : "N/A"} · {h.time}
                </small>
              </div>
            ))
          )}
        </section>

        <footer className="foot">
          <b>FORENSICLAB 2.0</b>
          <span>Verifiable Evidence Intake · Strict Cryptographic Hashing · Certified Examiner Required</span>
        </footer>
      </main>
    </div>
  );
}