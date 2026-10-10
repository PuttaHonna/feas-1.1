import React, { useState } from 'react';
import { Users, UserCheck, Search, Shield, Fingerprint, Calendar } from 'lucide-react';

export default function SuspectRegistryView() {
  const [searchQuery, setSearchQuery] = useState('');

  const suspects = [
    {
      id: 'SUSP-001',
      name: 'Marcus Vance',
      alias: 'ZeroDay',
      status: 'WARRANT ACTIVE',
      statusColor: '#ff3366',
      threat: 'CRITICAL',
      registeredDate: '2025-11-14',
      fingerprintVector: '512-D L2 LATTICE #4A2F',
      notes: 'Prior convictions in digital wire fraud, synthetic CCTV identity injection, and generative voice spoofing.',
    },
    {
      id: 'SUSP-002',
      name: 'Dmitri Sokolov',
      alias: 'Vector',
      status: 'MONITORED',
      statusColor: '#f59e0b',
      threat: 'ELEVATED',
      registeredDate: '2026-02-01',
      fingerprintVector: '512-D L2 LATTICE #8B11',
      notes: 'Hardware surveillance tampering specialist; suspected involvement in perimeter security breaches.',
    },
    {
      id: 'SUSP-003',
      name: 'Elena Rostova',
      alias: 'Ghostwriter',
      status: 'INVESTIGATION',
      statusColor: '#00f0ff',
      threat: 'MODERATE',
      registeredDate: '2026-05-19',
      fingerprintVector: '512-D L2 LATTICE #1E99',
      notes: 'Expert in deepfake latent diffusion and facial morphing attacks on access control nodes.',
    },
  ];

  const filtered = suspects.filter(s =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.alias.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Search Header */}
      <div className="hud-card">
        <div className="hud-card-accent-top" />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 14 }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Users size={18} color="#00f0ff" />
              <span>Biometric Suspect Registry & FaceNet 512-D Database</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Active facial vector gallery indexed in SQLite WAL for real-time cosine distance matching
            </div>
          </div>

          <div style={{ position: 'relative', width: 260 }}>
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: 12 }} />
            <input
              type="text"
              placeholder="Search suspect dossiers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(10, 16, 30, 0.9)',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                borderRadius: 8,
                padding: '9px 14px 9px 36px',
                color: '#fff',
                fontSize: 13,
                fontFamily: 'var(--font-sans)',
              }}
            />
          </div>
        </div>
      </div>

      {/* Suspect Dossier Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 18 }}>
        {filtered.map((s) => (
          <div key={s.id} className="hud-card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 17, fontWeight: 800, color: '#fff' }}>
                  {s.name} <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>("{s.alias}")</span>
                </div>
                <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', marginTop: 2 }}>
                  IDENTIFIER: <b style={{ color: '#38bdf8' }}>{s.id}</b>
                </div>
              </div>

              <span
                style={{
                  padding: '4px 10px',
                  borderRadius: 9999,
                  fontSize: 10,
                  fontWeight: 800,
                  fontFamily: 'var(--font-mono)',
                  background: `${s.statusColor}22`,
                  color: s.statusColor,
                  border: `1px solid ${s.statusColor}`,
                }}
              >
                {s.status}
              </span>
            </div>

            <div style={{ background: '#090e17', borderRadius: 8, padding: 12, marginBottom: 14, border: '1px solid rgba(56,189,248,0.1)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Fingerprint size={13} color="#00f0ff" /> {s.fingerprintVector}
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Calendar size={13} /> {s.registeredDate}
                </span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-main)', lineHeight: 1.4 }}>
                {s.notes}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
              <span style={{ color: 'var(--text-muted)' }}>THREAT EVALUATION: <b style={{ color: s.statusColor }}>{s.threat}</b></span>
              <button className="btn-outline" style={{ padding: '4px 10px', fontSize: 11 }}>
                Compare Vector
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
