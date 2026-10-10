import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import LightfallDashboard from './components/LightfallDashboard';
import TamperingDetector from './components/TamperingDetector';
import CctvEnhancer from './components/CctvEnhancer';
import WoundDetector from './components/WoundDetector';
import BulletDetector from './components/BulletDetector';
import Forensic3DLab from './components/Forensic3DLab';
import { Search, Video, Activity, Crosshair, Sparkles, Rotate3d } from 'lucide-react';

export default function App() {
  const getInitialTab = () => {
    const p = new URLSearchParams(window.location.search).get('tab');
    return ['dashboard', 'tampering', 'cctv', 'wound', 'bullet', '3dlab'].includes(p) ? p : 'dashboard';
  };
  const getInitialView = () => {
    const v = new URLSearchParams(window.location.search).get('view');
    return v === 'all' ? 'all' : 'tabs';
  };

  const [activeTab, setActiveTab] = useState(getInitialTab);
  const [viewMode, setViewMode] = useState(getInitialView);

  return (
    <div className="feas-app-layout">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        viewMode={viewMode}
        setViewMode={setViewMode}
      />

      <div className="main-content-wrapper">
        <main className="app-main">
          {viewMode === 'tabs' ? (
            <div className="tab-content">
              {activeTab === 'dashboard' && (
                <LightfallDashboard
                  onSelectModule={(tab) => {
                    setActiveTab(tab);
                  }}
                  onViewModeChange={setViewMode}
                />
              )}
              {activeTab === 'tampering' && <TamperingDetector />}
              {activeTab === 'cctv' && <CctvEnhancer />}
              {activeTab === 'wound' && <WoundDetector />}
              {activeTab === 'bullet' && <BulletDetector />}
              {activeTab === '3dlab' && <Forensic3DLab />}
            </div>
          ) : (
            <div className="all-modules-view">
              <div className="quick-jump-bar">
                <span className="jump-title">Quick Jump:</span>
                <a href="#section-hero" className="jump-link">
                  <Sparkles size={13} />
                  <span>Lightfall Hub</span>
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
              </div>

              <section id="section-hero" className="module-section" style={{ marginBottom: '2rem' }}>
                <LightfallDashboard
                  onSelectModule={(tab) => {
                    const el = document.getElementById(`section-${tab}`);
                    if (el) {
                      el.scrollIntoView({ behavior: 'smooth' });
                    } else {
                      setActiveTab(tab);
                      setViewMode('tabs');
                    }
                  }}
                  onViewModeChange={setViewMode}
                />
              </section>

              <section id="section-tampering" className="module-section">
                <TamperingDetector />
              </section>

              <section id="section-cctv" className="module-section">
                <CctvEnhancer />
              </section>

              <section id="section-wound" className="module-section">
                <WoundDetector />
              </section>

              <section id="section-bullet" className="module-section">
                <BulletDetector />
              </section>

              <section id="section-3dlab" className="module-section">
                <Forensic3DLab />
              </section>
            </div>
          )}
        </main>

        <footer className="app-footer">
          <div>
            <strong>FEAS Forensic Suite</strong> &mdash; Court-Admissible AI Computer Vision Pipeline
          </div>
          <div className="footer-links">
            <span>Lightfall Telemetry</span> &bull;
            <span>Image Tampering</span> &bull;
            <span>CCTV Super-Resolution</span> &bull;
            <span>Wound Pathology</span> &bull;
            <span>Ballistics 3D</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
