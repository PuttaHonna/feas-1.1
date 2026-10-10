import React, { useState } from 'react';
import { Layers, Play, Download, CheckCircle, ShieldAlert, Cpu, Clock, FileText } from 'lucide-react';

export default function BatchTriageView({ examiner = 'Special Agent Forensic Examiner' }) {
  const [isRunning, setIsRunning] = useState(false);
  const [batchData, setBatchData] = useState(null);

  const runBatchTest = async () => {
    setIsRunning(true);
    setBatchData(null);

    // Simulate or call batch endpoint
    setTimeout(() => {
      setBatchData({
        batch_id: `BATCH-${Math.random().toString(36).substring(2, 10).toUpperCase()}`,
        pdf_sha256: 'a6c8e9f13456bb0123984712093485abcedf01928374650192837465abcde123',
        summary: {
          total_files: 6,
          tampered_count: 3,
          deepfake_count: 2,
          tamper_rate: 0.50,
          average_seconds_per_file: 0.84,
        },
        items: [
          { case_id: 'CASE-001', filename: 'sample_tampered.jpg', tamper_score: 0.942, deepfake_score: 0.041, verdict: 'TAMPERED', match: 'None', status: 'FLAGGED' },
          { case_id: 'CASE-002', filename: 'deepfake_sample.png', tamper_score: 0.120, deepfake_score: 0.914, verdict: 'SYNTHETIC AI', match: 'None', status: 'FLAGGED' },
          { case_id: 'CASE-003', filename: 'sample_audio.wav', tamper_score: 0.080, deepfake_score: 0.880, verdict: 'SYNTHETIC VOICE', match: 'None', status: 'FLAGGED' },
          { case_id: 'CASE-004', filename: 'cctv_crop.jpg', tamper_score: 0.021, deepfake_score: 0.052, verdict: 'AUTHENTIC', match: 'Marcus Vance (91.4%)', status: 'CLEARED' },
          { case_id: 'CASE-005', filename: 'wound_sample.jpg', tamper_score: 0.035, deepfake_score: 0.010, verdict: 'AUTHENTIC', match: 'None', status: 'CLEARED' },
          { case_id: 'CASE-006', filename: 'bullet_sample.jpg', tamper_score: 0.015, deepfake_score: 0.020, verdict: 'AUTHENTIC', match: 'None', status: 'CLEARED' },
        ],
      });
      setIsRunning(false);
    }, 1500);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Batch Control Header */}
      <div className="hud-card">
        <div className="hud-card-accent-top" />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 14 }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Layers size={18} color="#00f0ff" />
              <span>High-Throughput Batch Evidence Triage</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Parallel multi-evidence assessment matrix with consolidated cryptographic audit report
            </div>
          </div>

          <button
            onClick={runBatchTest}
            disabled={isRunning}
            className="btn-primary"
            style={{ opacity: isRunning ? 0.7 : 1 }}
          >
            <Play size={15} /> {isRunning ? 'Processing Batch Matrix...' : '⚡ Test All 6 Evidentiary Assets'}
          </button>
        </div>
      </div>

      {/* Batch Summary Metrics */}
      {batchData && (
        <>
          <div className="kpi-deck">
            <div className="kpi-card">
              <div className="kpi-title">Total Evidence Files</div>
              <div className="kpi-value" style={{ color: '#00f0ff' }}>
                {batchData.summary.total_files} Items
              </div>
              <div className="kpi-subtext">Multi-Thread Ingestion</div>
            </div>

            <div className="kpi-card">
              <div className="kpi-title">Tampering Flags</div>
              <div className="kpi-value" style={{ color: '#ff3366' }}>
                {batchData.summary.tampered_count}
              </div>
              <div className="kpi-subtext">{(batchData.summary.tamper_rate * 100).toFixed(0)}% Flagged Rate</div>
            </div>

            <div className="kpi-card">
              <div className="kpi-title">Generative Deepfakes</div>
              <div className="kpi-value" style={{ color: '#ec4899' }}>
                {batchData.summary.deepfake_count}
              </div>
              <div className="kpi-subtext">AI Synthesis Detected</div>
            </div>

            <div className="kpi-card">
              <div className="kpi-title">Avg Latency</div>
              <div className="kpi-value" style={{ color: '#10b981' }}>
                {batchData.summary.average_seconds_per_file}s
              </div>
              <div className="kpi-subtext">Sub-Second Execution</div>
            </div>
          </div>

          {/* Master Batch PDF Action Bar */}
          <div className="hud-card" style={{ padding: '14px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
              <FileText size={18} color="#10b981" />
              <span>CONSOLIDATED BATCH PDF SHA-256: <b style={{ color: '#fff' }}>{batchData.pdf_sha256}</b></span>
            </div>
            <button className="btn-primary">
              <Download size={15} /> Download Consolidated Batch Report
            </button>
          </div>

          {/* Master Batch Matrix Table */}
          <div className="hud-card">
            <div style={{ fontSize: 15, fontWeight: 800, color: '#fff', marginBottom: 14 }}>
              Master Evidentiary Triage Matrix
            </div>

            <table className="feas-table">
              <thead>
                <tr>
                  <th>CASE ID</th>
                  <th>EVIDENCE FILENAME</th>
                  <th>FORGERY RATIO</th>
                  <th>AI DEEPFAKE</th>
                  <th>BIOMETRIC MATCH</th>
                  <th>VERDICT</th>
                  <th>STATUS</th>
                </tr>
              </thead>
              <tbody>
                {batchData.items.map((item, idx) => (
                  <tr key={idx}>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{item.case_id}</td>
                    <td style={{ fontWeight: 600 }}>{item.filename}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: item.tamper_score > 0.5 ? '#ff3366' : '#10b981' }}>
                      {(item.tamper_score * 100).toFixed(1)}%
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: item.deepfake_score > 0.5 ? '#ec4899' : '#10b981' }}>
                      {(item.deepfake_score * 100).toFixed(1)}%
                    </td>
                    <td>{item.match}</td>
                    <td style={{ fontWeight: 700, color: item.status === 'FLAGGED' ? '#ff3366' : '#10b981' }}>
                      {item.verdict}
                    </td>
                    <td>
                      <span
                        style={{
                          padding: '3px 8px',
                          borderRadius: 4,
                          fontSize: 10,
                          fontWeight: 700,
                          background: item.status === 'FLAGGED' ? 'rgba(255,51,102,0.15)' : 'rgba(16,185,129,0.15)',
                          color: item.status === 'FLAGGED' ? '#ff3366' : '#10b981',
                          border: `1px solid ${item.status === 'FLAGGED' ? '#ff3366' : '#10b981'}`,
                        }}
                      >
                        {item.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
