import React, { useState, useEffect } from 'react';
import {
  Cloud,
  Shield,
  Lock,
  Database,
  UploadCloud,
  FileText,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  UserCheck,
  HardDrive,
  Key,
  FolderLock,
  ExternalLink,
  PlusCircle,
  FileCheck2
} from 'lucide-react';
import { firebaseService } from '../services/firebase';

export default function FirebaseVault() {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState(null);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [uploadMessage, setUploadMessage] = useState('');
  const [selectedCase, setSelectedCase] = useState(null);
  const [auditTrail, setAuditTrail] = useState([]);
  
  // New Case Modal / Input
  const [showNewCase, setShowNewCase] = useState(false);
  const [newCaseId, setNewCaseId] = useState(`CASE-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`);
  const [newCaseTitle, setNewCaseTitle] = useState('');
  const [newCaseInvestigator, setNewCaseInvestigator] = useState('Chief Forensic Examiner');

  useEffect(() => {
    // 1. Auth Listener
    const unsub = firebaseService.onAuthStateChange((currentUser) => {
      setUser(currentUser);
    });

    // 2. Load Telemetry & Cases
    loadInitialData();

    return () => unsub();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const sysStatus = await firebaseService.getSystemStatus();
      setStatus(sysStatus);
      const caseList = await firebaseService.getCases();
      setCases(caseList);
      if (caseList.length > 0) {
        setSelectedCase(caseList[0]);
        loadAudit(caseList[0].case_id || caseList[0].id);
      }
    } catch (err) {
      console.error('Failed to load Firebase data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadAudit = async (caseId) => {
    try {
      const res = await fetch(`/api/v1/firebase/cases/${caseId}/audit`);
      if (res.ok) {
        const data = await res.json();
        setAuditTrail(data);
      }
    } catch {
      setAuditTrail([]);
    }
  };

  const handleCreateCase = async (e) => {
    e.preventDefault();
    if (!newCaseId || !newCaseTitle) return;

    const payload = {
      case_id: newCaseId,
      title: newCaseTitle,
      investigator: newCaseInvestigator,
      status: 'OPEN',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    await firebaseService.saveCase(payload);
    setShowNewCase(false);
    setNewCaseTitle('');
    setNewCaseId(`CASE-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`);
    loadInitialData();
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const activeCaseId = selectedCase?.case_id || selectedCase?.id || 'GLOBAL';
    setUploadProgress(10);
    setUploadMessage(`Encrypting and uploading ${file.name}...`);

    try {
      const result = await firebaseService.uploadEvidence(file, activeCaseId, (pct) => {
        setUploadProgress(Math.max(10, Math.round(pct)));
      });

      setUploadProgress(100);
      setUploadMessage(`Success! Saved to ${result.storage}`);
      setTimeout(() => {
        setUploadProgress(null);
        setUploadMessage('');
        loadInitialData();
      }, 2500);
    } catch (err) {
      setUploadProgress(null);
      setUploadMessage(`Upload error: ${err.message}`);
    }
  };

  const handleSyncLocalCase = async (caseId) => {
    try {
      const res = await fetch(`/api/v1/firebase/cases/${caseId}/sync`, { method: 'POST' });
      if (res.ok) {
        await res.json();
        loadInitialData();
      }
    } catch (err) {
      console.error('Failed to sync case:', err);
    }
  };

  return (
    <div className="firebase-vault-container" style={{ padding: '1.5rem', color: '#f8fafc' }}>
      {/* Top Banner / Hero */}
      <div
        className="vault-hero"
        style={{
          background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          borderRadius: '16px',
          padding: '1.75rem',
          boxShadow: '0 12px 30px rgba(0, 0, 0, 0.35)',
          backdropFilter: 'blur(12px)',
          marginBottom: '1.5rem',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div
              style={{
                width: '52px',
                height: '52px',
                borderRadius: '12px',
                background: 'linear-gradient(135deg, #0284c7 0%, #38bdf8 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 20px rgba(56, 189, 248, 0.4)',
              }}
            >
              <Cloud size={28} color="#ffffff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <h1 style={{ fontSize: '1.45rem', fontWeight: '700', margin: 0, letterSpacing: '0.02em' }}>
                  Firebase Cloud Forensic Vault
                </h1>
                <span
                  style={{
                    background: status?.is_live ? 'rgba(34, 197, 94, 0.2)' : 'rgba(56, 189, 248, 0.15)',
                    color: status?.is_live ? '#4ade80' : '#38bdf8',
                    border: `1px solid ${status?.is_live ? 'rgba(34, 197, 94, 0.4)' : 'rgba(56, 189, 248, 0.3)'}`,
                    padding: '0.2rem 0.65rem',
                    borderRadius: '20px',
                    fontSize: '0.72rem',
                    fontWeight: '600',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                  }}
                >
                  <span
                    style={{
                      width: '7px',
                      height: '7px',
                      borderRadius: '50%',
                      background: status?.is_live ? '#22c55e' : '#38bdf8',
                      boxShadow: status?.is_live ? '0 0 8px #22c55e' : '0 0 8px #38bdf8',
                    }}
                  />
                  {status?.is_live ? 'LIVE CLOUD CONNECTED' : 'AIR-GAPPED VAULT ACTIVE'}
                </span>
              </div>
              <p style={{ margin: '0.3rem 0 0 0', color: '#94a3b8', fontSize: '0.86rem' }}>
                Unified Firebase Authentication, Cloud Firestore Case Management, and Evidence Storage
              </p>
            </div>
          </div>

          {/* Quick Refresh & Spark Free Tier Badge */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                padding: '0.45rem 0.85rem',
                borderRadius: '8px',
                textAlign: 'right',
              }}
            >
              <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Firebase Tier</div>
              <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#fbbf24' }}>Spark Plan (100% Free)</div>
            </div>

            <button
              onClick={loadInitialData}
              disabled={loading}
              style={{
                background: 'rgba(56, 189, 248, 0.15)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                color: '#38bdf8',
                padding: '0.55rem 0.85rem',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                fontSize: '0.82rem',
                fontWeight: '600',
              }}
            >
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
              Sync Status
            </button>
          </div>
        </div>

        {/* Free Plan Quotas Row */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '0.75rem',
            marginTop: '1.25rem',
            paddingTop: '1rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <UserCheck size={18} color="#38bdf8" />
            <div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Auth Free Tier</div>
              <div style={{ fontSize: '0.85rem', fontWeight: '600' }}>50,000 Users / Month</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <Database size={18} color="#818cf8" />
            <div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Firestore Database</div>
              <div style={{ fontSize: '0.85rem', fontWeight: '600' }}>1 GB • 50k Reads / Day</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <HardDrive size={18} color="#34d399" />
            <div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Cloud Storage</div>
              <div style={{ fontSize: '0.85rem', fontWeight: '600' }}>5 GB Free Capacity</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <Shield size={18} color="#fbbf24" />
            <div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Active Project ID</div>
              <div style={{ fontSize: '0.85rem', fontWeight: '600', fontFamily: 'monospace' }}>
                {status?.project_id || 'feas-forensics-dev'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Left = Case Vault & Storage, Right = Examiner & Audit Ledger */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '1.5rem' }}>
        {/* Left Column: Cloud Cases & Evidence Upload */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Case Records Card */}
          <div
            style={{
              background: 'rgba(30, 41, 59, 0.7)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '14px',
              padding: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FolderLock size={19} color="#38bdf8" />
                <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: '600' }}>
                  Cloud Case Registry ({cases.length})
                </h3>
              </div>

              <button
                onClick={() => setShowNewCase(!showNewCase)}
                style={{
                  background: 'linear-gradient(135deg, #0284c7 0%, #38bdf8 100%)',
                  border: 'none',
                  color: '#ffffff',
                  padding: '0.45rem 0.85rem',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  fontSize: '0.78rem',
                  fontWeight: '600',
                }}
              >
                <PlusCircle size={14} />
                New Case
              </button>
            </div>

            {/* New Case Form */}
            {showNewCase && (
              <form
                onSubmit={handleCreateCase}
                style={{
                  background: 'rgba(15, 23, 42, 0.9)',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  borderRadius: '8px',
                  padding: '1rem',
                  marginBottom: '1rem',
                }}
              >
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '0.75rem', marginBottom: '0.75rem' }}>
                  <div>
                    <label style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Case Number</label>
                    <input
                      type="text"
                      value={newCaseId}
                      onChange={(e) => setNewCaseId(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '0.4rem 0.6rem',
                        background: '#0f172a',
                        border: '1px solid rgba(255,255,255,0.15)',
                        borderRadius: '4px',
                        color: '#fff',
                        fontSize: '0.8rem',
                      }}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Case Title / Allegation</label>
                    <input
                      type="text"
                      placeholder="e.g. CCTV Tamper & Vehicle Tracking Investigation"
                      value={newCaseTitle}
                      onChange={(e) => setNewCaseTitle(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '0.4rem 0.6rem',
                        background: '#0f172a',
                        border: '1px solid rgba(255,255,255,0.15)',
                        borderRadius: '4px',
                        color: '#fff',
                        fontSize: '0.8rem',
                      }}
                      required
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                  <button
                    type="button"
                    onClick={() => setShowNewCase(false)}
                    style={{
                      background: 'transparent',
                      border: '1px solid rgba(255,255,255,0.2)',
                      color: '#94a3b8',
                      padding: '0.35rem 0.75rem',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    style={{
                      background: '#0284c7',
                      border: 'none',
                      color: '#fff',
                      padding: '0.35rem 0.85rem',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      fontWeight: '600',
                    }}
                  >
                    Register to Firestore
                  </button>
                </div>
              </form>
            )}

            {/* Cases List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              {cases.map((c) => {
                const cid = c.case_id || c.id;
                const isSelected = (selectedCase?.case_id || selectedCase?.id) === cid;

                return (
                  <div
                    key={cid}
                    onClick={() => {
                      setSelectedCase(c);
                      loadAudit(cid);
                    }}
                    style={{
                      background: isSelected ? 'rgba(56, 189, 248, 0.12)' : 'rgba(15, 23, 42, 0.6)',
                      border: `1px solid ${isSelected ? 'rgba(56, 189, 248, 0.4)' : 'rgba(255, 255, 255, 0.06)'}`,
                      borderRadius: '8px',
                      padding: '0.85rem 1rem',
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontFamily: 'monospace', fontWeight: '700', color: '#38bdf8', fontSize: '0.82rem' }}>
                          {cid}
                        </span>
                        <span
                          style={{
                            fontSize: '0.68rem',
                            padding: '0.15rem 0.45rem',
                            borderRadius: '4px',
                            background: c.status === 'OPEN' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(234, 179, 8, 0.2)',
                            color: c.status === 'OPEN' ? '#4ade80' : '#facc15',
                          }}
                        >
                          {c.status || 'OPEN'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.86rem', fontWeight: '500', marginTop: '0.2rem' }}>
                        {c.title || 'Forensic Examination'}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '0.2rem' }}>
                        Investigator: {c.investigator || 'Examiner'} &bull; Updated:{' '}
                        {new Date(c.updated_at || Date.now()).toLocaleTimeString()}
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSyncLocalCase(cid);
                        }}
                        title="Synchronize case & reports to Cloud Storage"
                        style={{
                          background: 'rgba(56, 189, 248, 0.1)',
                          border: '1px solid rgba(56, 189, 248, 0.25)',
                          color: '#38bdf8',
                          padding: '0.35rem 0.65rem',
                          borderRadius: '4px',
                          fontSize: '0.72rem',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.3rem',
                          cursor: 'pointer',
                        }}
                      >
                        <RefreshCw size={12} />
                        Sync Cloud
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Cloud Storage & Evidence Ingestion */}
          <div
            style={{
              background: 'rgba(30, 41, 59, 0.7)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '14px',
              padding: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <UploadCloud size={19} color="#34d399" />
              <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: '600' }}>
                Cloud Evidence & PDF Vault (Firebase Storage)
              </h3>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '0 0 1rem 0' }}>
              Upload original CCTV clips, high-res weapon images, or court-admissible PDF reports directly into Firebase Cloud Storage.
            </p>

            <div
              style={{
                border: '2px dashed rgba(56, 189, 248, 0.3)',
                borderRadius: '8px',
                padding: '1.5rem',
                textAlign: 'center',
                background: 'rgba(15, 23, 42, 0.4)',
                cursor: 'pointer',
              }}
              onClick={() => document.getElementById('cloud-upload-input').click()}
            >
              <input
                id="cloud-upload-input"
                type="file"
                style={{ display: 'none' }}
                onChange={handleFileUpload}
              />
              <FileCheck2 size={32} color="#38bdf8" style={{ margin: '0 auto 0.5rem auto' }} />
              <div style={{ fontSize: '0.88rem', fontWeight: '600', color: '#f1f5f9' }}>
                Click to Select Evidence or Report to Upload
              </div>
              <div style={{ fontSize: '0.74rem', color: '#94a3b8', marginTop: '0.25rem' }}>
                Files will be saved under: <code>cases/{selectedCase?.case_id || 'GLOBAL'}/evidence/</code>
              </div>
            </div>

            {/* Upload Progress Bar */}
            {uploadProgress !== null && (
              <div style={{ marginTop: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                  <span>{uploadMessage}</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div style={{ height: '6px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${uploadProgress}%`,
                      height: '100%',
                      background: 'linear-gradient(90deg, #38bdf8 0%, #34d399 100%)',
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Examiner RBAC Profile & Immutable Audit Trail */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Forensic Examiner Card */}
          <div
            style={{
              background: 'rgba(30, 41, 59, 0.7)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '14px',
              padding: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <Lock size={18} color="#fbbf24" />
              <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: '600' }}>
                Firebase Examiner Authentication
              </h3>
            </div>

            <div
              style={{
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                padding: '1rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: '700',
                    color: '#0f172a',
                  }}
                >
                  FE
                </div>
                <div>
                  <div style={{ fontSize: '0.88rem', fontWeight: '700' }}>
                    {user?.displayName || 'Chief Forensic Examiner'}
                  </div>
                  <div style={{ fontSize: '0.74rem', color: '#94a3b8' }}>{user?.email || 'examiner@feas-forensics.gov'}</div>
                </div>
              </div>

              <div style={{ fontSize: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8' }}>RBAC Role:</span>
                  <span style={{ fontWeight: '600', color: '#38bdf8' }}>{user?.role || 'lead_investigator'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8' }}>Badge ID:</span>
                  <span style={{ fontFamily: 'monospace', color: '#f8fafc' }}>{user?.badgeNumber || 'FEAS-8842'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#94a3b8' }}>Clearance:</span>
                  <span style={{ color: '#4ade80', fontWeight: '600' }}>{user?.clearance || 'Secret / Judicial'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Immutable Chain-of-Custody Audit Ledger */}
          <div
            style={{
              background: 'rgba(30, 41, 59, 0.7)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '14px',
              padding: '1.25rem',
              flex: 1,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <FileText size={18} color="#818cf8" />
              <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: '600' }}>
                Chain of Custody Ledger (Firestore)
              </h3>
            </div>
            <div style={{ fontSize: '0.74rem', color: '#94a3b8', marginBottom: '0.75rem' }}>
              Cryptographic integrity records for Case: <strong>{selectedCase?.case_id || selectedCase?.id || 'GLOBAL'}</strong>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '320px', overflowY: 'auto' }}>
              {auditTrail.length === 0 ? (
                <div style={{ color: '#64748b', fontSize: '0.78rem', textAlign: 'center', padding: '1.5rem' }}>
                  No audit trail recorded yet for this case.
                </div>
              ) : (
                auditTrail.map((ev, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: 'rgba(15, 23, 42, 0.6)',
                      borderLeft: '3px solid #38bdf8',
                      padding: '0.55rem 0.75rem',
                      borderRadius: '4px',
                      fontSize: '0.74rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: '700', color: '#f1f5f9' }}>{ev.event_type}</span>
                      <span style={{ color: '#94a3b8', fontSize: '0.68rem' }}>
                        {new Date(ev.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div style={{ color: '#94a3b8', marginTop: '0.15rem' }}>By: {ev.user}</div>
                    {ev.details && Object.keys(ev.details).length > 0 && (
                      <pre
                        style={{
                          margin: '0.25rem 0 0 0',
                          padding: '0.3rem',
                          background: 'rgba(0,0,0,0.3)',
                          borderRadius: '3px',
                          fontSize: '0.66rem',
                          color: '#cbd5e1',
                          overflowX: 'auto',
                        }}
                      >
                        {JSON.stringify(ev.details, null, 2)}
                      </pre>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
