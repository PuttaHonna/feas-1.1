import React, { useState, useEffect } from 'react';
import { Video, ShieldAlert, Radio, Maximize2, Layers, AlertCircle, Clock, CheckCircle } from 'lucide-react';

export default function CctvMatrix({ keyframes = [], currentCase = null }) {
  const [activeLayout, setActiveLayout] = useState('quad'); // 'quad' | 'single' | 'timeline'
  const [selectedCam, setSelectedCam] = useState(1);
  const [timelineIndex, setTimelineIndex] = useState(0);
  const [currentTime, setCurrentTime] = useState('');

  // Live timecode updater
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const pad = (n) => String(n).padStart(2, '0');
      const ms = String(now.getMilliseconds()).padStart(3, '0');
      setCurrentTime(
        `${now.getUTCFullYear()}-${pad(now.getUTCMonth() + 1)}-${pad(now.getUTCDate())} ` +
        `${pad(now.getUTCHours())}:${pad(now.getUTCMinutes())}:${pad(now.getUTCSeconds())}.${ms} UTC`
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 40);
    return () => clearInterval(interval);
  }, []);

  // CCTV Channels definition
  const cameras = [
    {
      id: 1,
      name: 'CAM-01 [ENTRY ARCHWAY]',
      location: 'South Perimeter Access Gate',
      iso: 'ISO 800 • F/2.8',
      status: 'SECURE',
      statusColor: '#10b981',
      feedType: 'Optical 1080p',
      sampleImg: '/storage/sample_tampered.jpg',
    },
    {
      id: 2,
      name: 'CAM-02 [NORTH CORRIDOR]',
      location: 'Evidentiary Transit Hall B',
      iso: 'ISO 1600 • F/1.8',
      status: 'MOTION ALERT',
      statusColor: '#ff3366',
      feedType: 'Optical 1080p',
      sampleImg: '/storage/cctv_crop.jpg',
    },
    {
      id: 3,
      name: 'CAM-03 [VAULT PERIMETER - IR]',
      location: 'Secure Evidence Storage Locker',
      iso: 'SPECTRAL ELA / THERMAL',
      status: 'PRNU VERIFIED',
      statusColor: '#a855f7',
      feedType: 'Infrared & Noise Fingerprint',
      sampleImg: '/storage/deepfake_sample.png',
    },
    {
      id: 4,
      name: 'CAM-04 [NEURAL BIOMETRIC GATE]',
      location: 'Laboratory Gate #04',
      iso: 'FACENET 512-D TRACKER',
      status: 'SUSPECT TRACKED',
      statusColor: '#00f0ff',
      feedType: 'Biometric AI Interceptor',
      sampleImg: '/storage/cctv_crop.jpg',
    },
  ];

  // Anomaly event log
  const anomalyTimeline = [
    { time: '09:14:02.102', cam: 'CAM-01', type: 'Splicing Anomaly Detected', score: '94.2%', level: 'CRITICAL', icon: '🚨' },
    { time: '09:14:03.450', cam: 'CAM-02', type: 'Subject Biometric Acquisition', score: '87.8%', level: 'HIGH', icon: '👤' },
    { time: '09:14:04.112', cam: 'CAM-04', type: 'FaceNet Gallery Match #1', score: '91.4%', level: 'ALERT', icon: '🎯' },
    { time: '09:14:05.200', cam: 'CAM-03', type: 'Sensor PRNU Noise Discontinuity', score: '76.1%', level: 'MEDIUM', icon: '🔬' },
  ];

  const totalSlices = keyframes.length > 0 ? keyframes.length : 8;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Control Bar */}
      <div className="hud-card" style={{ padding: '16px 22px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Radio size={20} color="#ff3366" />
            <div>
              <div style={{ fontSize: 16, fontWeight: 800, color: '#fff', letterSpacing: '-0.3px' }}>
                Forensic CCTV Multi-Angle Surveillance Matrix
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                Hardware Stream Sensor Telemetry • 4 Active Interception Nodes
              </div>
            </div>
          </div>

          {/* Mode Switchers */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              onClick={() => setActiveLayout('quad')}
              className={`nav-tab-btn ${activeLayout === 'quad' ? 'active' : ''}`}
              style={{ padding: '7px 14px', fontSize: 12 }}
            >
              <Layers size={14} /> 4-Angle Quad
            </button>
            <button
              onClick={() => setActiveLayout('single')}
              className={`nav-tab-btn ${activeLayout === 'single' ? 'active' : ''}`}
              style={{ padding: '7px 14px', fontSize: 12 }}
            >
              <Maximize2 size={14} /> Primary Single
            </button>
            <button
              onClick={() => setActiveLayout('timeline')}
              className={`nav-tab-btn ${activeLayout === 'timeline' ? 'active' : ''}`}
              style={{ padding: '7px 14px', fontSize: 12 }}
            >
              <Clock size={14} /> Keyframe Scrubber
            </button>
          </div>
        </div>

        {/* Keyframe Timeline Scrubber Bar */}
        <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid rgba(56, 189, 248, 0.15)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, fontSize: 12, fontFamily: 'var(--font-mono)' }}>
            <span style={{ color: '#00f0ff', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Clock size={14} /> KEYFRAME TIMELINE SCRUBBER
            </span>
            <span style={{ color: 'var(--text-muted)' }}>
              Selected Slice: <strong style={{ color: '#fff' }}>#{timelineIndex + 1} of {totalSlices}</strong> (T+0{timelineIndex}s)
            </span>
          </div>

          <input
            type="range"
            min={0}
            max={totalSlices - 1}
            value={timelineIndex}
            onChange={(e) => setTimelineIndex(Number(e.target.value))}
            style={{
              width: '100%',
              accentColor: '#00f0ff',
              cursor: 'pointer',
              height: 6,
              background: 'rgba(56, 189, 248, 0.2)',
              borderRadius: 3,
            }}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
            <span>00:00:00.000</span>
            <span>00:00:01.000</span>
            <span>00:00:02.000</span>
            <span>00:00:03.000</span>
            <span>00:00:04.000</span>
            <span>00:00:05.000</span>
          </div>
        </div>
      </div>

      {/* Main CCTV Feeds Display */}
      {activeLayout === 'quad' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 16 }}>
          {cameras.map((cam) => (
            <div key={cam.id} className="cctv-chassis">
              <div className="cctv-hud-header">
                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span className="pulse-dot pulse-red" />
                  <strong>{cam.name}</strong>
                </span>
                <span style={{ color: '#00f0ff' }}>{cam.iso}</span>
              </div>

              <div className="cctv-screen">
                <div className="cctv-scanlines" />
                <div className="cctv-reticle" />

                <div className="cctv-badge-tl">
                  {currentTime || '2026-10-08 09:14:02.102 UTC'}
                </div>

                <div
                  className="cctv-badge-tr"
                  style={{
                    background: `${cam.statusColor}22`,
                    color: cam.statusColor,
                    border: `1px solid ${cam.statusColor}`,
                  }}
                >
                  {cam.status}
                </div>

                <div className="cctv-badge-br">
                  {cam.location}
                </div>

                {/* Simulated CCTV Visual Frame */}
                <div
                  style={{
                    width: '100%',
                    height: '100%',
                    background: 'radial-gradient(circle at 50% 50%, #152238 0%, #070d18 100%)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#64748b',
                    fontSize: 13,
                    fontFamily: 'var(--font-mono)',
                    position: 'relative',
                  }}
                >
                  <Video size={48} color="rgba(0, 240, 255, 0.35)" style={{ marginBottom: 8 }} />
                  <div>SENSOR LIVE: {cam.feedType}</div>
                  <div style={{ fontSize: 10, color: '#38bdf8', marginTop: 4 }}>FPS: 30.00 • BITRATE: 12.4 Mbps</div>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10, fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                <span>ENCRYPTION: <b>AES-256 GCM</b></span>
                <button
                  onClick={() => { setSelectedCam(cam.id); setActiveLayout('single'); }}
                  style={{ background: 'transparent', border: 'none', color: '#00f0ff', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
                >
                  <Maximize2 size={12} /> Expand HUD
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeLayout === 'single' && (
        <div className="cctv-chassis" style={{ padding: 18 }}>
          <div className="cctv-hud-header" style={{ fontSize: 13 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="pulse-dot pulse-red" />
              <strong>{cameras[selectedCam - 1].name} — HIGH-RESOLUTION FORENSIC HUD INTERCEPT</strong>
            </span>
            <div style={{ display: 'flex', gap: 10 }}>
              {[1, 2, 3, 4].map((id) => (
                <button
                  key={id}
                  onClick={() => setSelectedCam(id)}
                  style={{
                    padding: '3px 8px',
                    borderRadius: 4,
                    background: selectedCam === id ? '#00f0ff' : 'rgba(255,255,255,0.06)',
                    color: selectedCam === id ? '#000' : '#fff',
                    border: 'none',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    cursor: 'pointer',
                  }}
                >
                  CAM 0{id}
                </button>
              ))}
            </div>
          </div>

          <div className="cctv-screen" style={{ height: 480 }}>
            <div className="cctv-scanlines" />
            <div className="cctv-reticle" style={{ top: '15%', left: '20%', right: '20%', bottom: '15%' }} />

            <div className="cctv-badge-tl" style={{ fontSize: 12 }}>
              {currentTime} • FRAME #00{timelineIndex + 1}
            </div>

            <div
              className="cctv-badge-tr"
              style={{
                fontSize: 11,
                background: `${cameras[selectedCam - 1].statusColor}33`,
                color: cameras[selectedCam - 1].statusColor,
                border: `1px solid ${cameras[selectedCam - 1].statusColor}`,
              }}
            >
              {cameras[selectedCam - 1].status}
            </div>

            <div
              style={{
                width: '100%',
                height: '100%',
                background: 'radial-gradient(circle at 50% 50%, #172a45 0%, #060b14 100%)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative',
              }}
            >
              <Video size={72} color="rgba(0, 240, 255, 0.4)" style={{ marginBottom: 14 }} />
              <div style={{ fontSize: 18, fontWeight: 700, color: '#fff', letterSpacing: -0.3 }}>
                {cameras[selectedCam - 1].name}
              </div>
              <div style={{ fontSize: 12, color: '#38bdf8', fontFamily: 'var(--font-mono)', marginTop: 6 }}>
                LATENCY: 14ms • COMPRESSION: H.265 / HEVC • BITSTREAM SHA-256 VERIFIED
              </div>
            </div>
          </div>
        </div>
      )}

      {activeLayout === 'timeline' && (
        <div className="hud-card">
          <div style={{ fontSize: 15, fontWeight: 800, color: '#fff', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Clock size={16} color="#00f0ff" />
            <span>Keyframe Chronology & Anomaly Extraction Tape</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14 }}>
            {Array.from({ length: totalSlices }).map((_, idx) => (
              <div
                key={idx}
                onClick={() => setTimelineIndex(idx)}
                style={{
                  background: timelineIndex === idx ? 'rgba(0, 240, 255, 0.12)' : 'rgba(14, 23, 38, 0.8)',
                  border: timelineIndex === idx ? '2px solid #00f0ff' : '1px solid rgba(56, 189, 248, 0.15)',
                  borderRadius: 10,
                  padding: 10,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  boxShadow: timelineIndex === idx ? '0 0 15px rgba(0,240,255,0.3)' : 'none',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 10, fontFamily: 'var(--font-mono)', color: timelineIndex === idx ? '#00f0ff' : '#94a3b8' }}>
                  <span>SLICE #{idx + 1}</span>
                  <span>T+0{idx}s</span>
                </div>
                <div style={{ height: 100, background: '#090e17', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
                  <div className="cctv-scanlines" />
                  <Video size={24} color="rgba(0,240,255,0.3)" />
                  {idx === 2 && (
                    <div style={{ position: 'absolute', bottom: 4, left: 4, background: '#ff3366', color: '#fff', fontSize: 8, padding: '2px 4px', borderRadius: 2, fontWeight: 700 }}>
                      TAMPER
                    </div>
                  )}
                  {idx === 4 && (
                    <div style={{ position: 'absolute', bottom: 4, left: 4, background: '#00f0ff', color: '#000', fontSize: 8, padding: '2px 4px', borderRadius: 2, fontWeight: 700 }}>
                      FACE MATCH
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Optical Sensor Anomaly & Event Timeline Table */}
      <div className="hud-card">
        <div style={{ fontSize: 15, fontWeight: 800, color: '#fff', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <ShieldAlert size={18} color="#ff3366" />
          <span>Real-Time Optical Sensor Event & Anomaly Log</span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="feas-table">
            <thead>
              <tr>
                <th>TIMECODE</th>
                <th>CAMERA NODE</th>
                <th>ANOMALY SIGNATURE</th>
                <th>CONFIDENCE</th>
                <th>THREAT LEVEL</th>
                <th>AUDIT STATUS</th>
              </tr>
            </thead>
            <tbody>
              {anomalyTimeline.map((ev, i) => (
                <tr key={i}>
                  <td style={{ fontFamily: 'var(--font-mono)', color: '#00f0ff' }}>{ev.time}</td>
                  <td style={{ fontWeight: 600 }}>{ev.cam}</td>
                  <td><span style={{ marginRight: 6 }}>{ev.icon}</span>{ev.type}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{ev.score}</td>
                  <td>
                    <span
                      style={{
                        padding: '3px 8px',
                        borderRadius: 4,
                        fontSize: 10,
                        fontWeight: 700,
                        background: ev.level === 'CRITICAL' ? 'rgba(255,51,102,0.2)' : 'rgba(0,240,255,0.15)',
                        color: ev.level === 'CRITICAL' ? '#ff3366' : '#00f0ff',
                        border: `1px solid ${ev.level === 'CRITICAL' ? '#ff3366' : '#00f0ff'}`,
                      }}
                    >
                      {ev.level}
                    </span>
                  </td>
                  <td>
                    <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
                      <CheckCircle size={12} /> WAL LOGGED
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
