import React, { useState, useEffect } from 'react';
import {
  Shield,
  Search,
  Video,
  Activity,
  Crosshair,
  LayoutGrid,
  Layers,
  Sparkles,
  Rotate3d,
  CheckCircle2,
  Cloud,
  History,
  UserCheck
} from 'lucide-react';
import { firebaseService } from '../services/firebase';

export default function Sidebar({ activeTab, setActiveTab, viewMode, setViewMode }) {
  const [examiner, setExaminer] = useState(firebaseService.getActiveExaminer());

  useEffect(() => {
    const handler = (e) => {
      if (e.detail) setExaminer(e.detail);
    };
    window.addEventListener('feas-examiner-changed', handler);
    return () => window.removeEventListener('feas-examiner-changed', handler);
  }, []);

  return (
    <aside className="app-sidebar">
      {/* Brand Profile */}
      <div className="sidebar-brand">
        <div className="brand-logo-badge">
          <Shield size={22} color="#38bdf8" />
        </div>
        <div className="brand-info">
          <div className="brand-title">
            FEAS <span className="brand-badge">PRO</span>
          </div>
          <div className="brand-desc">Forensic Suite v2.4</div>
        </div>
      </div>

      {/* AI Status */}
      <div className="sidebar-status">
        <span className="dot green"></span>
        <span className="status-text">AI Engines Active</span>
      </div>

      {/* Cloud Vault Status */}
      <div className="sidebar-status" style={{ marginTop: '0.35rem', background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.2)' }}>
        <span className="dot" style={{ background: '#38bdf8', boxShadow: '0 0 8px #38bdf8' }}></span>
        <span className="status-text" style={{ color: '#38bdf8', fontWeight: '600' }}>Cloud Vault: Live Spark</span>
      </div>

      {/* Navigation Sections */}
      <div className="sidebar-nav-section">
        <span className="nav-section-title">COMMAND CENTER</span>
        <nav className="sidebar-nav">
          <button
            onClick={() => { setActiveTab('dashboard'); if (viewMode === 'all') setViewMode('tabs'); }}
            className={"sidebar-item nav-dashboard " + (activeTab === 'dashboard' && viewMode === 'tabs' ? 'active' : '')}
          >
            <div className="nav-icon-wrapper purple">
              <Sparkles size={16} />
            </div>
            <div className="sidebar-label">
              <span className="item-title">Lightfall Dashboard</span>
              <span className="item-sub">Telemetry & Overview</span>
            </div>
          </button>

          <button
            onClick={() => { setActiveTab('history'); if (viewMode === 'all') setViewMode('tabs'); }}
            className={"sidebar-item nav-history " + (activeTab === 'history' && viewMode === 'tabs' ? 'active' : '')}
          >
            <div className="nav-icon-wrapper cyan" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', borderColor: 'rgba(56, 189, 248, 0.3)' }}>
              <History size={16} />
            </div>
            <div className="sidebar-label">
              <span className="item-title">Examiner Ledger</span>
              <span className="item-sub">User ID & History</span>
            </div>
          </button>
        </nav>
      </div>

      <div className="sidebar-nav-section">
        <span className="nav-section-title">CORE MODULES</span>
        <nav className="sidebar-nav">
          <button
            onClick={() => { setActiveTab('tampering'); if (viewMode === 'all') setViewMode('tabs'); }}
            className={"sidebar-item nav-tampering " + (activeTab === 'tampering' && viewMode === 'tabs' ? 'active' : '')}
          >
            <div className="nav-icon-wrapper amber">
              <Search size={16} />
            </div>
            <div className="sidebar-label">
              <span className="item-title">Image Tampering</span>
              <span className="item-sub">Forgery & ELA analysis</span>
            </div>
          </button>

          <button
            onClick={() => { setActiveTab('cctv'); if (viewMode === 'all') setViewMode('tabs'); }}
            className={"sidebar-item nav-cctv " + (activeTab === 'cctv' && viewMode === 'tabs' ? 'active' : '')}
          >
            <div className="nav-icon-wrapper blue">
              <Video size={16} />
            </div>
            <div className="sidebar-label">
              <span className="item-title">CCTV Enhance</span>
              <span className="item-sub">Super-resolution & denoise</span>
            </div>
          </button>

          <button
            onClick={() => { setActiveTab('wound'); if (viewMode === 'all') setViewMode('tabs'); }}
            className={"sidebar-item nav-wound " + (activeTab === 'wound' && viewMode === 'tabs' ? 'active' : '')}
          >
            <div className="nav-icon-wrapper red">
              <Activity size={16} />
            </div>
            <div className="sidebar-label">
              <span className="item-title">Wound Detection</span>
              <span className="item-sub">Trauma classification</span>
            </div>
          </button>

          <button
            onClick={() => { setActiveTab('bullet'); if (viewMode === 'all') setViewMode('tabs'); }}
            className={"sidebar-item nav-bullet " + (activeTab === 'bullet' && viewMode === 'tabs' ? 'active' : '')}
          >
            <div className="nav-icon-wrapper emerald">
              <Crosshair size={16} />
            </div>
            <div className="sidebar-label">
              <span className="item-title">Bullet Detection</span>
              <span className="item-sub">Caliber & striations</span>
            </div>
          </button>

          <button
            onClick={() => { setActiveTab('3dlab'); if (viewMode === 'all') setViewMode('tabs'); }}
            className={"sidebar-item nav-3d " + (activeTab === '3dlab' && viewMode === 'tabs' ? 'active' : '')}
          >
            <div className="nav-icon-wrapper blue" style={{ background: 'rgba(129, 140, 248, 0.15)', color: '#818cf8', borderColor: 'rgba(129, 140, 248, 0.3)' }}>
              <Rotate3d size={16} />
            </div>
            <div className="sidebar-label">
              <span className="item-title">Forensic 3D Lab</span>
              <span className="item-sub">Biometric mesh & FFT</span>
            </div>
          </button>

          <button
            onClick={() => { setActiveTab('firebase'); if (viewMode === 'all') setViewMode('tabs'); }}
            className={"sidebar-item nav-firebase " + (activeTab === 'firebase' && viewMode === 'tabs' ? 'active' : '')}
          >
            <div className="nav-icon-wrapper cyan" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', borderColor: 'rgba(56, 189, 248, 0.3)' }}>
              <Cloud size={16} />
            </div>
            <div className="sidebar-label">
              <span className="item-title">Firebase Cloud Vault</span>
              <span className="item-sub">Auth & Evidence Store</span>
            </div>
          </button>
        </nav>
      </div>

      {/* View Mode Toggle Button */}
      <div className="sidebar-nav-section mt-auto">
        <span className="nav-section-title">VIEW OPTIONS</span>
        <button
          className={"sidebar-toggle-btn " + (viewMode === 'all' ? 'active' : '')}
          onClick={() => setViewMode(viewMode === 'tabs' ? 'all' : 'tabs')}
        >
          {viewMode === 'all' ? (
            <>
              <Layers size={15} />
              <span>Switch to Tabs Mode</span>
            </>
          ) : (
            <>
              <LayoutGrid size={15} />
              <span>Show All Modules View</span>
            </>
          )}
        </button>
      </div>

      {/* Active Examiner Mini Profile Badge */}
      <div
        className="sidebar-examiner-card"
        onClick={() => { setActiveTab('history'); if (viewMode === 'all') setViewMode('tabs'); }}
        title="View Personal Analysis Ledger"
        style={{
          margin: '0.75rem 0.25rem',
          padding: '0.65rem 0.75rem',
          borderRadius: '10px',
          background: 'rgba(16, 23, 38, 0.95)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.65rem',
          cursor: 'pointer',
          transition: 'all 0.2s',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
        }}
      >
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: examiner?.avatarBg || '#0284c7',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 'bold',
            fontSize: '0.9rem',
            color: '#fff',
            flexShrink: 0
          }}
        >
          {examiner?.displayName ? examiner.displayName.charAt(0) : 'E'}
        </div>
        <div style={{ overflow: 'hidden', flex: 1 }}>
          <div style={{ fontSize: '0.78rem', fontWeight: '600', color: '#fff', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
            {examiner?.displayName || 'Examiner'}
          </div>
          <div style={{ fontSize: '0.68rem', color: '#38bdf8', fontFamily: 'monospace' }}>
            {examiner?.badgeNumber || 'FEAS-8842'}
          </div>
        </div>
      </div>

      {/* Footer info */}
      <div className="sidebar-footer">
        <div className="version-tag">FEAS v2.4 &bull; Lightfall Enabled</div>
      </div>
    </aside>
  );
}
