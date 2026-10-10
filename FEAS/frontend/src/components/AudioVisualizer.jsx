import React, { useEffect, useRef, useState } from 'react';
import { Mic, Volume2, Activity, Play, Pause, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function AudioVisualizer({ audioData = {} }) {
  const canvasRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);

  // Audio metrics
  const duration = audioData.duration_seconds || 4.2;
  const sampleRate = audioData.sample_rate_hz || 44100;
  const snr = audioData.snr_db !== undefined ? audioData.snr_db : 24.5;
  const pitchJitter = audioData.pitch_jitter !== undefined ? audioData.pitch_jitter : 0.018;
  const synthScore = audioData.synthetic_voice_score !== undefined ? audioData.synthetic_voice_score : 0.12;
  const isSynth = audioData.is_synthetic_voice || synthScore > 0.5;

  // Animated Oscillogram Waveform
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let frameId;
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const w = canvas.width;
      const h = canvas.height;
      const mid = h / 2;

      // Draw Center Axis
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.15)';
      ctx.beginPath();
      ctx.moveTo(0, mid);
      ctx.lineTo(w, mid);
      ctx.stroke();

      // Oscillogram Waveform Curve
      ctx.lineWidth = 2;
      ctx.strokeStyle = isSynth ? '#ff3366' : '#00f0ff';
      ctx.shadowColor = isSynth ? '#ff3366' : '#00f0ff';
      ctx.shadowBlur = 8;
      ctx.beginPath();

      const numPoints = 120;
      for (let i = 0; i < numPoints; i++) {
        const x = (i / (numPoints - 1)) * w;
        const normX = i / numPoints;

        // Envelope shape
        const env = Math.sin(normX * Math.PI) * Math.sin(normX * 8 * Math.PI + phase);
        const noise = (Math.random() - 0.5) * (isSynth ? 4 : 12);
        const y = mid + env * (h * 0.38) + (isPlaying ? noise : 0);

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.shadowBlur = 0;

      if (isPlaying) {
        phase += 0.08;
      }

      frameId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(frameId);
  }, [isPlaying, isSynth]);

  // 6-axis Radar points computation
  const radarAxes = [
    { label: 'Pitch Jitter', val: Math.min(1, pitchJitter * 10), human: 0.25, ai: 0.05 },
    { label: 'Shimmer Amp', val: 0.35 + synthScore * 0.4, human: 0.2, ai: 0.75 },
    { label: 'Acoustic SNR', val: Math.min(1, snr / 40), human: 0.85, ai: 0.4 },
    { label: 'Spectral Centroid', val: 0.65, human: 0.5, ai: 0.9 },
    { label: 'F0 Stability', val: Math.max(0.1, 0.85 - synthScore * 0.6), human: 0.85, ai: 0.2 },
    { label: 'Harmonic Ratio', val: 0.72, human: 0.8, ai: 0.45 },
  ];

  const radarRadius = 85;
  const radarCenter = { x: 120, y: 120 };

  const getCoord = (angleIdx, value) => {
    const angle = (angleIdx / radarAxes.length) * Math.PI * 2 - Math.PI / 2;
    return {
      x: radarCenter.x + Math.cos(angle) * (radarRadius * value),
      y: radarCenter.y + Math.sin(angle) * (radarRadius * value),
    };
  };

  const evidencePath = radarAxes.map((ax, i) => {
    const pt = getCoord(i, ax.val);
    return `${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`;
  }).join(' ') + ' Z';

  const humanPath = radarAxes.map((ax, i) => {
    const pt = getCoord(i, ax.human);
    return `${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`;
  }).join(' ') + ' Z';

  const aiPath = radarAxes.map((ax, i) => {
    const pt = getCoord(i, ax.ai);
    return `${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`;
  }).join(' ') + ' Z';

  return (
    <div className="hud-card">
      <div className="hud-card-accent-top" />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Mic size={18} color="#00f0ff" />
            <span>Acoustic Oscillogram & Voiceprint Radar HUD</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            Micro-Jitter Extraction & Neural TTS Synthesis Detection
          </div>
        </div>

        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="btn-outline"
          style={{ padding: '6px 14px', fontSize: 12 }}
        >
          {isPlaying ? <><Pause size={14} /> Pause Stream</> : <><Play size={14} /> Play Acoustic Vector</>}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
        {/* Oscillogram Waveform Canvas */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
            <span>Time-Domain Oscillogram Waveform</span>
            <span style={{ color: isSynth ? '#ff3366' : '#10b981' }}>
              {isSynth ? '⚠️ SYNTHETIC AI VOCAL SPIKES' : '✅ ORGANIC VOCAL PROFILE'}
            </span>
          </div>

          <div style={{ background: '#070c17', borderRadius: 10, border: '1px solid rgba(56, 189, 248, 0.2)', padding: 10, position: 'relative' }}>
            <canvas ref={canvasRef} width={440} height={160} style={{ width: '100%', height: 'auto', display: 'block' }} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginTop: 12 }}>
            <div style={{ background: 'rgba(14,23,38,0.7)', padding: 8, borderRadius: 6, border: '1px solid rgba(56,189,248,0.1)' }}>
              <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>DURATION</div>
              <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{duration.toFixed(2)}s</div>
            </div>
            <div style={{ background: 'rgba(14,23,38,0.7)', padding: 8, borderRadius: 6, border: '1px solid rgba(56,189,248,0.1)' }}>
              <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>SAMPLING</div>
              <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{sampleRate}Hz</div>
            </div>
            <div style={{ background: 'rgba(14,23,38,0.7)', padding: 8, borderRadius: 6, border: '1px solid rgba(56,189,248,0.1)' }}>
              <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>SNR</div>
              <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{snr.toFixed(1)}dB</div>
            </div>
            <div style={{ background: 'rgba(14,23,38,0.7)', padding: 8, borderRadius: 6, border: '1px solid rgba(56,189,248,0.1)' }}>
              <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>JITTER (F0)</div>
              <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-mono)', color: isSynth ? '#ff3366' : '#10b981' }}>{(pitchJitter * 100).toFixed(2)}%</div>
            </div>
          </div>
        </div>

        {/* 6-Axis Voiceprint Radar Vector */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
            <span>Voiceprint Multi-Axis Vector Radar</span>
            <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: '#00f0ff' }}>Evidence vs Baseline</span>
          </div>

          <div style={{ background: '#070c17', borderRadius: 10, border: '1px solid rgba(56, 189, 248, 0.2)', padding: 12, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <svg width={240} height={240} viewBox="0 0 240 240">
              {/* Radar Grid Circles */}
              {[0.25, 0.5, 0.75, 1.0].map((r, i) => (
                <circle
                  key={i}
                  cx={radarCenter.x}
                  cy={radarCenter.y}
                  r={radarRadius * r}
                  fill="none"
                  stroke="rgba(56, 189, 248, 0.15)"
                  strokeDasharray={i === 3 ? 'none' : '3,3'}
                />
              ))}

              {/* Radar Radial Spokes */}
              {radarAxes.map((_, i) => {
                const pt = getCoord(i, 1.0);
                return (
                  <line
                    key={i}
                    x1={radarCenter.x}
                    y1={radarCenter.y}
                    x2={pt.x}
                    y2={pt.y}
                    stroke="rgba(56, 189, 248, 0.2)"
                  />
                );
              })}

              {/* Human Reference Polygon */}
              <path d={humanPath} fill="rgba(16, 185, 129, 0.12)" stroke="#10b981" strokeWidth={1.5} strokeDasharray="3,3" />

              {/* AI Synthetic Polygon */}
              <path d={aiPath} fill="rgba(255, 51, 102, 0.1)" stroke="#ff3366" strokeWidth={1.5} strokeDasharray="2,2" />

              {/* Evidence Acoustic Vector Polygon */}
              <path d={evidencePath} fill="rgba(0, 240, 255, 0.25)" stroke="#00f0ff" strokeWidth={2} />

              {/* Vertex Dots */}
              {radarAxes.map((ax, i) => {
                const pt = getCoord(i, ax.val);
                return <circle key={i} cx={pt.x} cy={pt.y} r={3.5} fill="#00f0ff" />;
              })}
            </svg>
          </div>

          {/* Legend */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginTop: 10, fontSize: 11, fontFamily: 'var(--font-mono)' }}>
            <span style={{ color: '#00f0ff', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, background: '#00f0ff', borderRadius: 2 }} /> Evidence
            </span>
            <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, background: '#10b981', borderRadius: 2 }} /> Human Norm
            </span>
            <span style={{ color: '#ff3366', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 8, height: 8, background: '#ff3366', borderRadius: 2 }} /> AI Cloner
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
