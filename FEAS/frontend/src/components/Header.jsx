import React from 'react';
import { Shield, LayoutGrid, Layers, Search, Video, Activity, Crosshair } from 'lucide-react';

export default function Header({ activeTab, setActiveTab, viewMode, setViewMode }) {
  return (
    <header className="app-header">
      <div className="header-top">
        <div className="brand-group">
          <div className="brand-logo-badge">
            <Shield size={22} color="#38bdf8" />
          </div>
          <div>
            <div className="brand-title">
              FEAS <span className="brand-badge">Forensic Suite</span>
            </div>
            <div className="brand-desc">
              AI Forensic Analysis &bull; Simple, Compact & Easy to Use
            </div>
          </div>
        </div>

        <div className="header-actions">
          <div className="status-indicator">
            <span className="dot green"></span>
            <span>AI Ready</span>
          </div>
          <button
            className={"mode-toggle-btn " + (viewMode === 'all' ? 'active' : '')}
            onClick={() => setViewMode(viewMode === 'tabs' ? 'all' : 'tabs')}
            title="Toggle between single tab or all 4 tools on one page"
          >
            {viewMode === 'all' ? (
              <>
                <Layers size={14} />
                <span>Single Tab Mode</span>
              </>
            ) : (
              <>
                <LayoutGrid size={14} />
                <span>Show All 4 on One Page</span>
              </>
            )}
          </button>
        </div>
      </div>

      <nav className="nav-bar">
        <button
          onClick={() => { setActiveTab('tampering'); if (viewMode === 'all') setViewMode('tabs'); }}
          className={"nav-item nav-tampering " + (activeTab === 'tampering' && viewMode === 'tabs' ? 'active' : '')}
        >
          <Search size={17} className="nav-icon-lucide" />
          <div className="nav-label-box">
            <span className="nav-title">Image Tampering</span>
            <span className="nav-caption">Photo edits & forgery</span>
          </div>
        </button>

        <button
          onClick={() => { setActiveTab('cctv'); if (viewMode === 'all') setViewMode('tabs'); }}
          className={"nav-item nav-cctv " + (activeTab === 'cctv' && viewMode === 'tabs' ? 'active' : '')}
        >
          <Video size={17} className="nav-icon-lucide" />
          <div className="nav-label-box">
            <span className="nav-title">CCTV Enhance</span>
            <span className="nav-caption">Sharpen blurry footage</span>
          </div>
        </button>

        <button
          onClick={() => { setActiveTab('wound'); if (viewMode === 'all') setViewMode('tabs'); }}
          className={"nav-item nav-wound " + (activeTab === 'wound' && viewMode === 'tabs' ? 'active' : '')}
        >
          <Activity size={17} className="nav-icon-lucide" />
          <div className="nav-label-box">
            <span className="nav-title">Wound Detection</span>
            <span className="nav-caption">Classify trauma & severity</span>
          </div>
        </button>

        <button
          onClick={() => { setActiveTab('bullet'); if (viewMode === 'all') setViewMode('tabs'); }}
          className={"nav-item nav-bullet " + (activeTab === 'bullet' && viewMode === 'tabs' ? 'active' : '')}
        >
          <Crosshair size={17} className="nav-icon-lucide" />
          <div className="nav-label-box">
            <span className="nav-title">Bullet Detection</span>
            <span className="nav-caption">Caliber & ballistics</span>
          </div>
        </button>
      </nav>
    </header>
  );
}
