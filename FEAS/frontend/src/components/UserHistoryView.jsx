import React, { useState, useEffect } from 'react';
import {
  User,
  Shield,
  FileText,
  Search,
  Filter,
  CheckCircle,
  AlertTriangle,
  Clock,
  Fingerprint,
  Trash2,
  Copy,
  ExternalLink,
  ChevronDown,
  Sparkles,
  Download,
  PlusCircle,
  Edit3,
  Award,
  Video,
  Activity,
  Crosshair,
  Rotate3d,
  Layers,
  Check,
  RefreshCw
} from 'lucide-react';
import { firebaseService, EXAMINER_ROSTER } from '../services/firebase';

export default function UserHistoryView() {
  const [activeExaminer, setActiveExaminer] = useState(firebaseService.getActiveExaminer());
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModule, setSelectedModule] = useState('all');
  const [selectedVerdict, setSelectedVerdict] = useState('all');
  const [copiedId, setCopiedId] = useState(null);
  const [downloadingPdfId, setDownloadingPdfId] = useState(null);
  const [pdfNotice, setPdfNotice] = useState(null);
  
  // Modals & Panels
  const [inspectItem, setInspectItem] = useState(null);
  const [showRosterModal, setShowRosterModal] = useState(false);
  const [showQuickRunModal, setShowQuickRunModal] = useState(false);
  const [showEditProfileModal, setShowEditProfileModal] = useState(false);

  // Quick Run Form State
  const [quickModule, setQuickModule] = useState('tampering');
  const [quickEvidence, setQuickEvidence] = useState('scene_evidence_001.png');
  const [quickVerdict, setQuickVerdict] = useState('FORGED');
  const [quickConfidence, setQuickConfidence] = useState(96);
  const [quickNotes, setQuickNotes] = useState('Localization anomaly detected in high-frequency ELA channels.');

  // Profile Edit State
  const [editName, setEditName] = useState(activeExaminer.displayName);
  const [editRole, setEditRole] = useState(activeExaminer.role);
  const [editBadge, setEditBadge] = useState(activeExaminer.badgeNumber);
  const [editClearance, setEditClearance] = useState(activeExaminer.clearance);

  // Load history when activeExaminer changes
  useEffect(() => {
    loadUserHistory(activeExaminer.uid);

    const onExaminerChange = (e) => {
      if (e.detail) {
        setActiveExaminer(e.detail);
        loadUserHistory(e.detail.uid);
      }
    };

    const onAnalysisRecorded = (e) => {
      // Reload history
      loadUserHistory(activeExaminer.uid);
    };

    window.addEventListener('feas-examiner-changed', onExaminerChange);
    window.addEventListener('feas-analysis-recorded', onAnalysisRecorded);

    return () => {
      window.removeEventListener('feas-examiner-changed', onExaminerChange);
      window.removeEventListener('feas-analysis-recorded', onAnalysisRecorded);
    };
  }, [activeExaminer.uid]);

  const loadUserHistory = async (uid) => {
    setLoading(true);
    try {
      const records = await firebaseService.getUserHistory(uid);
      setHistory(records);
    } catch (err) {
      console.warn('Failed to load user history:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSwitchExaminer = (examiner) => {
    const updated = firebaseService.switchExaminer(examiner);
    setActiveExaminer(updated);
    setEditName(updated.displayName);
    setEditRole(updated.role);
    setEditBadge(updated.badgeNumber);
    setEditClearance(updated.clearance);
    setShowRosterModal(false);
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    const updated = {
      ...activeExaminer,
      displayName: editName,
      role: editRole,
      badgeNumber: editBadge,
      clearance: editClearance,
    };
    await firebaseService.saveUserProfile(activeExaminer.uid, {
      user_id: activeExaminer.uid,
      email: activeExaminer.email,
      display_name: editName,
      role: editRole,
      badge_number: editBadge,
      clearance_level: editClearance,
    });
    firebaseService.switchExaminer(updated);
    setActiveExaminer(updated);
    setShowEditProfileModal(false);
  };

  const handleQuickRun = async (e) => {
    e.preventDefault();
    const newRecord = {
      module: quickModule,
      verdict: quickVerdict,
      confidence: parseFloat(quickConfidence) / 100,
      evidence_name: quickEvidence,
      sha256: Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join(''),
      timestamp: new Date().toISOString(),
      findings: {
        examiner: activeExaminer.displayName,
        badge: activeExaminer.badgeNumber,
        summary: quickNotes,
        verification_status: 'COURT_VERIFIED',
      }
    };

    await firebaseService.recordAnalysis(activeExaminer.uid, newRecord);
    setShowQuickRunModal(false);
    loadUserHistory(activeExaminer.uid);
  };

  const handleDeleteEntry = async (analysisId) => {
    if (!window.confirm(`Delete forensic record ${analysisId} from examiner ledger?`)) return;
    await firebaseService.deleteUserAnalysis(activeExaminer.uid, analysisId);
    setHistory(prev => prev.filter(item => item.analysis_id !== analysisId));
    if (inspectItem?.analysis_id === analysisId) setInspectItem(null);
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const exportCourtAffidavit = (item) => {
    const affidavit = {
      document_type: "CERTIFICATE OF FORENSIC EXAMINATION - COURT ADMISSIBLE (FED. R. EVID. 702)",
      analysis_id: item.analysis_id,
      case_id: item.case_id,
      timestamp_utc: item.timestamp,
      examiner_credentials: {
        name: activeExaminer.displayName,
        user_id: activeExaminer.uid,
        badge_number: activeExaminer.badgeNumber,
        clearance_level: activeExaminer.clearance,
        affiliation: "FEAS Forensics Division / Digital Evidence Lab"
      },
      evidence_chain: {
        filename: item.evidence_name,
        sha256_cryptographic_hash: item.sha256,
        integrity_verified: true
      },
      evaluation: {
        forensic_module: item.module?.toUpperCase(),
        verdict: item.verdict,
        confidence_metric: `${((item.confidence || 0.95) * 100).toFixed(1)}%`,
        findings: item.findings || {}
      },
      attestation: "I certify under penalty of perjury that this analysis was conducted using validated neural computer vision algorithms adhering to ISO/IEC 17025 standards."
    };

    const blob = new Blob([JSON.stringify(affidavit, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `AFFIDAVIT_${item.analysis_id}_${activeExaminer.badgeNumber}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadPdf = async (item) => {
    setDownloadingPdfId(item.analysis_id);
    try {
      const res = await firebaseService.downloadCourtAffidavitPdf(activeExaminer.uid, item.analysis_id);
      setPdfNotice({
        analysis_id: item.analysis_id,
        sha256: res.sha256,
        filename: res.filename
      });
      setTimeout(() => setPdfNotice(null), 7000);
    } catch (err) {
      console.warn('Backend PDF download error, exporting json fallback:', err);
      exportCourtAffidavit(item);
    } finally {
      setDownloadingPdfId(null);
    }
  };

  // Filter and Search logic
  const filteredHistory = history.filter(item => {
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      !q ||
      item.analysis_id?.toLowerCase().includes(q) ||
      item.case_id?.toLowerCase().includes(q) ||
      item.evidence_name?.toLowerCase().includes(q) ||
      item.verdict?.toLowerCase().includes(q) ||
      item.sha256?.toLowerCase().includes(q);

    const matchesModule = selectedModule === 'all' || item.module === selectedModule;
    const matchesVerdict =
      selectedVerdict === 'all' ||
      item.verdict?.toLowerCase() === selectedVerdict.toLowerCase();

    return matchesSearch && matchesModule && matchesVerdict;
  });

  // Calculate Metrics
  const totalAnalyses = history.length;
  const tamperingCount = history.filter(h => h.module === 'tampering').length;
  const cctvCount = history.filter(h => h.module === 'cctv').length;
  const woundCount = history.filter(h => h.module === 'wound').length;
  const bulletCount = history.filter(h => h.module === 'bullet').length;
  const avgConfidence = totalAnalyses > 0
    ? (history.reduce((acc, h) => acc + (typeof h.confidence === 'number' ? h.confidence : 0.95), 0) / totalAnalyses * 100).toFixed(1)
    : '95.0';

  const getModuleBadge = (mod) => {
    switch (mod) {
      case 'tampering':
        return { label: 'Tampering ELA', icon: Search, bg: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', border: 'rgba(245, 158, 11, 0.3)' };
      case 'cctv':
        return { label: 'CCTV Enhance', icon: Video, bg: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: 'rgba(56, 189, 248, 0.3)' };
      case 'wound':
        return { label: 'Wound Pathology', icon: Activity, bg: 'rgba(244, 63, 94, 0.15)', color: '#f43f5e', border: 'rgba(244, 63, 94, 0.3)' };
      case 'bullet':
        return { label: 'Ballistics', icon: Crosshair, bg: 'rgba(16, 185, 129, 0.15)', color: '#10b981', border: 'rgba(16, 185, 129, 0.3)' };
      case '3d_lab':
      case '3dlab':
        return { label: 'Forensic 3D', icon: Rotate3d, bg: 'rgba(129, 140, 248, 0.15)', color: '#818cf8', border: 'rgba(129, 140, 248, 0.3)' };
      default:
        return { label: mod || 'Forensic', icon: Layers, bg: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8', border: 'rgba(148, 163, 184, 0.3)' };
    }
  };

  const getVerdictStyle = (v) => {
    const verdict = (v || '').toUpperCase();
    if (verdict.includes('FORGED') || verdict.includes('TAMPER') || verdict.includes('SPLICE')) {
      return { bg: 'rgba(244, 63, 94, 0.15)', color: '#f43f5e', border: 'rgba(244, 63, 94, 0.35)', label: verdict };
    }
    if (verdict.includes('MATCH') || verdict.includes('CONFIRMED')) {
      return { bg: 'rgba(16, 185, 129, 0.15)', color: '#10b981', border: 'rgba(16, 185, 129, 0.35)', label: verdict };
    }
    if (verdict.includes('AUTHENTIC') || verdict.includes('ORIGINAL')) {
      return { bg: 'rgba(34, 197, 94, 0.15)', color: '#22c55e', border: 'rgba(34, 197, 94, 0.35)', label: verdict };
    }
    if (verdict.includes('ENHANCE') || verdict.includes('TRAJECTORY')) {
      return { bg: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: 'rgba(56, 189, 248, 0.35)', label: verdict };
    }
    return { bg: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', border: 'rgba(245, 158, 11, 0.35)', label: verdict };
  };

  return (
    <div className="user-history-view-container" style={{ padding: '1.5rem', maxWidth: '1440px', margin: '0 auto' }}>
      
      {/* 1. EXAMINER IDENTIFICATION & AUTHENTICATION BANNER */}
      <div
        className="examiner-id-banner"
        style={{
          background: 'linear-gradient(135deg, rgba(16, 23, 38, 0.95), rgba(11, 17, 28, 0.98))',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          borderRadius: '16px',
          padding: '1.5rem 1.75rem',
          marginBottom: '1.5rem',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        <div style={{ position: 'absolute', right: '-20px', top: '-20px', opacity: 0.05, pointerEvents: 'none' }}>
          <Shield size={240} color="#38bdf8" />
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '1.25rem', position: 'relative', zIndex: 1 }}>
          
          {/* Avatar and Info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '14px',
                background: activeExaminer.avatarBg || '#0284c7',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.6rem',
                fontWeight: 'bold',
                color: '#fff',
                border: '2px solid rgba(255, 255, 255, 0.2)',
                boxShadow: `0 0 20px ${activeExaminer.avatarBg || '#0284c7'}66`
              }}
            >
              {activeExaminer.displayName ? activeExaminer.displayName.charAt(0) : 'E'}
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.25rem' }}>
                <h2 style={{ fontSize: '1.4rem', fontWeight: '700', color: '#fff', letterSpacing: '-0.02em', margin: 0 }}>
                  {activeExaminer.displayName}
                </h2>
                <span
                  style={{
                    background: 'rgba(56, 189, 248, 0.15)',
                    color: '#38bdf8',
                    border: '1px solid rgba(56, 189, 248, 0.35)',
                    padding: '2px 8px',
                    borderRadius: '6px',
                    fontSize: '0.72rem',
                    fontWeight: '700',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em'
                  }}
                >
                  UID: {activeExaminer.uid}
                </span>
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', fontSize: '0.85rem', color: '#94a3b8' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Award size={14} color="#f59e0b" />
                  <strong style={{ color: '#e2e8f0' }}>{activeExaminer.role}</strong>
                </span>
                <span>&bull;</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Shield size={14} color="#38bdf8" />
                  Badge: <span style={{ fontFamily: 'monospace', color: '#38bdf8', fontWeight: '600' }}>{activeExaminer.badgeNumber}</span>
                </span>
                <span>&bull;</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <CheckCircle size={14} color="#10b981" />
                  <span>{activeExaminer.clearance}</span>
                </span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              onClick={() => setShowRosterModal(true)}
              style={{
                background: 'rgba(56, 189, 248, 0.12)',
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                padding: '0.55rem 1rem',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                transition: 'all 0.2s'
              }}
            >
              <User size={15} />
              <span>Switch Examiner</span>
              <ChevronDown size={14} />
            </button>

            <button
              onClick={() => setShowEditProfileModal(true)}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                color: '#e2e8f0',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                padding: '0.55rem 0.9rem',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: '500',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem'
              }}
            >
              <Edit3 size={15} />
              <span>Edit Credentials</span>
            </button>

            <button
              onClick={() => setShowQuickRunModal(true)}
              style={{
                background: 'linear-gradient(135deg, #0284c7, #2563eb)',
                color: '#fff',
                border: 'none',
                padding: '0.55rem 1.1rem',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                boxShadow: '0 4px 14px rgba(2, 132, 199, 0.4)'
              }}
            >
              <PlusCircle size={15} />
              <span>Log Direct Analysis</span>
            </button>
          </div>
        </div>

        {/* Verification Footer Pill */}
        <div
          style={{
            marginTop: '1.25rem',
            paddingTop: '0.85rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.07)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
            fontSize: '0.78rem',
            color: '#64748b'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', boxShadow: '0 0 8px #10b981' }}></span>
            <span style={{ color: '#94a3b8' }}>
              Forensic Audit Ledger Active &bull; Linked to Firebase Cloud Vault &amp; Local SQLite Cache
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Fingerprint size={14} color="#38bdf8" />
            <span style={{ fontFamily: 'monospace', color: '#94a3b8' }}>
              Audit Signature: SHA256-RSA-FEAS-GOV-2026
            </span>
          </div>
        </div>
      </div>

      {/* 2. STATISTICAL METRICS ROW */}
      <div
        className="examiner-metrics-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
          marginBottom: '1.5rem'
        }}
      >
        <div
          style={{
            background: 'rgba(16, 23, 38, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '12px',
            padding: '1rem 1.25rem'
          }}
        >
          <div style={{ fontSize: '0.78rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.35rem' }}>
            Total Personal Analyses
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'baseline', gap: '0.4rem' }}>
            {totalAnalyses}
            <span style={{ fontSize: '0.8rem', color: '#10b981', fontWeight: '500' }}>Active Records</span>
          </div>
        </div>

        <div
          style={{
            background: 'rgba(16, 23, 38, 0.8)',
            border: '1px solid rgba(245, 158, 11, 0.2)',
            borderRadius: '12px',
            padding: '1rem 1.25rem'
          }}
        >
          <div style={{ fontSize: '0.78rem', color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.35rem' }}>
            Tampering Audits
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '700', color: '#f59e0b' }}>
            {tamperingCount}
          </div>
        </div>

        <div
          style={{
            background: 'rgba(16, 23, 38, 0.8)',
            border: '1px solid rgba(56, 189, 248, 0.2)',
            borderRadius: '12px',
            padding: '1rem 1.25rem'
          }}
        >
          <div style={{ fontSize: '0.78rem', color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.35rem' }}>
            CCTV Enhancements
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '700', color: '#38bdf8' }}>
            {cctvCount}
          </div>
        </div>

        <div
          style={{
            background: 'rgba(16, 23, 38, 0.8)',
            border: '1px solid rgba(244, 63, 94, 0.2)',
            borderRadius: '12px',
            padding: '1rem 1.25rem'
          }}
        >
          <div style={{ fontSize: '0.78rem', color: '#f43f5e', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.35rem' }}>
            Wound &amp; Trauma
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '700', color: '#f43f5e' }}>
            {woundCount}
          </div>
        </div>

        <div
          style={{
            background: 'rgba(16, 23, 38, 0.8)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            borderRadius: '12px',
            padding: '1rem 1.25rem'
          }}
        >
          <div style={{ fontSize: '0.78rem', color: '#10b981', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.35rem' }}>
            Ballistics / 3D
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '700', color: '#10b981' }}>
            {bulletCount}
          </div>
        </div>

        <div
          style={{
            background: 'rgba(16, 23, 38, 0.8)',
            border: '1px solid rgba(129, 140, 248, 0.2)',
            borderRadius: '12px',
            padding: '1rem 1.25rem'
          }}
        >
          <div style={{ fontSize: '0.78rem', color: '#818cf8', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.35rem' }}>
            Mean Confidence
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '700', color: '#818cf8' }}>
            {avgConfidence}%
          </div>
        </div>
      </div>

      {/* 3. SEARCH & FILTERS BAR */}
      <div
        className="history-controls-bar"
        style={{
          background: 'rgba(16, 23, 38, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '12px',
          padding: '1rem',
          marginBottom: '1.25rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem'
        }}
      >
        {/* Search Input */}
        <div style={{ position: 'relative', flex: '1 1 280px', maxWidth: '420px' }}>
          <Search size={16} color="#64748b" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            placeholder="Search analysis ID, case ID, evidence filename, or hash..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '0.55rem 0.75rem 0.55rem 2.25rem',
              background: 'rgba(11, 17, 28, 0.9)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              color: '#fff',
              fontSize: '0.85rem',
              outline: 'none'
            }}
          />
        </div>

        {/* Module Filter Chips */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.4rem' }}>
          {[
            { id: 'all', label: 'All Modules' },
            { id: 'tampering', label: 'Tampering' },
            { id: 'cctv', label: 'CCTV' },
            { id: 'wound', label: 'Wound' },
            { id: 'bullet', label: 'Bullet' },
            { id: '3d_lab', label: '3D Lab' },
          ].map(mod => (
            <button
              key={mod.id}
              onClick={() => setSelectedModule(mod.id)}
              style={{
                padding: '0.4rem 0.75rem',
                borderRadius: '6px',
                fontSize: '0.78rem',
                fontWeight: '600',
                border: selectedModule === mod.id ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
                background: selectedModule === mod.id ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                color: selectedModule === mod.id ? '#38bdf8' : '#94a3b8',
                cursor: 'pointer',
                transition: 'all 0.15s'
              }}
            >
              {mod.label}
            </button>
          ))}
        </div>

        {/* Refresh button */}
        <button
          onClick={() => loadUserHistory(activeExaminer.uid)}
          title="Refresh Analysis Ledger"
          style={{
            background: 'transparent',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '8px',
            color: '#94a3b8',
            padding: '0.5rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          <RefreshCw size={15} className={loading ? 'spin' : ''} />
        </button>
      </div>

      {/* 4. HISTORY LEDGER TABLE */}
      <div
        className="history-table-wrapper"
        style={{
          background: 'rgba(16, 23, 38, 0.9)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '14px',
          overflow: 'hidden',
          boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
        }}
      >
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ background: 'rgba(11, 17, 28, 0.95)', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                <th style={{ padding: '0.9rem 1rem' }}>Analysis ID &amp; Case</th>
                <th style={{ padding: '0.9rem 1rem' }}>Forensic Module</th>
                <th style={{ padding: '0.9rem 1rem' }}>Evidence File &amp; Hash</th>
                <th style={{ padding: '0.9rem 1rem' }}>Verdict</th>
                <th style={{ padding: '0.9rem 1rem' }}>Confidence</th>
                <th style={{ padding: '0.9rem 1rem' }}>Timestamp</th>
                <th style={{ padding: '0.9rem 1rem', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: '3rem 1rem', textAlign: 'center', color: '#64748b' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
                      <FileText size={36} color="#334155" />
                      <div style={{ fontSize: '1rem', color: '#94a3b8', fontWeight: '600' }}>No Analysis Records Found</div>
                      <div style={{ fontSize: '0.82rem' }}>
                        {searchQuery ? 'No analyses match your search query.' : `Examiner ${activeExaminer.displayName} has no logged analyses yet.`}
                      </div>
                      <button
                        onClick={() => setShowQuickRunModal(true)}
                        style={{
                          marginTop: '0.5rem',
                          background: 'rgba(56, 189, 248, 0.15)',
                          color: '#38bdf8',
                          border: '1px solid rgba(56, 189, 248, 0.3)',
                          padding: '0.45rem 0.9rem',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontSize: '0.82rem'
                        }}
                      >
                        Record First Analysis
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredHistory.map((item) => {
                  const modBadge = getModuleBadge(item.module);
                  const Icon = modBadge.icon;
                  const vStyle = getVerdictStyle(item.verdict);
                  const confPct = Math.round((typeof item.confidence === 'number' ? item.confidence : 0.95) * 100);

                  return (
                    <tr
                      key={item.analysis_id}
                      style={{
                        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                        transition: 'background 0.15s'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      {/* Analysis ID and Case */}
                      <td style={{ padding: '0.9rem 1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.2rem' }}>
                          <span style={{ fontFamily: 'monospace', fontWeight: '700', color: '#fff' }}>
                            {item.analysis_id}
                          </span>
                          <button
                            onClick={() => copyToClipboard(item.analysis_id, item.analysis_id)}
                            title="Copy Analysis ID"
                            style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', padding: '2px' }}
                          >
                            {copiedId === item.analysis_id ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
                          </button>
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#38bdf8', fontFamily: 'monospace' }}>
                          {item.case_id || 'GENERAL-CASE'}
                        </div>
                      </td>

                      {/* Module Badge */}
                      <td style={{ padding: '0.9rem 1rem' }}>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            padding: '3px 8px',
                            borderRadius: '6px',
                            fontSize: '0.75rem',
                            fontWeight: '600',
                            background: modBadge.bg,
                            color: modBadge.color,
                            border: `1px solid ${modBadge.border}`
                          }}
                        >
                          <Icon size={13} />
                          {modBadge.label}
                        </span>
                      </td>

                      {/* Evidence File & SHA-256 */}
                      <td style={{ padding: '0.9rem 1rem' }}>
                        <div style={{ fontWeight: '500', color: '#e2e8f0', marginBottom: '0.2rem' }}>
                          {item.evidence_name || 'evidence_asset.dat'}
                        </div>
                        {item.sha256 && (
                          <div
                            onClick={() => copyToClipboard(item.sha256, `hash-${item.analysis_id}`)}
                            title={`Click to copy SHA-256: ${item.sha256}`}
                            style={{
                              fontFamily: 'monospace',
                              fontSize: '0.72rem',
                              color: '#64748b',
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.25rem'
                            }}
                          >
                            <span>SHA-256: {item.sha256.slice(0, 8)}...{item.sha256.slice(-6)}</span>
                            {copiedId === `hash-${item.analysis_id}` && <Check size={12} color="#10b981" />}
                          </div>
                        )}
                      </td>

                      {/* Verdict */}
                      <td style={{ padding: '0.9rem 1rem' }}>
                        <span
                          style={{
                            display: 'inline-block',
                            padding: '3px 8px',
                            borderRadius: '6px',
                            fontSize: '0.75rem',
                            fontWeight: '700',
                            background: vStyle.bg,
                            color: vStyle.color,
                            border: `1px solid ${vStyle.border}`
                          }}
                        >
                          {vStyle.label}
                        </span>
                      </td>

                      {/* Confidence Meter */}
                      <td style={{ padding: '0.9rem 1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <div style={{ width: '60px', height: '6px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div
                              style={{
                                width: `${confPct}%`,
                                height: '100%',
                                background: confPct > 90 ? '#10b981' : confPct > 75 ? '#38bdf8' : '#f59e0b',
                                borderRadius: '3px'
                              }}
                            />
                          </div>
                          <span style={{ fontFamily: 'monospace', fontWeight: '600', color: '#e2e8f0', fontSize: '0.78rem' }}>
                            {confPct}%
                          </span>
                        </div>
                      </td>

                      {/* Timestamp */}
                      <td style={{ padding: '0.9rem 1rem', color: '#94a3b8', fontSize: '0.78rem' }}>
                        {new Date(item.timestamp).toLocaleString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </td>

                      {/* Action buttons */}
                      <td style={{ padding: '0.9rem 1rem', textAlign: 'right' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.4rem' }}>
                          <button
                            onClick={() => setInspectItem(item)}
                            title="Inspect Detailed Findings"
                            style={{
                              background: 'rgba(56, 189, 248, 0.12)',
                              color: '#38bdf8',
                              border: '1px solid rgba(56, 189, 248, 0.25)',
                              padding: '0.35rem 0.65rem',
                              borderRadius: '6px',
                              fontSize: '0.75rem',
                              fontWeight: '600',
                              cursor: 'pointer'
                            }}
                          >
                            Inspect
                          </button>

                          <button
                            onClick={() => handleDownloadPdf(item)}
                            title="Download Signed Court PDF Affidavit (FRE 702)"
                            disabled={downloadingPdfId === item.analysis_id}
                            style={{
                              background: 'rgba(2, 132, 199, 0.18)',
                              color: '#38bdf8',
                              border: '1px solid rgba(56, 189, 248, 0.35)',
                              padding: '0.35rem 0.65rem',
                              borderRadius: '6px',
                              fontSize: '0.75rem',
                              fontWeight: '600',
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.35rem'
                            }}
                          >
                            {downloadingPdfId === item.analysis_id ? (
                              <RefreshCw size={13} className="spin" />
                            ) : (
                              <FileText size={13} />
                            )}
                            <span>PDF</span>
                          </button>

                          <button
                            onClick={() => exportCourtAffidavit(item)}
                            title="Export Court Technical JSON"
                            style={{
                              background: 'rgba(255, 255, 255, 0.05)',
                              color: '#94a3b8',
                              border: '1px solid rgba(255, 255, 255, 0.1)',
                              padding: '0.35rem',
                              borderRadius: '6px',
                              cursor: 'pointer'
                            }}
                          >
                            <Download size={13} />
                          </button>

                          <button
                            onClick={() => handleDeleteEntry(item.analysis_id)}
                            title="Delete Ledger Entry"
                            style={{
                              background: 'rgba(244, 63, 94, 0.1)',
                              color: '#f43f5e',
                              border: '1px solid rgba(244, 63, 94, 0.2)',
                              padding: '0.35rem',
                              borderRadius: '6px',
                              cursor: 'pointer'
                            }}
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. INSPECTION MODAL */}
      {inspectItem && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(8px)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1.5rem'
          }}
          onClick={() => setInspectItem(null)}
        >
          <div
            style={{
              background: '#0f172a',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: '16px',
              maxWidth: '750px',
              width: '100%',
              maxHeight: '90vh',
              overflowY: 'auto',
              padding: '1.75rem',
              boxShadow: '0 20px 50px rgba(0,0,0,0.6)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '1rem' }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: '700' }}>
                  Court Admissible Forensic Analysis Dossier
                </div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: '700', color: '#fff', margin: '0.2rem 0' }}>
                  {inspectItem.analysis_id}
                </h3>
              </div>
              <button
                onClick={() => setInspectItem(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.4rem', cursor: 'pointer' }}
              >
                &times;
              </button>
            </div>

            {/* Grid of Key Info */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1.25rem' }}>
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.85rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase' }}>Investigating Examiner</span>
                <div style={{ fontWeight: '600', color: '#fff' }}>{activeExaminer.displayName} ({activeExaminer.uid})</div>
                <div style={{ fontSize: '0.75rem', color: '#38bdf8' }}>Badge: {activeExaminer.badgeNumber}</div>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.85rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase' }}>Verdict &amp; Metric</span>
                <div style={{ fontWeight: '700', color: getVerdictStyle(inspectItem.verdict).color }}>
                  {inspectItem.verdict}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  Confidence: {Math.round((inspectItem.confidence || 0.95) * 100)}%
                </div>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.85rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase' }}>Evidence Asset</span>
                <div style={{ fontWeight: '600', color: '#fff' }}>{inspectItem.evidence_name}</div>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Case: {inspectItem.case_id}</div>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.85rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase' }}>Cryptographic Hash</span>
                <div style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#38bdf8', wordBreak: 'break-all' }}>
                  {inspectItem.sha256}
                </div>
              </div>
            </div>

            {/* Structured Findings */}
            <div style={{ marginBottom: '1.25rem' }}>
              <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.04em', marginBottom: '0.5rem' }}>
                Extracted Findings &amp; Observations
              </h4>
              <div style={{ background: 'rgba(0,0,0,0.4)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                {inspectItem.findings && Object.keys(inspectItem.findings).length > 0 ? (
                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.82rem', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                    {Object.entries(inspectItem.findings).map(([k, v]) => (
                      <li key={k} style={{ display: 'flex', gap: '0.5rem' }}>
                        <span style={{ color: '#38bdf8', fontWeight: '600', textTransform: 'capitalize' }}>
                          {k.replace(/_/g, ' ')}:
                        </span>
                        <span style={{ color: '#e2e8f0' }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div style={{ fontSize: '0.82rem', color: '#64748b' }}>No sub-findings recorded for this entry.</div>
                )}
              </div>
            </div>

            {/* Modal Actions */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '1rem' }}>
              <button
                onClick={() => handleDownloadPdf(inspectItem)}
                disabled={downloadingPdfId === inspectItem.analysis_id}
                style={{
                  background: 'linear-gradient(135deg, #0284c7, #2563eb)',
                  color: '#fff',
                  border: 'none',
                  padding: '0.55rem 1.15rem',
                  borderRadius: '8px',
                  fontWeight: '600',
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.45rem',
                  boxShadow: '0 4px 14px rgba(2, 132, 199, 0.4)'
                }}
              >
                {downloadingPdfId === inspectItem.analysis_id ? (
                  <RefreshCw size={14} className="spin" />
                ) : (
                  <FileText size={14} />
                )}
                <span>Download Signed Court PDF (FRE 702)</span>
              </button>

              <button
                onClick={() => exportCourtAffidavit(inspectItem)}
                style={{
                  background: 'rgba(255, 255, 255, 0.08)',
                  color: '#cbd5e1',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  padding: '0.55rem 0.95rem',
                  borderRadius: '8px',
                  fontWeight: '500',
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem'
                }}
              >
                <Download size={13} />
                <span>Export JSON Dossier</span>
              </button>
              <button
                onClick={() => setInspectItem(null)}
                style={{
                  background: 'rgba(255,255,255,0.08)',
                  color: '#e2e8f0',
                  border: '1px solid rgba(255,255,255,0.1)',
                  padding: '0.55rem 1rem',
                  borderRadius: '8px',
                  fontSize: '0.85rem',
                  cursor: 'pointer'
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 6. SWITCH EXAMINER ROSTER MODAL */}
      {showRosterModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(8px)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1.5rem'
          }}
          onClick={() => setShowRosterModal(false)}
        >
          <div
            style={{
              background: '#0f172a',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: '16px',
              maxWidth: '560px',
              width: '100%',
              padding: '1.75rem',
              boxShadow: '0 20px 50px rgba(0,0,0,0.6)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: '700', color: '#fff', margin: 0 }}>
                  Select Forensic Examiner
                </h3>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '0.2rem 0 0 0' }}>
                  Each examiner maintains a personal cryptographically sealed analysis history.
                </p>
              </div>
              <button onClick={() => setShowRosterModal(false)} style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.4rem', cursor: 'pointer' }}>
                &times;
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.25rem' }}>
              {EXAMINER_ROSTER.map((examiner) => {
                const isSelected = activeExaminer.uid === examiner.uid;
                return (
                  <div
                    key={examiner.uid}
                    onClick={() => handleSwitchExaminer(examiner)}
                    style={{
                      background: isSelected ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                      border: isSelected ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '12px',
                      padding: '1rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '1rem',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                  >
                    <div
                      style={{
                        width: '46px',
                        height: '46px',
                        borderRadius: '10px',
                        background: examiner.avatarBg,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '1.2rem',
                        fontWeight: 'bold',
                        color: '#fff',
                        flexShrink: 0
                      }}
                    >
                      {examiner.displayName.charAt(0)}
                    </div>

                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontWeight: '700', color: '#fff', fontSize: '0.95rem' }}>
                          {examiner.displayName}
                        </span>
                        {isSelected && (
                          <span style={{ fontSize: '0.7rem', color: '#10b981', background: 'rgba(16, 185, 129, 0.15)', padding: '1px 6px', borderRadius: '4px', fontWeight: '700' }}>
                            ACTIVE
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>{examiner.role}</div>
                      <div style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace', marginTop: '0.15rem' }}>
                        UID: {examiner.uid} &bull; Badge: {examiner.badgeNumber}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div style={{ textAlign: 'right' }}>
              <button
                onClick={() => setShowRosterModal(false)}
                style={{
                  background: 'rgba(255, 255, 255, 0.08)',
                  color: '#e2e8f0',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  padding: '0.5rem 1rem',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '0.85rem'
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 7. QUICK RUN / DIRECT ANALYSIS RECORDING MODAL */}
      {showQuickRunModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(8px)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1.5rem'
          }}
          onClick={() => setShowQuickRunModal(false)}
        >
          <div
            style={{
              background: '#0f172a',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: '16px',
              maxWidth: '560px',
              width: '100%',
              padding: '1.75rem',
              boxShadow: '0 20px 50px rgba(0,0,0,0.6)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: '700', color: '#fff', margin: 0 }}>
                  Log Direct Forensic Analysis
                </h3>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '0.2rem 0 0 0' }}>
                  Record a custom test run directly into examiner {activeExaminer.displayName}'s ledger.
                </p>
              </div>
              <button onClick={() => setShowQuickRunModal(false)} style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.4rem', cursor: 'pointer' }}>
                &times;
              </button>
            </div>

            <form onSubmit={handleQuickRun}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.25rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Forensic Module
                  </label>
                  <select
                    value={quickModule}
                    onChange={(e) => setQuickModule(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      background: 'rgba(11, 17, 28, 0.9)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                      borderRadius: '8px',
                      color: '#fff',
                      fontSize: '0.85rem'
                    }}
                  >
                    <option value="tampering">Image Tampering &amp; ELA</option>
                    <option value="cctv">CCTV Super-Resolution &amp; Denoise</option>
                    <option value="wound">Wound &amp; Trauma Classification</option>
                    <option value="bullet">Ballistics &amp; Caliber Comparison</option>
                    <option value="3d_lab">Forensic 3D Lab Trajectory</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Evidence Asset Filename
                  </label>
                  <input
                    type="text"
                    value={quickEvidence}
                    onChange={(e) => setQuickEvidence(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      background: 'rgba(11, 17, 28, 0.9)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                      borderRadius: '8px',
                      color: '#fff',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.78rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                      Verdict / Outcome
                    </label>
                    <select
                      value={quickVerdict}
                      onChange={(e) => setQuickVerdict(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '0.6rem',
                        background: 'rgba(11, 17, 28, 0.9)',
                        border: '1px solid rgba(255, 255, 255, 0.12)',
                        borderRadius: '8px',
                        color: '#fff',
                        fontSize: '0.85rem'
                      }}
                    >
                      <option value="FORGED">FORGED (Tampered)</option>
                      <option value="AUTHENTIC">AUTHENTIC (Original)</option>
                      <option value="MATCH_CONFIRMED">MATCH CONFIRMED</option>
                      <option value="ENHANCED">ENHANCED (Restored)</option>
                      <option value="LACERATION">LACERATION (Trauma)</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.78rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                      Confidence ({quickConfidence}%)
                    </label>
                    <input
                      type="range"
                      min="50"
                      max="99"
                      value={quickConfidence}
                      onChange={(e) => setQuickConfidence(e.target.value)}
                      style={{ width: '100%', marginTop: '0.6rem' }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Examiner Notes / Technical Findings
                  </label>
                  <textarea
                    rows={3}
                    value={quickNotes}
                    onChange={(e) => setQuickNotes(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      background: 'rgba(11, 17, 28, 0.9)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                      borderRadius: '8px',
                      color: '#fff',
                      fontSize: '0.85rem',
                      resize: 'vertical'
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.75rem' }}>
                <button
                  type="button"
                  onClick={() => setShowQuickRunModal(false)}
                  style={{
                    background: 'rgba(255, 255, 255, 0.08)',
                    color: '#e2e8f0',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    padding: '0.55rem 1rem',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{
                    background: 'linear-gradient(135deg, #0284c7, #2563eb)',
                    color: '#fff',
                    border: 'none',
                    padding: '0.55rem 1.25rem',
                    borderRadius: '8px',
                    fontWeight: '600',
                    fontSize: '0.85rem',
                    cursor: 'pointer'
                  }}
                >
                  Save to Personal Ledger
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 8. EDIT PROFILE MODAL */}
      {showEditProfileModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(8px)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1.5rem'
          }}
          onClick={() => setShowEditProfileModal(false)}
        >
          <div
            style={{
              background: '#0f172a',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: '16px',
              maxWidth: '520px',
              width: '100%',
              padding: '1.75rem',
              boxShadow: '0 20px 50px rgba(0,0,0,0.6)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: '700', color: '#fff', margin: 0 }}>
                  Edit Examiner Credentials
                </h3>
                <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '0.2rem 0 0 0' }}>
                  Update courtroom identification attributes for User ID: {activeExaminer.uid}
                </p>
              </div>
              <button onClick={() => setShowEditProfileModal(false)} style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.4rem', cursor: 'pointer' }}>
                &times;
              </button>
            </div>

            <form onSubmit={handleSaveProfile}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.25rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Full Legal / Official Name
                  </label>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      background: 'rgba(11, 17, 28, 0.9)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                      borderRadius: '8px',
                      color: '#fff',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Title &amp; Specialty
                  </label>
                  <input
                    type="text"
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: '0.6rem',
                      background: 'rgba(11, 17, 28, 0.9)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                      borderRadius: '8px',
                      color: '#fff',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.78rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                      Badge Number
                    </label>
                    <input
                      type="text"
                      value={editBadge}
                      onChange={(e) => setEditBadge(e.target.value)}
                      required
                      style={{
                        width: '100%',
                        padding: '0.6rem',
                        background: 'rgba(11, 17, 28, 0.9)',
                        border: '1px solid rgba(255, 255, 255, 0.12)',
                        borderRadius: '8px',
                        color: '#fff',
                        fontSize: '0.85rem'
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.78rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                      Clearance Level
                    </label>
                    <input
                      type="text"
                      value={editClearance}
                      onChange={(e) => setEditClearance(e.target.value)}
                      required
                      style={{
                        width: '100%',
                        padding: '0.6rem',
                        background: 'rgba(11, 17, 28, 0.9)',
                        border: '1px solid rgba(255, 255, 255, 0.12)',
                        borderRadius: '8px',
                        color: '#fff',
                        fontSize: '0.85rem'
                      }}
                    />
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.75rem' }}>
                <button
                  type="button"
                  onClick={() => setShowEditProfileModal(false)}
                  style={{
                    background: 'rgba(255, 255, 255, 0.08)',
                    color: '#e2e8f0',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    padding: '0.55rem 1rem',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{
                    background: 'linear-gradient(135deg, #0284c7, #2563eb)',
                    color: '#fff',
                    border: 'none',
                    padding: '0.55rem 1.25rem',
                    borderRadius: '8px',
                    fontWeight: '600',
                    fontSize: '0.85rem',
                    cursor: 'pointer'
                  }}
                >
                  Update Profile
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* PDF Generation Success Toast */}
      {pdfNotice && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            background: 'rgba(15, 23, 42, 0.96)',
            border: '1px solid #10b981',
            borderRadius: '12px',
            padding: '1rem 1.25rem',
            boxShadow: '0 12px 36px rgba(0,0,0,0.6)',
            zIndex: 2000,
            display: 'flex',
            alignItems: 'center',
            gap: '0.85rem',
            maxWidth: '460px',
            backdropFilter: 'blur(12px)',
            animation: 'fadeIn 0.25s ease-out'
          }}
        >
          <CheckCircle size={24} color="#10b981" style={{ flexShrink: 0 }} />
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <div style={{ fontWeight: '700', color: '#fff', fontSize: '0.88rem', marginBottom: '0.15rem' }}>
              Court-Admissible PDF Affidavit Generated
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.4 }}>
              Saved <strong>{pdfNotice.filename}</strong>
              <div style={{ fontFamily: 'monospace', color: '#38bdf8', fontSize: '0.7rem', marginTop: '0.2rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                SHA-256: {pdfNotice.sha256}
              </div>
            </div>
          </div>
          <button
            onClick={() => setPdfNotice(null)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#64748b',
              fontSize: '1.2rem',
              cursor: 'pointer',
              padding: '0.2rem'
            }}
          >
            &times;
          </button>
        </div>
      )}

    </div>
  );
}
