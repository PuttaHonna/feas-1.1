import React, { useState } from 'react';
import PatternWaves from './PatternWaves';
import Sidebar from './components/Sidebar';
import LightfallDashboard from './components/LightfallDashboard';
import TamperingDetector from './components/TamperingDetector';
import CctvEnhancer from './components/CctvEnhancer';
import WoundDetector from './components/WoundDetector';
import BulletDetector from './components/BulletDetector';
import Forensic3DLab from './components/Forensic3DLab';
import FirebaseVault from './components/FirebaseVault';
import UserHistoryView from './components/UserHistoryView';
import ErrorBoundary from './components/ErrorBoundary';
import { Search, Video, Activity, Crosshair, Sparkles, Rotate3d, Cloud, History } from 'lucide-react';

export default function App() {
  const getInitialTab = () => {
    const p = new URLSearchParams(window.location.search).get('tab');
    return ['dashboard', 'history', 'tampering', 'cctv', 'wound', 'bullet', '3dlab', 'firebase'].includes(p) ? p : 'dashboard';
  };
  const getInitialView = () => {
    const v = new URLSearchParams(window.location.search).get('view');
    return v === 'all' ? 'all' : 'tabs';
  };

  const [activeTab, setActiveTab] = useState(getInitialTab);
  const [viewMode, setViewMode] = useState(getInitialView);

  return (
    <div className="feas-app-layout">
      {/* Full-screen Interactive Pattern Waves Background */}
      <div
        className="feas-background-waves"
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          zIndex: 0,
          pointerEvents: 'none',
          overflow: 'hidden'
        }}
      >
        <PatternWaves
          preset="lines"
          color="#1e293b"
          backgroundColor="#000000"
          fade="top"
          interactive
          cursorSize={50}
          cursorStrength={0.4}
          pattern="line"
          wave="ripple"
          spacing={5}
          markSize={0.42}
          depth={0.9}
          light={0}
          shine={0.6}
          contrast={1.2}
          speed={0.3}
          scale={1}
          direction={20}
          opacity={1}
          fadeSize={0.4}
          characters=".:-=+*#%@"
          intro={false}
          paused={false}
        />
      </div>

      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        viewMode={viewMode}
        setViewMode={setViewMode}
      />

      <div className="main-content-wrapper">
        <main className="app-main">
          {viewMode === 'all' && (
            <div className="quick-jump-bar">
              <span className="jump-title">Quick Jump:</span>
              <a href="#section-dashboard" className="jump-link">
                <Sparkles size={13} />
                <span>Lightfall Hub</span>
              </a>
              <a href="#section-history" className="jump-link">
                <History size={13} />
                <span>Examiner Ledger</span>
              </a>
              <a href="#section-tampering" className="jump-link">
                <Search size={13} />
                <span>Image Tampering</span>
              </a>
              <a href="#section-cctv" className="jump-link">
                <Video size={13} />
                <span>CCTV Enhance</span>
              </a>
              <a href="#section-wound" className="jump-link">
                <Activity size={13} />
                <span>Wound Detection</span>
              </a>
              <a href="#section-bullet" className="jump-link">
                <Crosshair size={13} />
                <span>Bullet Detection</span>
              </a>
              <a href="#section-3dlab" className="jump-link">
                <Rotate3d size={13} />
                <span>3D Lab</span>
              </a>
              <a href="#section-firebase" className="jump-link">
                <Cloud size={13} />
                <span>Cloud Vault</span>
              </a>
            </div>
          )}

          <div className={viewMode === 'tabs' ? 'tab-content' : 'all-modules-view'}>
            <section
              id="section-dashboard"
              className={viewMode === 'all' ? 'module-section' : ''}
              style={{
                display: viewMode === 'all' || activeTab === 'dashboard' ? 'block' : 'none',
                width: '100%',
                marginBottom: viewMode === 'all' ? '2rem' : undefined,
              }}
            >
              <LightfallDashboard
                onSelectModule={(tab) => {
                  if (viewMode === 'all') {
                    const el = document.getElementById(`section-${tab}`);
                    if (el) {
                      el.scrollIntoView({ behavior: 'smooth' });
                    } else {
                      setActiveTab(tab);
                      setViewMode('tabs');
                    }
                  } else {
                    setActiveTab(tab);
                  }
                }}
                onViewModeChange={setViewMode}
              />
            </section>

            <section
              id="section-history"
              className={viewMode === 'all' ? 'module-section' : ''}
              style={{
                display: viewMode === 'all' || activeTab === 'history' ? 'block' : 'none',
                width: '100%',
                marginBottom: viewMode === 'all' ? '2rem' : undefined,
              }}
            >
              <ErrorBoundary title="Examiner Account & Analysis Ledger">
                <UserHistoryView />
              </ErrorBoundary>
            </section>

            <section
              id="section-tampering"
              className={viewMode === 'all' ? 'module-section' : ''}
              style={{
                display: viewMode === 'all' || activeTab === 'tampering' ? 'block' : 'none',
                width: '100%',
              }}
            >
              <TamperingDetector />
            </section>

            <section
              id="section-cctv"
              className={viewMode === 'all' ? 'module-section' : ''}
              style={{
                display: viewMode === 'all' || activeTab === 'cctv' ? 'block' : 'none',
                width: '100%',
              }}
            >
              <ErrorBoundary title="CCTV Intelligence & Neural Enhancement">
                <CctvEnhancer />
              </ErrorBoundary>
            </section>

            <section
              id="section-wound"
              className={viewMode === 'all' ? 'module-section' : ''}
              style={{
                display: viewMode === 'all' || activeTab === 'wound' ? 'block' : 'none',
                width: '100%',
              }}
            >
              <WoundDetector />
            </section>

            <section
              id="section-bullet"
              className={viewMode === 'all' ? 'module-section' : ''}
              style={{
                display: viewMode === 'all' || activeTab === 'bullet' ? 'block' : 'none',
                width: '100%',
              }}
            >
              <BulletDetector />
            </section>

            <section
              id="section-3dlab"
              className={viewMode === 'all' ? 'module-section' : ''}
              style={{
                display: viewMode === 'all' || activeTab === '3dlab' ? 'block' : 'none',
                width: '100%',
              }}
            >
              <Forensic3DLab />
            </section>

            <section
              id="section-firebase"
              className={viewMode === 'all' ? 'module-section' : ''}
              style={{
                display: viewMode === 'all' || activeTab === 'firebase' ? 'block' : 'none',
                width: '100%',
              }}
            >
              <ErrorBoundary title="Firebase Cloud Forensic Vault">
                <FirebaseVault />
              </ErrorBoundary>
            </section>
          </div>
        </main>

        <footer className="app-footer">
          <div>
            <strong>FEAS Forensic Suite</strong> &mdash; Court-Admissible AI Computer Vision Pipeline
          </div>
          <div className="footer-links">
            <span>Lightfall Telemetry</span> &bull;
            <span>Examiner Ledger</span> &bull;
            <span>Image Tampering</span> &bull;
            <span>CCTV Super-Resolution</span> &bull;
            <span>Wound Pathology</span> &bull;
            <span>Ballistics 3D</span> &bull;
            <span>Firebase Cloud Vault</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
