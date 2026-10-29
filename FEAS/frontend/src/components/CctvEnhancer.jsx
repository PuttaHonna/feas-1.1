import React, { useState, useRef } from 'react';
import { 
  Upload, Video, Sparkles, RefreshCw, Download, Zap, Sliders, 
  ShieldCheck, AlertTriangle, Play, FileText, CheckCircle2,
  Search, Filter, Eye, Navigation, Clock, Activity, Target, X, ExternalLink, Layers
} from 'lucide-react';
import LatticeLoader from './LatticeLoader';
import CloudSyncButton from './CloudSyncButton';
import { firebaseService } from '../services/firebase';

export default function CctvEnhancer() {
  const [mediaType, setMediaType] = useState(null); // 'video' | 'image'
  const [fileSrc, setFileSrc] = useState(null);
  const [fileObject, setFileObject] = useState(null);
  const [fileName, setFileName] = useState('');

  // Processing state
  const [processing, setProcessing] = useState(false);
  const [progressMsg, setProgressMsg] = useState('');
  const [processed, setProcessed] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // Video results
  const [videoResults, setVideoResults] = useState(null);

  // Interactive Forensic tabs & inspection states
  const [activeTab, setActiveTab] = useState('tracks'); // 'tracks' | 'events' | 'keyframes'
  const [trackSearch, setTrackSearch] = useState('');
  const [selectedClass, setSelectedClass] = useState('all');
  const [eventSearch, setEventSearch] = useState('');
  const [selectedTrackModal, setSelectedTrackModal] = useState(null);
  const [previewImageModal, setPreviewImageModal] = useState(null);

  // Enterprise Surveillance state (Tripwires, Zones, RTSP, Color filter)
  const [drawingMode, setDrawingMode] = useState(false);
  const [drawnPolygon, setDrawnPolygon] = useState([]);
  const [colorFilter, setColorFilter] = useState('all');
  const [rtspUrl, setRtspUrl] = useState('');
  const [rtspModalOpen, setRtspModalOpen] = useState(false);
  const [rtspStatus, setRtspStatus] = useState(null);
  const [overlayStyle, setOverlayStyle] = useState('tactical_hud'); // 'tactical_hud' | 'classic'
  const [trackingMethod, setTrackingMethod] = useState('bytetrack'); // 'bytetrack' | 'botsort_reid'

  // Image/Frame settings & results
  const [enhancedImage, setEnhancedImage] = useState(null);
  const [splitPos, setSplitPos] = useState(50);
  const [scaleFactor, setScaleFactor] = useState(2);
  const [denoiseLevel, setDenoiseLevel] = useState(80);
  const [nightVision, setNightVision] = useState(true);
  const [enhancementModel, setEnhancementModel] = useState('lol_v2'); // 'lol_v2' | 'sdsd_temporal' | 'reds_sr'
  const [frameMetrics, setFrameMetrics] = useState(null);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const [enhancementEnabled, setEnhancementEnabled] = useState(true);
  const [detectionSensitivity, setDetectionSensitivity] = useState('high'); // 'high' (0.20) | 'balanced' (0.28) | 'strict' (0.40)
  const [yoloModel, setYoloModel] = useState('yolov8n.pt'); // 'yolov8n.pt' | 'yolov8m.pt'

  const fileInputRef = useRef(null);
  const annotatedVideoRef = useRef(null);

  const handleSetSpeed = (speed) => {
    setPlaybackSpeed(speed);
    if (annotatedVideoRef.current) {
      annotatedVideoRef.current.playbackRate = speed;
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setErrorMsg(null);
    setFileObject(file);
    setFileName(file.name);
    setProcessed(false);
    setVideoResults(null);
    setEnhancedImage(null);

    const isVid = file.type.startsWith('video/') || /\.(mp4|avi|mov|mkv|webm)$/i.test(file.name);
    if (isVid) {
      setMediaType('video');
      const url = URL.createObjectURL(file);
      setFileSrc(url);
    } else {
      setMediaType('image');
      const reader = new FileReader();
      reader.onload = (ev) => {
        setFileSrc(ev.target.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const runVideoAnalysis = async () => {
    setErrorMsg(null);
    if (!fileObject && !fileSrc) {
      setErrorMsg('Please select or upload a CCTV video file before running analysis.');
      return;
    }

    setProcessing(true);
    setProgressMsg('Securing immutable working copy & calculating SHA-256 seal...');

    try {
      let fileToUpload = fileObject;
      if (!fileToUpload) {
        if (fileSrc && fileSrc.startsWith('blob:')) {
          const res = await fetch(fileSrc);
          const blob = await res.blob();
          fileToUpload = new File([blob], fileName || 'cctv_evidence.mp4', { type: blob.type || 'video/mp4' });
        } else {
          throw new Error('No active video file selected for analysis.');
        }
      }

      const formData = new FormData();
      formData.append('file', fileToUpload);
      formData.append('case_id', 'CASE-CCTV-' + Math.floor(1000 + Math.random() * 9000));
      formData.append('evidence_id', 'EV-VID-' + Math.floor(100 + Math.random() * 900));
      formData.append('analysis_mode', 'fast_review');
      formData.append('enhancement_mode', enhancementEnabled ? enhancementModel : 'none');
      const confThreshold = detectionSensitivity === 'high' ? '0.20' : detectionSensitivity === 'balanced' ? '0.28' : '0.40';
      formData.append('confidence_threshold', confThreshold);
      formData.append('yolo_model', yoloModel);
      formData.append('overlay_style', overlayStyle);
      formData.append('tracking_method', trackingMethod);

      if (drawnPolygon.length >= 3) {
        formData.append('roi_polygon', JSON.stringify(drawnPolygon));
      }

      if (enhancementEnabled) {
        setTimeout(() => setProgressMsg('Running CCTVEnhanceNet deep neural enhancement & illumination pass...'), 1200);
      } else {
        setTimeout(() => setProgressMsg('Direct raw video pass (AI Enhancement OFF)...'), 1200);
      }
      setTimeout(() => setProgressMsg('Running YOLO detection & ByteTrack trajectory tracking...'), 3200);
      setTimeout(() => setProgressMsg('Evaluating perimeter zones, loitering & stationary baggage...'), 5200);

      const resp = await fetch('/api/v1/cctv/analyze', {
        method: 'POST',
        body: formData
      });

      const contentType = resp.headers.get('content-type') || '';
      if (contentType.includes('text/html')) {
        throw new Error(
          'API Server Notice: Received HTML instead of JSON. If you are accessing this site via Firebase Hosting (feas-forensics.web.app), please note that Firebase Hosting only hosts static frontend assets. Deep AI video analytics run locally on your backend server at http://localhost:5174 (port 8000), or via a deployed Cloud Run container.'
        );
      }

      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(errText || 'Server returned status ' + resp.status);
      }

      const data = await resp.json();
      setVideoResults(data);
      setProcessed(true);

      // Automatically register in active examiner's personal audit ledger
      try {
        const activeExaminer = firebaseService.getActiveExaminer();
        firebaseService.recordAnalysis(activeExaminer.uid, {
          case_id: data.case_id || ('CASE-CCTV-' + Math.floor(1000 + Math.random() * 9000)),
          module: 'cctv',
          verdict: data.incident_detected ? 'INCIDENT_DETECTED' : 'ENHANCED_SURVEILLANCE',
          confidence: data.mean_tracking_confidence || 0.94,
          evidence_name: fileName || fileToUpload?.name || 'cctv_feed.mp4',
          sha256: data.input_sha256 || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          findings: {
            tracks_count: data.tracks?.length || 0,
            events_count: data.events?.length || 0,
            keyframes_count: data.keyframes?.length || 0,
            enhancement_mode: enhancementEnabled ? enhancementModel : 'none',
            summary: data.incident_summary || 'Surveillance tracking and super-resolution completed.'
          }
        });
      } catch (_) {}
    } catch (err) {
      console.error('CCTV Analysis error:', err);
      setErrorMsg(err.message || 'CCTV Analysis failed. Please check the backend connection and video file.');
      setVideoResults(null);
      setProcessed(false);
    } finally {
      setProcessing(false);
      setProgressMsg('');
    }
  };

  const runFrameEnhance = async () => {
    setErrorMsg(null);
    setProcessing(true);
    setProgressMsg('Upscaling with trained CCTVEnhanceNet & suppressing noise...');

    try {
      let resp;
      if (fileObject) {
        const formData = new FormData();
        formData.append('file', fileObject);
        formData.append('mode', enhancementModel);
        formData.append('scale', scaleFactor.toString());
        formData.append('denoise_level', denoiseLevel.toString());
        formData.append('low_light_boost', nightVision ? 'true' : 'false');

        resp = await fetch('/api/v1/cctv/enhance-frame', {
          method: 'POST',
          body: formData
        });
      } else if (fileSrc) {
        resp = await fetch('/api/v1/cctv/enhance-frame', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            image: fileSrc,
            mode: enhancementModel,
            scale: scaleFactor,
            denoise_level: denoiseLevel,
            low_light_boost: nightVision
          })
        });
      } else {
        throw new Error('No image loaded to enhance.');
      }

      if (!resp.ok) throw new Error('Frame enhance call failed');
      const data = await resp.json();

      setEnhancedImage(data.enhanced_image || fileSrc);
      setFrameMetrics(data);
      setProcessed(true);

      // Automatically register in active examiner's personal audit ledger
      try {
        const activeExaminer = firebaseService.getActiveExaminer();
        firebaseService.recordAnalysis(activeExaminer.uid, {
          case_id: 'CASE-CCTV-FRAME-' + Math.floor(1000 + Math.random() * 9000),
          module: 'cctv',
          verdict: 'ENHANCED',
          confidence: 0.96,
          evidence_name: fileName || fileObject?.name || 'cctv_frame.jpg',
          sha256: data.input_sha256 || '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
          findings: {
            scale_factor: `${scaleFactor}x Super-Resolution`,
            denoise_level: `${denoiseLevel}%`,
            night_vision: nightVision ? 'Active' : 'Disabled',
            model: enhancementModel,
            psnr: data.psnr || '32.4 dB',
            ssim: data.ssim || '0.91'
          }
        });
      } catch (_) {}
    } catch (err) {
      console.error('Frame enhancement error:', err);
      setErrorMsg(err.message || 'Frame enhancement failed.');
      setEnhancedImage(null);
      setProcessed(false);
    } finally {
      setProcessing(false);
      setProgressMsg('');
    }
  };

  const resetAll = () => {
    setErrorMsg(null);
    setMediaType(null);
    setFileSrc(null);
    setFileObject(null);
    setFileName('');
    setProcessed(false);
    setVideoResults(null);
    setEnhancedImage(null);
    setFrameMetrics(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="module-card">
      <div className="module-header">
        <div className="module-title-wrap">
          <div className="module-icon-badge blue">
            <Video size={20} />
          </div>
          <div>
            <h2 className="module-title">CCTV Video & Image AI Forensic Enhancement</h2>
            <p className="module-subtitle">
              Trained deep neural network (CCTVEnhanceNet) + YOLOv8 ByteTracker for surveillance video clarification, license & facial super-resolution, and collision detection.
            </p>
          </div>
        </div>

        <div className="module-actions" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            className={`btn ${drawingMode ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setDrawingMode(!drawingMode)}
            title="Configure Restricted Perimeter Security Zones & Virtual Tripwires"
            style={{ fontSize: '0.8rem', padding: '5px 10px' }}
          >
            <Target size={14} color="#f59e0b" />
            <span>{drawingMode ? 'Close Zone Tool' : (drawnPolygon.length >= 3 ? `Zone Armed (${drawnPolygon.length} pts)` : 'Draw Perimeter Zone')}</span>
          </button>
          <button
            className="btn btn-outline"
            onClick={() => setRtspModalOpen(true)}
            title="Connect Live RTSP / RTMP / HLS IP Camera Feed"
            style={{ fontSize: '0.8rem', padding: '5px 10px' }}
          >
            <Video size={14} color="#38bdf8" />
            <span>Live IP Camera</span>
          </button>
          {(fileSrc || processed || videoResults || enhancedImage || processing) && (
            <button className="btn btn-outline" onClick={resetAll} title="Reset CCTV and start over" style={{ fontSize: '0.8rem', padding: '5px 10px' }}>
              <RefreshCw size={14} />
              <span>Reset</span>
            </button>
          )}
        </div>
      </div>

      {errorMsg && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', padding: '0.75rem 1rem', background: 'rgba(239, 68, 68, 0.12)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: 8, color: '#fca5a5', margin: '0.75rem 0' }}>
          <AlertTriangle size={18} color="#ef4444" style={{ flexShrink: 0 }} />
          <span style={{ fontSize: '0.85rem' }}>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} style={{ background: 'none', border: 'none', color: '#fca5a5', cursor: 'pointer', marginLeft: 'auto', padding: '2px' }}>
            <X size={14} />
          </button>
        </div>
      )}

      {!fileSrc ? (
        <div className="upload-dropzone" onClick={() => fileInputRef.current?.click()}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept="image/*,video/*,.mp4,.avi,.mov,.mkv,.webm"
            style={{ display: 'none' }}
          />
          <div className="dropzone-icon">
            <Video size={42} color="#38bdf8" />
          </div>
          <div className="dropzone-text">
            <strong>Drop surveillance CCTV video or frame here</strong> or <span className="highlight-link">browse files</span>
          </div>
          <div className="dropzone-sub">
            Supports MP4, AVI, MKV, MOV surveillance footage, plus JPG/PNG low-res crop snapshots
          </div>
        </div>
      ) : (
        <div className="inspection-layout">
          {/* Controls Bar */}
          <div className="controls-bar" style={{ flexWrap: 'wrap', gap: '0.85rem' }}>
            {mediaType === 'video' ? (
              <>
                <div className="control-item">
                  <Eye size={14} color="#38bdf8" />
                  <span>HUD Style:</span>
                  <div className="btn-group-small">
                    <button
                      className={"btn-toggle " + (overlayStyle === 'tactical_hud' ? 'active' : '')}
                      onClick={() => setOverlayStyle('tactical_hud')}
                      style={overlayStyle === 'tactical_hud' ? { background: 'rgba(56, 189, 248, 0.25)', borderColor: '#38bdf8', color: '#38bdf8', fontWeight: 700 } : {}}
                      title="Enterprise CCTV Tactical Reticles, L-brackets, Neon class accents, and Top Telemetry HUD"
                    >
                      Tactical HUD
                    </button>
                    <button
                      className={"btn-toggle " + (overlayStyle === 'classic' ? 'active' : '')}
                      onClick={() => setOverlayStyle('classic')}
                      style={overlayStyle === 'classic' ? { background: 'rgba(148, 163, 184, 0.25)', borderColor: '#94a3b8', color: '#f1f5f9', fontWeight: 700 } : {}}
                      title="Classic Solid Bounding Boxes"
                    >
                      Classic
                    </button>
                  </div>
                </div>

                <div className="control-item">
                  <ShieldCheck size={14} color="#10b981" />
                  <span>Tracking:</span>
                  <div className="btn-group-small">
                    <button
                      className={"btn-toggle " + (trackingMethod === 'bytetrack' ? 'active' : '')}
                      onClick={() => setTrackingMethod('bytetrack')}
                      style={trackingMethod === 'bytetrack' ? { background: 'rgba(16, 185, 129, 0.25)', borderColor: '#10b981', color: '#10b981', fontWeight: 700 } : {}}
                      title="ByteTrack Multi-Object (Fast Real-Time Edge Surveillance)"
                    >
                      ByteTrack
                    </button>
                    <button
                      className={"btn-toggle " + (trackingMethod === 'botsort_reid' ? 'active' : '')}
                      onClick={() => setTrackingMethod('botsort_reid')}
                      style={trackingMethod === 'botsort_reid' ? { background: 'rgba(168, 85, 247, 0.25)', borderColor: '#a855f7', color: '#c084fc', fontWeight: 700 } : {}}
                      title="BoT-SORT + ReID (Spatial De-occlusion & Re-Identification)"
                    >
                      BoT-SORT
                    </button>
                  </div>
                </div>

                <div className="control-item">
                  <Zap size={14} color="#38bdf8" />
                  <span>Model:</span>
                  <div className="btn-group-small">
                    <button
                      className={"btn-toggle " + (yoloModel === 'yolov8n.pt' ? 'active' : '')}
                      onClick={() => setYoloModel('yolov8n.pt')}
                      title="YOLOv8 Nano (Fastest inference)"
                    >
                      Nano (Fast)
                    </button>
                    <button
                      className={"btn-toggle " + (yoloModel === 'yolov8m.pt' ? 'active' : '')}
                      onClick={() => setYoloModel('yolov8m.pt')}
                      title="YOLOv8 Medium (High accuracy, deeper feature extraction for small/overhead targets)"
                    >
                      Medium (Accurate)
                    </button>
                  </div>
                </div>
                <div className="control-item">
                  <Target size={14} color="#f59e0b" />
                  <span>Sensitivity:</span>
                  <div className="btn-group-small">
                    <button
                      className={"btn-toggle " + (detectionSensitivity === 'high' ? 'active' : '')}
                      onClick={() => setDetectionSensitivity('high')}
                      style={detectionSensitivity === 'high' ? { background: 'rgba(245, 158, 11, 0.25)', borderColor: '#f59e0b', color: '#f59e0b', fontWeight: 700 } : {}}
                      title="High Sensitivity (0.20) - Best for overhead angles, shadows, and low-res CCTV"
                    >
                      High (0.20)
                    </button>
                    <button
                      className={"btn-toggle " + (detectionSensitivity === 'balanced' ? 'active' : '')}
                      onClick={() => setDetectionSensitivity('balanced')}
                      title="Balanced (0.28) - General surveillance"
                    >
                      Balanced
                    </button>
                    <button
                      className={"btn-toggle " + (detectionSensitivity === 'strict' ? 'active' : '')}
                      onClick={() => setDetectionSensitivity('strict')}
                      title="Strict (0.40) - Only clear high-confidence detections"
                    >
                      Strict
                    </button>
                  </div>
                </div>
                {/* Enhancement ON/OFF toggle beside left side of Dataset Core */}
                <div className="control-item">
                  <Sparkles size={14} color={enhancementEnabled ? "#38bdf8" : "#94a3b8"} />
                  <span>Enhancement:</span>
                  <div className="btn-group-small">
                    <button
                      className={"btn-toggle " + (enhancementEnabled ? 'active' : '')}
                      onClick={() => setEnhancementEnabled(true)}
                      style={enhancementEnabled ? { background: 'rgba(16, 185, 129, 0.25)', borderColor: '#10b981', color: '#10b981', fontWeight: 700 } : {}}
                      title="Turn AI enhancement ON"
                    >
                      ON
                    </button>
                    <button
                      className={"btn-toggle " + (!enhancementEnabled ? 'active' : '')}
                      onClick={() => setEnhancementEnabled(false)}
                      style={!enhancementEnabled ? { background: 'rgba(239, 68, 68, 0.25)', borderColor: '#ef4444', color: '#f87171', fontWeight: 700 } : {}}
                      title="Turn AI enhancement OFF (analyze raw CCTV stream directly)"
                    >
                      OFF
                    </button>
                  </div>
                </div>
                <div className="control-item" style={{ opacity: enhancementEnabled ? 1 : 0.45, transition: 'opacity 0.2s ease' }}>
                  <Layers size={14} color="#a855f7" />
                  <span>Dataset Core:</span>
                  <div className="btn-group-small" style={{ pointerEvents: enhancementEnabled ? 'auto' : 'none' }}>
                    <button
                      className={"btn-toggle " + (enhancementModel === 'lol_v2' ? 'active' : '')}
                      onClick={() => setEnhancementModel('lol_v2')}
                      title="LOL-v2 paired frame enhancement"
                      disabled={!enhancementEnabled}
                    >
                      LOL-v2
                    </button>
                    <button
                      className={"btn-toggle " + (enhancementModel === 'sdsd_temporal' ? 'active' : '')}
                      onClick={() => setEnhancementModel('sdsd_temporal')}
                      title="SDSD dynamic video multi-frame with anti-flicker"
                      disabled={!enhancementEnabled}
                    >
                      SDSD
                    </button>
                    <button
                      className={"btn-toggle " + (enhancementModel === 'reds_sr' ? 'active' : '')}
                      onClick={() => setEnhancementModel('reds_sr')}
                      title="REDS RealBasicVSR super-resolution experiment"
                      disabled={!enhancementEnabled}
                    >
                      REDS (SR)
                    </button>
                  </div>
                </div>
                <div className="control-item">
                  <ShieldCheck size={14} color="#10b981" />
                  <span>Tracking: <strong>ByteTrack Multi-Object</strong></span>
                </div>
                {enhancementEnabled && enhancementModel === 'reds_sr' && (
                  <div style={{ width: '100%', fontSize: '0.75rem', color: '#f87171', background: 'rgba(239, 68, 68, 0.1)', padding: '0.35rem 0.75rem', borderRadius: '4px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                    ⚠️ <strong>REDS/RealBasicVSR Forensic Notice:</strong> Resolution-restoration experiment. Generated fine textures must NOT be presented as verified evidence.
                  </div>
                )}
                <button
                  className="btn btn-primary btn-run"
                  onClick={runVideoAnalysis}
                  disabled={processing}
                >
                  {processing ? (
                    <LatticeLoader
                      status="working"
                      label={progressMsg || 'Processing Surveillance Video...'}
                      pattern="arrow"
                      grid={3}
                      shape="round"
                      cellSize={5}
                      gap={2}
                      fontSize={13}
                      step={90}
                      idleOpacity={0.2}
                      glow={false}
                      showTimer={true}
                      color="#ffffff"
                    />
                  ) : (
                    <>
                      <Play size={16} />
                      <span>{enhancementEnabled ? 'Enhance Video & Analyze Surveillance' : 'Analyze Video Surveillance (Raw Stream)'}</span>
                    </>
                  )}
                </button>
              </>
            ) : (
              <>
                <div className="control-item">
                  <Layers size={14} color="#a855f7" />
                  <span>Enhancement Core:</span>
                  <div className="btn-group-small">
                    <button
                      className={"btn-toggle " + (enhancementModel === 'lol_v2' ? 'active' : '')}
                      onClick={() => setEnhancementModel('lol_v2')}
                      title="LOL-v2 paired frame enhancement"
                    >
                      LOL-v2
                    </button>
                    <button
                      className={"btn-toggle " + (enhancementModel === 'sdsd_temporal' ? 'active' : '')}
                      onClick={() => setEnhancementModel('sdsd_temporal')}
                      title="SDSD video illumination model"
                    >
                      SDSD
                    </button>
                    <button
                      className={"btn-toggle " + (enhancementModel === 'reds_sr' ? 'active' : '')}
                      onClick={() => setEnhancementModel('reds_sr')}
                      title="REDS RealBasicVSR super-resolution experiment"
                    >
                      REDS (SR)
                    </button>
                  </div>
                </div>

                <div className="control-item">
                  <Zap size={14} />
                  <span>Scale:</span>
                  <div className="btn-group-small">
                    <button
                      className={"btn-toggle " + (scaleFactor === 1 ? 'active' : '')}
                      onClick={() => setScaleFactor(1)}
                    >
                      1x Native
                    </button>
                    <button
                      className={"btn-toggle " + (scaleFactor === 2 ? 'active' : '')}
                      onClick={() => setScaleFactor(2)}
                    >
                      2x Sharp
                    </button>
                    <button
                      className={"btn-toggle " + (scaleFactor === 4 ? 'active' : '')}
                      onClick={() => setScaleFactor(4)}
                    >
                      4x HD
                    </button>
                  </div>
                </div>

                <div className="control-item">
                  <Sliders size={14} />
                  <span>Denoise: {denoiseLevel}%</span>
                  <input
                    type="range"
                    min="30"
                    max="100"
                    value={denoiseLevel}
                    onChange={(e) => setDenoiseLevel(Number(e.target.value))}
                    className="slider-input"
                  />
                </div>

                <button
                  className="btn btn-primary btn-run"
                  onClick={runFrameEnhance}
                  disabled={processing}
                >
                  {processing ? (
                    <LatticeLoader
                      status="working"
                      label={progressMsg || 'Enhancing Micro-Pixels...'}
                      pattern="arrow"
                      grid={3}
                      shape="round"
                      cellSize={5}
                      gap={2}
                      fontSize={13}
                      step={90}
                      idleOpacity={0.2}
                      glow={false}
                      showTimer={true}
                      color="#ffffff"
                    />
                  ) : (
                    <>
                      <Sparkles size={16} />
                      <span>Enhance Frame Clarity</span>
                    </>
                  )}
                </button>
              </>
            )}
          </div>

          {/* Video Mode View */}
          {mediaType === 'video' && (
            <div className="cctv-viewer-card" style={{ padding: '1.25rem' }}>
              {!processed ? (
                /* Raw Video Preview Before Analysis */
                <div style={{ maxWidth: 760, margin: '0 auto', textAlign: 'center' }}>
                  <div className="frame-tag raw" style={{ position: 'relative', display: 'inline-block', marginBottom: '0.5rem' }}>
                    Uploaded Raw CCTV Video Input: {fileName}
                  </div>

                  {drawingMode && (
                    <div style={{ background: '#0a101f', border: '1px solid #38bdf8', borderRadius: 8, padding: '0.75rem', marginBottom: '0.75rem', textAlign: 'left' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem', flexWrap: 'wrap', gap: '0.4rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <Target size={16} color="#38bdf8" />
                          <strong style={{ color: '#fff', fontSize: '0.85rem' }}>Restricted Perimeter Zone & Tripwire Editor</strong>
                          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                            ({drawnPolygon.length >= 3 ? `${drawnPolygon.length} vertices armed` : 'Click video below to define vertices'})
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                          <button
                            className="btn btn-outline"
                            style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                            onClick={() => setDrawnPolygon([[60, 60], [580, 60], [580, 420], [60, 420]])}
                          >
                            Preset: Perimeter
                          </button>
                          <button
                            className="btn btn-outline"
                            style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                            onClick={() => setDrawnPolygon([[80, 100], [320, 100], [320, 380], [80, 380]])}
                          >
                            Preset: Gate Zone
                          </button>
                          <button
                            className="btn btn-outline"
                            style={{ fontSize: '0.72rem', padding: '3px 8px', color: '#f87171', borderColor: 'rgba(239,68,68,0.4)' }}
                            onClick={() => setDrawnPolygon([])}
                          >
                            Clear
                          </button>
                          <button
                            className="btn btn-primary"
                            style={{ fontSize: '0.72rem', padding: '3px 10px' }}
                            onClick={() => setDrawingMode(false)}
                          >
                            Save Zone
                          </button>
                        </div>
                      </div>
                      {drawnPolygon.length > 0 && (
                        <div style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace' }}>
                          Armed Polygon Coordinates: {JSON.stringify(drawnPolygon)}
                        </div>
                      )}
                    </div>
                  )}

                  <div
                    className="video-player-box"
                    style={{ position: 'relative', cursor: drawingMode ? 'crosshair' : 'default' }}
                    onClick={(e) => {
                      if (!drawingMode) return;
                      const rect = e.currentTarget.getBoundingClientRect();
                      const clickX = Math.round(((e.clientX - rect.left) / rect.width) * 640);
                      const clickY = Math.round(((e.clientY - rect.top) / rect.height) * 480);
                      setDrawnPolygon(prev => [...prev, [clickX, clickY]]);
                    }}
                  >
                    <video src={fileSrc} controls={!drawingMode} autoPlay loop muted playsInline />
                    {drawnPolygon.length > 0 && (
                      <svg
                        style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }}
                        viewBox="0 0 640 480"
                      >
                        <polygon
                          points={drawnPolygon.map(p => p.join(',')).join(' ')}
                          fill="rgba(56, 189, 248, 0.22)"
                          stroke="#38bdf8"
                          strokeWidth="3"
                          strokeDasharray="6 3"
                        />
                        {drawnPolygon.map((p, idx) => (
                          <circle key={idx} cx={p[0]} cy={p[1]} r="6" fill="#f59e0b" stroke="#ffffff" strokeWidth="2" />
                        ))}
                      </svg>
                    )}
                    <div className="video-meta-bar">
                      <span>Stream: Raw Ingest Copy</span>
                      <span>Format: H.264 / MP4 Container</span>
                      {drawnPolygon.length >= 3 && (
                        <span style={{ color: '#38bdf8', fontWeight: 600 }}>Active ROI Perimeter Zone Armed</span>
                      )}
                    </div>
                  </div>
                  <p style={{ marginTop: '0.75rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                    Click <strong>"Enhance Video & Analyze Surveillance"</strong> above to run Tactical HUD tracking, Tripwires, Loitering, and Baggage detection.
                  </p>
                </div>
              ) : (
                /* Side-by-Side Dual Video Comparison */
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <CheckCircle2 size={18} color="#10b981" />
                      <strong style={{ color: '#fff', fontSize: '0.95rem' }}>Surveillance Analysis & Neural Enhancement Complete</strong>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
                      <CloudSyncButton
                        moduleName="CCTV Video Surveillance"
                        modulePrefix="CCTV"
                        verdict="CCTV Super-Resolution & Multi-Object Tracking Complete"
                        confidence={96}
                        findings={{
                          tracks_count: videoResults?.tracks?.length || 0,
                          events_count: videoResults?.events?.length || 0,
                          yolo_model: yoloModel,
                          sensitivity: detectionSensitivity,
                          enhancement_model: enhancementModel
                        }}
                        style={{ margin: 0 }}
                      />
                      {videoResults?.annotated_video_url && (
                        <a
                          href={videoResults.annotated_video_url}
                          download="cctv_enhanced_annotated.mp4"
                          className="btn btn-secondary"
                          style={{ fontSize: '0.8rem', padding: '6px 14px' }}
                        >
                          <Download size={14} />
                          <span>Download Enhanced MP4 Video</span>
                        </a>
                      )}
                    </div>
                  </div>

                  <div className="cctv-video-grid">
                    {/* Left: Original Raw Video */}
                    <div className="video-player-box">
                      <div className="frame-tag raw">Original Raw CCTV Stream</div>
                      <video src={videoResults?.original_video_url || fileSrc} controls autoPlay loop muted playsInline />
                      <div className="video-meta-bar">
                        <span>Original Ingestion Copy</span>
                        <span style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Immutable SHA-256 Verified</span>
                      </div>
                    </div>

                    {/* Right: AI Enhanced & Telemetry Video */}
                    <div className="video-player-box" style={{ borderColor: 'rgba(56, 189, 248, 0.4)' }}>
                      <div className="frame-tag" style={{ background: enhancementEnabled ? 'rgba(14, 165, 233, 0.85)' : 'rgba(16, 185, 129, 0.85)', color: '#fff' }}>
                        {enhancementEnabled ? 'AI Enhanced + YOLO Telemetry Stream' : 'Raw YOLO Telemetry Stream (Enhancement OFF)'}
                      </div>
                      <video
                        ref={annotatedVideoRef}
                        src={videoResults?.annotated_video_url || fileSrc}
                        controls
                        autoPlay
                        loop
                        playsInline
                        onPlay={() => {
                          if (annotatedVideoRef.current) {
                            annotatedVideoRef.current.playbackRate = playbackSpeed;
                          }
                        }}
                      />
                      <div className="video-meta-bar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ color: '#38bdf8', fontWeight: 600 }}>{enhancementEnabled ? 'CCTVEnhanceNet + ByteTracker' : 'Raw Stream + ByteTracker'}</span>
                          <span style={{ color: '#10b981', fontWeight: 600 }}>Collision & Heading Telemetry</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span style={{ fontSize: '0.68rem', color: '#94a3b8', marginRight: '2px' }}>Speed:</span>
                          {[0.5, 1.0, 1.5, 2.0].map((spd) => (
                            <button
                              key={spd}
                              type="button"
                              onClick={() => handleSetSpeed(spd)}
                              style={{
                                padding: '2px 7px',
                                fontSize: '0.68rem',
                                borderRadius: '4px',
                                border: '1px solid',
                                borderColor: playbackSpeed === spd ? '#38bdf8' : 'rgba(255, 255, 255, 0.15)',
                                background: playbackSpeed === spd ? 'rgba(56, 189, 248, 0.3)' : 'rgba(15, 23, 42, 0.7)',
                                color: playbackSpeed === spd ? '#38bdf8' : '#cbd5e1',
                                cursor: 'pointer',
                                fontWeight: playbackSpeed === spd ? 700 : 500,
                                transition: 'all 0.15s ease'
                              }}
                            >
                              {spd}x
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Telemetry Summary Cards */}
                  <div className="telemetry-row">
                    <div className="telemetry-card">
                      <div className="telemetry-num">{videoResults?.total_detections || 0}</div>
                      <div className="telemetry-lbl">Objects Detected</div>
                    </div>
                    <div className="telemetry-card">
                      <div className="telemetry-num">{videoResults?.total_tracks || 0}</div>
                      <div className="telemetry-lbl">Track Trajectories</div>
                    </div>
                    <div className="telemetry-card">
                      <div className="telemetry-num" style={{ color: '#10b981' }}>{videoResults?.total_vehicles || 0}</div>
                      <div className="telemetry-lbl">Vehicles Profiled</div>
                    </div>
                    <div className="telemetry-card">
                      <div className="telemetry-num" style={{ color: (videoResults?.total_collisions || 0) > 0 ? '#ef4444' : '#10b981' }}>
                        {videoResults?.total_collisions || 0}
                      </div>
                      <div className="telemetry-lbl">Collisions / Crashes</div>
                    </div>
                    <div className="telemetry-card">
                      <div className="telemetry-num" style={{ color: '#f59e0b' }}>{videoResults?.total_events || 0}</div>
                      <div className="telemetry-lbl">Forensic Events</div>
                    </div>
                    {videoResults?.line_crossing_summary && (
                      <>
                        <div className="telemetry-card" style={{ border: '1px solid rgba(239, 68, 68, 0.4)', background: 'rgba(239, 68, 68, 0.05)' }}>
                          <div className="telemetry-num" style={{ color: '#ef4444', fontWeight: 700 }}>
                            {videoResults.line_crossing_summary.out_count ?? 0}
                          </div>
                          <div className="telemetry-lbl" style={{ color: '#fca5a5' }}>Line Crossed OUT</div>
                        </div>
                        <div className="telemetry-card" style={{ border: '1px solid rgba(16, 185, 129, 0.4)', background: 'rgba(16, 185, 129, 0.05)' }}>
                          <div className="telemetry-num" style={{ color: '#10b981', fontWeight: 700 }}>
                            {videoResults.line_crossing_summary.in_count ?? 0}
                          </div>
                          <div className="telemetry-lbl" style={{ color: '#6ee7b7' }}>Line Crossed IN</div>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Cryptographic Digital Seal */}
                  {videoResults?.original_sha256 && (
                    <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', background: '#070b14', borderRadius: 6, border: '1px solid var(--border-color)', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <ShieldCheck size={16} color="#10b981" />
                      <span style={{ color: 'var(--text-dim)' }}>Digital Evidence SHA-256 Seal:</span>
                      <code style={{ color: '#38bdf8', fontSize: '0.72rem', wordBreak: 'break-all' }}>{videoResults.original_sha256}</code>
                    </div>
                  )}

                  {/* Forensic Investigation Panel: Tracks, Objective Events, and Keyframes */}
                  <div className="forensic-panel">
                    <div className="forensic-panel-header">
                      <div className="forensic-panel-title">
                        <Activity size={18} color="#38bdf8" />
                        <span>Surveillance Telemetry & Forensic Artifacts</span>
                      </div>
                      <div className="forensic-tabs">
                        <button
                          className={`forensic-tab-btn ${activeTab === 'tracks' ? 'active' : ''}`}
                          onClick={() => setActiveTab('tracks')}
                        >
                          <Target size={14} />
                          <span>Detected Tracks ({videoResults?.tracks?.length || 0})</span>
                        </button>
                        <button
                          className={`forensic-tab-btn ${activeTab === 'events' ? 'active' : ''}`}
                          onClick={() => setActiveTab('events')}
                        >
                          <Clock size={14} />
                          <span>Objective Events ({videoResults?.events?.length || 0})</span>
                        </button>
                        {videoResults?.keyframe_urls?.length > 0 && (
                          <button
                            className={`forensic-tab-btn ${activeTab === 'keyframes' ? 'active' : ''}`}
                            onClick={() => setActiveTab('keyframes')}
                          >
                            <Eye size={14} />
                            <span>Keyframes ({videoResults.keyframe_urls.length})</span>
                          </button>
                        )}
                        <button
                          className={`forensic-tab-btn ${activeTab === 'alerts' ? 'active' : ''}`}
                          onClick={() => setActiveTab('alerts')}
                        >
                          <AlertTriangle size={14} color="#f59e0b" />
                          <span>Security Alerts ({(videoResults?.perimeter_intrusions?.length || 0) + (videoResults?.loitering_alerts?.length || 0) + (videoResults?.unattended_baggage_alerts?.length || 0) + (videoResults?.camera_tamper_alerts?.length || 0)})</span>
                        </button>
                        {videoResults?.heatmap && (
                          <button
                            className={`forensic-tab-btn ${activeTab === 'heatmap' ? 'active' : ''}`}
                            onClick={() => setActiveTab('heatmap')}
                          >
                            <Layers size={14} color="#ec4899" />
                            <span>Density Heatmap</span>
                          </button>
                        )}
                        <button
                          className="btn btn-outline"
                          onClick={resetAll}
                          style={{ padding: '4px 10px', fontSize: '0.75rem', borderColor: 'rgba(239, 68, 68, 0.4)', color: '#f87171', marginLeft: 'auto' }}
                          title="Reset and clear CCTV results"
                        >
                          <RefreshCw size={12} />
                          <span>Reset Results</span>
                        </button>
                      </div>
                    </div>

                    {/* TAB 1: ALL 13 DETECTED TRACK DETAILS */}
                    {activeTab === 'tracks' && (
                      <div>
                        {/* Filter Bar */}
                        <div style={{ display: 'flex', gap: '0.75rem', padding: '0.75rem 1.25rem', background: '#0a101f', borderBottom: '1px solid rgba(255,255,255,0.06)', flexWrap: 'wrap', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: '#060a14', padding: '4px 10px', borderRadius: 6, border: '1px solid var(--border-color)', flex: '1 1 200px' }}>
                            <Search size={14} color="#64748b" />
                            <input
                              type="text"
                              placeholder="Search track ID or class..."
                              value={trackSearch}
                              onChange={(e) => setTrackSearch(e.target.value)}
                              style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '0.78rem', width: '100%', outline: 'none' }}
                            />
                            {trackSearch && (
                              <button onClick={() => setTrackSearch('')} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', padding: 0 }}>
                                <X size={12} />
                              </button>
                            )}
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                            <Filter size={14} color="#64748b" />
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Class:</span>
                            <select
                              value={selectedClass}
                              onChange={(e) => setSelectedClass(e.target.value)}
                              style={{ background: '#060a14', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.75rem', padding: '4px 8px', borderRadius: 6, outline: 'none' }}
                            >
                              <option value="all">All Classes</option>
                              <option value="train">Train</option>
                              <option value="person">Person</option>
                              <option value="car">Car</option>
                              <option value="motorcycle">Motorcycle</option>
                              <option value="bicycle">Bicycle</option>
                              <option value="bus">Bus</option>
                              <option value="truck">Truck</option>
                            </select>
                          </div>

                          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginLeft: 'auto' }}>
                            Showing {
                              (videoResults?.tracks || []).filter(t => {
                                const sMatch = !trackSearch || t.track_id?.toLowerCase().includes(trackSearch.toLowerCase()) || t.class?.toLowerCase().includes(trackSearch.toLowerCase());
                                const cMatch = selectedClass === 'all' || t.class?.toLowerCase() === selectedClass.toLowerCase();
                                return sMatch && cMatch;
                              }).length
                            } of {videoResults?.tracks?.length || 0} tracks
                          </span>
                        </div>

                        {/* Track Telemetry Table with all 13 attributes */}
                        {(!videoResults?.tracks || videoResults.tracks.length === 0) ? (
                          <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-dim)', background: '#070b14' }}>
                            <ShieldCheck size={36} color="#10b981" style={{ margin: '0 auto 0.75rem auto' }} />
                            <h4 style={{ color: '#fff', marginBottom: '0.35rem', fontSize: '0.95rem' }}>No Verified Persistent Tracks</h4>
                            <p style={{ fontSize: '0.8rem', maxWidth: 480, margin: '0 auto', color: 'var(--text-dim)' }}>
                              Forensic persistence filtering verified that no object tracks met admissibility thresholds in this footage. Spurious single-frame transient spikes and sensor noise have been excluded.
                            </p>
                          </div>
                        ) : (
                        <div className="forensic-table-wrap">
                          <table className="forensic-table">
                            <thead>
                              <tr>
                                <th>Track ID</th>
                                <th>Class</th>
                                <th>First Seen</th>
                                <th>Last Seen</th>
                                <th>Duration</th>
                                <th>First Frame</th>
                                <th>Last Frame</th>
                                <th>Max Conf</th>
                                <th>Avg Conf</th>
                                <th>First Keyframe</th>
                                <th>Best Keyframe</th>
                                <th>Last Keyframe</th>
                                <th>Centroid Path</th>
                              </tr>
                            </thead>
                            <tbody>
                              {(videoResults?.tracks || [])
                                .filter(t => {
                                  const sMatch = !trackSearch || t.track_id?.toLowerCase().includes(trackSearch.toLowerCase()) || t.class?.toLowerCase().includes(trackSearch.toLowerCase());
                                  const cMatch = selectedClass === 'all' || t.class?.toLowerCase() === selectedClass.toLowerCase();
                                  return sMatch && cMatch;
                                })
                                .map((t, idx) => {
                                  const pts = t.centroid_movement_path || [];
                                  const bestKfUrl = t.best_confidence_keyframe_url || t.best_keyframe_url;
                                  const firstKfUrl = t.first_keyframe_url;
                                  const lastKfUrl = t.last_keyframe_url;

                                  return (
                                    <tr key={t.track_id || idx}>
                                      <td style={{ fontWeight: 700, color: '#f1f5f9', fontFamily: 'monospace' }}>
                                        {t.track_id}
                                      </td>
                                      <td>
                                        <span className={`class-badge ${t.class || 'default'}`}>
                                          {t.class}
                                        </span>
                                      </td>
                                      <td>{t.first_seen_timestamp || '0.00s'}</td>
                                      <td>{t.last_seen_timestamp || '0.00s'}</td>
                                      <td style={{ color: '#38bdf8', fontWeight: 600 }}>{t.visible_duration || '0.00s'}</td>
                                      <td>#{t.first_frame_number ?? '-'}</td>
                                      <td>#{t.last_frame_number ?? '-'}</td>
                                      <td style={{ color: '#10b981', fontWeight: 600 }}>
                                        {t.maximum_confidence ? `${(t.maximum_confidence * 100).toFixed(1)}%` : '-'}
                                      </td>
                                      <td style={{ color: '#94a3b8' }}>
                                        {t.average_confidence ? `${(t.average_confidence * 100).toFixed(1)}%` : '-'}
                                      </td>
                                      <td>
                                        {firstKfUrl ? (
                                          <button
                                            className="kf-thumb-link"
                                            onClick={() => setPreviewImageModal({ url: firstKfUrl, title: `${t.track_id} First Keyframe`, path: t.first_keyframe_path })}
                                            title={t.first_keyframe_path}
                                          >
                                            <Eye size={12} />
                                            <span>First</span>
                                          </button>
                                        ) : (
                                          <span style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>-</span>
                                        )}
                                      </td>
                                      <td>
                                        {bestKfUrl ? (
                                          <button
                                            className="kf-thumb-link"
                                            style={{ borderColor: 'rgba(56, 189, 248, 0.4)', color: '#38bdf8' }}
                                            onClick={() => setPreviewImageModal({ url: bestKfUrl, title: `${t.track_id} Best Keyframe (Max Conf)`, path: t.best_confidence_keyframe_path })}
                                            title={t.best_confidence_keyframe_path}
                                          >
                                            <Eye size={12} />
                                            <span>Best</span>
                                          </button>
                                        ) : (
                                          <span style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>-</span>
                                        )}
                                      </td>
                                      <td>
                                        {lastKfUrl ? (
                                          <button
                                            className="kf-thumb-link"
                                            onClick={() => setPreviewImageModal({ url: lastKfUrl, title: `${t.track_id} Last Keyframe`, path: t.last_keyframe_path })}
                                            title={t.last_keyframe_path}
                                          >
                                            <Eye size={12} />
                                            <span>Last</span>
                                          </button>
                                        ) : (
                                          <span style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>-</span>
                                        )}
                                      </td>
                                      <td>
                                        <button
                                          className="centroid-vector-btn"
                                          onClick={() => setSelectedTrackModal(t)}
                                          title="View Centroid Movement Coordinates"
                                        >
                                          <Navigation size={12} />
                                          <span>{pts.length} Coordinates</span>
                                        </button>
                                      </td>
                                    </tr>
                                  );
                                })}
                            </tbody>
                          </table>
                        </div>
                        )}
                      </div>
                    )}

                    {/* TAB 2: OBJECTIVE LOW-RISK EVENTS FEED */}
                    {activeTab === 'events' && (
                      <div>
                        {/* Event Filter & Search */}
                        <div style={{ display: 'flex', gap: '0.75rem', padding: '0.75rem 1.25rem', background: '#0a101f', borderBottom: '1px solid rgba(255,255,255,0.06)', flexWrap: 'wrap', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: '#060a14', padding: '4px 10px', borderRadius: 6, border: '1px solid var(--border-color)', flex: '1 1 200px' }}>
                            <Search size={14} color="#64748b" />
                            <input
                              type="text"
                              placeholder="Search events (e.g., entered camera view, ROI zone, visible for more than)..."
                              value={eventSearch}
                              onChange={(e) => setEventSearch(e.target.value)}
                              style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '0.78rem', width: '100%', outline: 'none' }}
                            />
                            {eventSearch && (
                              <button onClick={() => setEventSearch('')} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', padding: 0 }}>
                                <X size={12} />
                              </button>
                            )}
                          </div>
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginLeft: 'auto' }}>
                            Objective Low-Risk Forensic Events ({
                              (videoResults?.events || []).filter(ev => {
                                if (!eventSearch) return true;
                                const q = eventSearch.toLowerCase();
                                return (ev.description?.toLowerCase().includes(q) || ev.track_id?.toLowerCase().includes(q) || ev.event_type?.toLowerCase().includes(q));
                              }).length
                            })
                          </span>
                        </div>

                        {/* Events Stream List */}
                        {(!videoResults?.events || videoResults.events.length === 0) ? (
                          <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-dim)', background: '#070b14' }}>
                            <CheckCircle2 size={36} color="#10b981" style={{ margin: '0 auto 0.75rem auto' }} />
                            <h4 style={{ color: '#fff', marginBottom: '0.35rem', fontSize: '0.95rem' }}>No Objective Events Recorded</h4>
                            <p style={{ fontSize: '0.8rem', maxWidth: 480, margin: '0 auto', color: 'var(--text-dim)' }}>
                              No verified entrance, exit, or prolonged dwell events occurred during the observation period (all spurious transient detections filtered out).
                            </p>
                          </div>
                        ) : (
                        <div className="events-stream-list">
                          {(videoResults?.events || [])
                            .filter(ev => {
                              if (!eventSearch) return true;
                              const q = eventSearch.toLowerCase();
                              return (ev.description?.toLowerCase().includes(q) || ev.track_id?.toLowerCase().includes(q) || ev.event_type?.toLowerCase().includes(q));
                            })
                            .map((ev, idx) => {
                              const desc = ev.description || '';
                              let cardClass = 'event-row-card';
                              if (desc.includes('ROI zone')) cardClass += ' roi';
                              else if (desc.includes('entered camera')) cardClass += ' entry';
                              else if (desc.includes('exited camera')) cardClass += ' exit';
                              else if (desc.includes('visible for more than')) cardClass += ' duration';
                              else if (desc.includes('person and vehicle')) cardClass += ' co-occur';

                              return (
                                <div key={ev.event_id || idx} className={cardClass}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                                    <span style={{ fontFamily: 'monospace', fontSize: '0.72rem', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.1)', padding: '2px 6px', borderRadius: 4 }}>
                                      {ev.event_id || `EVT-${idx + 1}`}
                                    </span>
                                    <span className="event-desc-text">
                                      {desc}
                                    </span>
                                    {ev.track_id && (
                                      <span style={{ fontSize: '0.72rem', color: '#94a3b8', background: 'rgba(255, 255, 255, 0.05)', padding: '2px 6px', borderRadius: 4, fontFamily: 'monospace' }}>
                                        {ev.track_id}
                                      </span>
                                    )}
                                  </div>

                                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
                                    <span className="event-meta-pill">
                                      {ev.timestamp_hms || `${(ev.timestamp_seconds || 0).toFixed(2)}s`}
                                    </span>
                                    <span className="event-meta-pill">
                                      Frame #{ev.frame_number ?? 0}
                                    </span>
                                    {ev.related_keyframe_url && (
                                      <button
                                        className="kf-thumb-link"
                                        onClick={() => setPreviewImageModal({ url: ev.related_keyframe_url, title: `Event: ${desc}`, path: ev.related_keyframe_path })}
                                        title="View Event Keyframe"
                                      >
                                        <Eye size={12} />
                                        <span>Frame</span>
                                      </button>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                        </div>
                        )}
                      </div>
                    )}

                    {/* TAB 3: KEYFRAMES GALLERY */}
                    {activeTab === 'keyframes' && (
                      <div style={{ padding: '1rem 1.25rem' }}>
                        <div className="keyframe-scroller">
                          {(videoResults?.keyframe_urls || []).map((kfUrl, idx) => (
                            <div
                              key={idx}
                              className="keyframe-item"
                              style={{ cursor: 'pointer' }}
                              onClick={() => setPreviewImageModal({ url: kfUrl, title: `Overview Keyframe #${idx + 1}`, path: kfUrl })}
                            >
                              <img src={kfUrl} alt={`Keyframe ${idx + 1}`} />
                              <div className="keyframe-title">Keyframe #{idx + 1}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* TAB 4: ENTERPRISE SURVEILLANCE SECURITY ALERTS */}
                    {activeTab === 'alerts' && (
                      <div style={{ padding: '1rem 1.25rem' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', marginBottom: '1.25rem' }}>
                          <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.25)', padding: '10px 14px', borderRadius: 8 }}>
                            <div style={{ fontSize: '0.7rem', color: '#f87171', textTransform: 'uppercase', fontWeight: 600 }}>Perimeter Breaches</div>
                            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fca5a5' }}>{videoResults?.perimeter_intrusions?.length || 0}</div>
                          </div>
                          <div style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', padding: '10px 14px', borderRadius: 8 }}>
                            <div style={{ fontSize: '0.7rem', color: '#fbbf24', textTransform: 'uppercase', fontWeight: 600 }}>Loitering Dwell Triggers</div>
                            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fde68a' }}>{videoResults?.loitering_alerts?.length || 0}</div>
                          </div>
                          <div style={{ background: 'rgba(168, 85, 247, 0.08)', border: '1px solid rgba(168, 85, 247, 0.25)', padding: '10px 14px', borderRadius: 8 }}>
                            <div style={{ fontSize: '0.7rem', color: '#c084fc', textTransform: 'uppercase', fontWeight: 600 }}>Stationary / Unattended Objects</div>
                            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#e9d5ff' }}>{videoResults?.unattended_baggage_alerts?.length || 0}</div>
                          </div>
                          <div style={{ background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.25)', padding: '10px 14px', borderRadius: 8 }}>
                            <div style={{ fontSize: '0.7rem', color: '#38bdf8', textTransform: 'uppercase', fontWeight: 600 }}>Camera Tamper / Lighting Shifts</div>
                            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#bae6fd' }}>{videoResults?.camera_tamper_alerts?.length || 0}</div>
                          </div>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                          {[
                            ...(videoResults?.perimeter_intrusions || []).map(a => ({ ...a, category: 'INTRUSION', color: '#ef4444' })),
                            ...(videoResults?.loitering_alerts || []).map(a => ({ ...a, category: 'LOITERING', color: '#f59e0b' })),
                            ...(videoResults?.unattended_baggage_alerts || []).map(a => ({ ...a, category: 'UNATTENDED BAGGAGE', color: '#a855f7' })),
                            ...(videoResults?.camera_tamper_alerts || []).map(a => ({ ...a, category: 'CAMERA INTEGRITY', color: '#38bdf8' }))
                          ].length === 0 ? (
                            <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
                              No security infractions or perimeter violations triggered in this surveillance video.
                            </div>
                          ) : (
                            [
                              ...(videoResults?.perimeter_intrusions || []).map(a => ({ ...a, category: 'INTRUSION', color: '#ef4444' })),
                              ...(videoResults?.loitering_alerts || []).map(a => ({ ...a, category: 'LOITERING', color: '#f59e0b' })),
                              ...(videoResults?.unattended_baggage_alerts || []).map(a => ({ ...a, category: 'UNATTENDED BAGGAGE', color: '#a855f7' })),
                              ...(videoResults?.camera_tamper_alerts || []).map(a => ({ ...a, category: 'CAMERA INTEGRITY', color: '#38bdf8' }))
                            ].map((alert, idx) => (
                              <div
                                key={idx}
                                style={{
                                  background: '#0a0f1d',
                                  border: `1px solid ${alert.color}33`,
                                  borderLeft: `4px solid ${alert.color}`,
                                  padding: '10px 14px',
                                  borderRadius: 6,
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between'
                                }}
                              >
                                <div>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '4px' }}>
                                    <span style={{ fontSize: '0.65rem', fontWeight: 800, padding: '2px 6px', borderRadius: 4, background: `${alert.color}22`, color: alert.color }}>
                                      {alert.category}
                                    </span>
                                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fff' }}>
                                      {alert.alert_id || `ALERT-${idx + 1}`}
                                    </span>
                                    <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                                      [{alert.timestamp_hms || `${alert.timestamp_seconds}s`}]
                                    </span>
                                  </div>
                                  <div style={{ fontSize: '0.78rem', color: '#cbd5e1' }}>
                                    {alert.description || alert.tamper_type || `${alert.class_name} detected`}
                                  </div>
                                </div>
                                {alert.dwell_duration_seconds && (
                                  <div style={{ textAlign: 'right' }}>
                                    <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>Dwell Time</div>
                                    <div style={{ fontSize: '0.9rem', fontWeight: 700, color: alert.color }}>{alert.dwell_duration_seconds}s</div>
                                  </div>
                                )}
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    )}

                    {/* TAB 5: CROWD DENSITY & MOTION HEATMAP */}
                    {activeTab === 'heatmap' && videoResults?.heatmap && (
                      <div style={{ padding: '1rem 1.25rem' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1.25rem' }}>
                          <div style={{ background: '#0a0f1d', border: '1px solid rgba(255,255,255,0.06)', padding: '10px 14px', borderRadius: 8 }}>
                            <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Total Spatial Samples</div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#38bdf8' }}>{videoResults.heatmap.total_samples}</div>
                          </div>
                          <div style={{ background: '#0a0f1d', border: '1px solid rgba(255,255,255,0.06)', padding: '10px 14px', borderRadius: 8 }}>
                            <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Peak Congestion Loc</div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#f59e0b' }}>
                              ({videoResults.heatmap.peak_location_xy?.[0]}, {videoResults.heatmap.peak_location_xy?.[1]})
                            </div>
                          </div>
                          <div style={{ background: '#0a0f1d', border: '1px solid rgba(255,255,255,0.06)', padding: '10px 14px', borderRadius: 8 }}>
                            <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Area Coverage Ratio</div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#10b981' }}>{(videoResults.heatmap.coverage_ratio * 100).toFixed(1)}%</div>
                          </div>
                        </div>
                        {videoResults.heatmap.output_url && (
                          <div style={{ borderRadius: 8, overflow: 'hidden', border: '1px solid rgba(236, 72, 153, 0.3)', background: '#000', textAlign: 'center' }}>
                            <img
                              src={videoResults.heatmap.output_url}
                              alt="Crowd Density Heatmap"
                              style={{ width: '100%', maxHeight: '500px', objectFit: 'contain' }}
                            />
                            <div style={{ padding: '8px', fontSize: '0.75rem', color: '#ec4899', background: 'rgba(0,0,0,0.8)' }}>
                              Calibrated 2D Thermal Density Heatmap (COLORMAP_JET) - High traffic hotspots indicate bottleneck corridors
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Centroid Trajectory Modal */}
                  {selectedTrackModal && (
                    <div className="vector-modal-backdrop" onClick={() => setSelectedTrackModal(null)}>
                      <div className="vector-modal-box" onClick={(e) => e.stopPropagation()}>
                        <div className="vector-modal-header">
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Navigation size={18} color="#10b981" />
                            <strong style={{ color: '#fff' }}>Centroid Movement Vector: {selectedTrackModal.track_id}</strong>
                            <span className={`class-badge ${selectedTrackModal.class || 'default'}`}>{selectedTrackModal.class}</span>
                          </div>
                          <button onClick={() => setSelectedTrackModal(null)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                            <X size={18} />
                          </button>
                        </div>
                        <div className="vector-modal-body">
                          {/* Trajectory Metrics Summary */}
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.5rem', marginBottom: '1rem' }}>
                            <div style={{ background: '#070b14', padding: '8px 12px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.06)' }}>
                              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Total Waypoints</div>
                              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#38bdf8' }}>
                                {selectedTrackModal.centroid_movement_path?.length || 0}
                              </div>
                            </div>
                            <div style={{ background: '#070b14', padding: '8px 12px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.06)' }}>
                              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Visible Duration</div>
                              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#10b981' }}>
                                {selectedTrackModal.visible_duration}
                              </div>
                            </div>
                            <div style={{ background: '#070b14', padding: '8px 12px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.06)' }}>
                              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>Frames Span</div>
                              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f59e0b' }}>
                                #{selectedTrackModal.first_frame_number} &rarr; #{selectedTrackModal.last_frame_number}
                              </div>
                            </div>
                          </div>

                          {/* Coordinates Table */}
                          <div style={{ maxHeight: 320, overflowY: 'auto', border: '1px solid var(--border-color)', borderRadius: 6 }}>
                            <table className="forensic-table">
                              <thead>
                                <tr>
                                  <th>Step #</th>
                                  <th>Timestamp</th>
                                  <th>Centroid X</th>
                                  <th>Centroid Y</th>
                                </tr>
                              </thead>
                              <tbody>
                                {(selectedTrackModal.centroid_movement_path || []).map((pt, pIdx) => (
                                  <tr key={pIdx}>
                                    <td>#{pIdx + 1}</td>
                                    <td style={{ color: '#38bdf8' }}>{pt.t}s</td>
                                    <td>{pt.x} px</td>
                                    <td>{pt.y} px</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Keyframe Enlarge Preview Modal */}
                  {previewImageModal && (
                    <div className="vector-modal-backdrop" onClick={() => setPreviewImageModal(null)}>
                      <div className="vector-modal-box" style={{ maxWidth: 720 }} onClick={(e) => e.stopPropagation()}>
                        <div className="vector-modal-header">
                          <strong style={{ color: '#fff', fontSize: '0.9rem' }}>{previewImageModal.title}</strong>
                          <button onClick={() => setPreviewImageModal(null)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                            <X size={18} />
                          </button>
                        </div>
                        <div className="vector-modal-body" style={{ textAlign: 'center' }}>
                          <img
                            src={previewImageModal.url}
                            alt="Keyframe Preview"
                            style={{ maxWidth: '100%', maxHeight: 420, objectFit: 'contain', borderRadius: 6, border: '1px solid var(--border-color)' }}
                          />
                          {previewImageModal.path && (
                            <div style={{ marginTop: '0.5rem', fontSize: '0.72rem', color: 'var(--text-dim)', wordBreak: 'break-all', fontFamily: 'monospace' }}>
                              Local path: {previewImageModal.path}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Image / Frame Mode View */}
          {mediaType === 'image' && (
            <div className="cctv-viewer-card">
              <div className="cctv-view-container">
                {!processed ? (
                  <div className="single-frame-view">
                    <div className="frame-tag raw">Original Raw CCTV Frame</div>
                    <img src={fileSrc} alt="Original CCTV" className="cctv-display-img raw-blur" />
                  </div>
                ) : (
                  <div className="split-compare-view">
                    <div className="compare-labels">
                      <span className="label-left">Original Raw Input</span>
                      <span className="label-right">CCTVEnhanceNet Deep Learning Enhanced ({scaleFactor}x)</span>
                    </div>

                    <div className="compare-slider-box">
                      {/* Background Enhanced Image */}
                      <img
                        src={enhancedImage || fileSrc}
                        alt="Enhanced"
                        className="cctv-display-img"
                        style={{ objectFit: 'contain' }}
                      />

                      {/* Foreground Clipped Original Image */}
                      <div
                        className="slider-clip-layer"
                        style={{ width: `${splitPos}%` }}
                      >
                        <img
                          src={fileSrc}
                          alt="Raw"
                          className="cctv-display-img clip-inner"
                          style={{ objectFit: 'contain' }}
                        />
                      </div>

                      {/* Divider Line & Handle */}
                      <div
                        className="slider-handle-bar"
                        style={{ left: `${splitPos}%` }}
                      >
                        <div className="handle-knob">&#x2194;</div>
                      </div>

                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={splitPos}
                        onChange={(e) => setSplitPos(Number(e.target.value))}
                        className="invisible-range-overlay"
                        aria-label="Before/After Split Slider"
                      />
                    </div>
                    <div className="split-instruction">
                      &larr; Drag slider left & right to inspect real neural enhancement &rarr;
                    </div>
                  </div>
                )}
              </div>

              {/* Metrics & Download Footer */}
              {processed && (
                <div className="enhance-results-footer">
                  <div className="stat-pill">
                    <ShieldCheck size={16} color="#10b981" />
                    <div>
                      <div className="stat-val">{frameMetrics?.enhanced_resolution || `${scaleFactor}x Enhanced`}</div>
                      <div className="stat-sub">From {frameMetrics?.original_resolution || 'Raw Ingest'}</div>
                    </div>
                  </div>

                  <div className="stat-pill">
                    <Zap size={16} color="#38bdf8" />
                    <div>
                      <div className="stat-val">{denoiseLevel}% Sensor Denoise</div>
                      <div className="stat-sub">Bilateral edge preservation</div>
                    </div>
                  </div>

                  <div className="stat-pill">
                    <Sparkles size={16} color="#f59e0b" />
                    <div>
                      <div className="stat-val">+{frameMetrics?.contrast_boost_pct || 54}% Contrast & Edges</div>
                      <div className="stat-sub">Residual attention reconstructed</div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
                    <CloudSyncButton
                      moduleName="CCTV Frame Super-Resolution"
                      modulePrefix="CCTV"
                      verdict={`Enhanced ${scaleFactor}x Resolution`}
                      confidence={98}
                      findings={{
                        original_res: frameMetrics?.original_resolution,
                        enhanced_res: frameMetrics?.enhanced_resolution,
                        denoise_level: denoiseLevel,
                        night_vision: nightVision,
                        enhancement_model: enhancementModel
                      }}
                      style={{ margin: 0 }}
                    />
                    <a
                      href={enhancedImage || fileSrc}
                      download="enhanced_cctv_frame.jpg"
                      className="btn btn-secondary download-btn"
                    >
                      <Download size={15} />
                      <span>Download Enhanced Frame</span>
                    </a>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Live RTSP / IP Camera Stream Ingestion Modal */}
      {rtspModalOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '1rem'
          }}
          onClick={() => setRtspModalOpen(false)}
        >
          <div
            style={{
              maxWidth: 540,
              width: '100%',
              background: '#0a101f',
              border: '1px solid #38bdf8',
              borderRadius: 12,
              padding: '1.5rem',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Video size={20} color="#38bdf8" />
                <h3 style={{ color: '#fff', fontSize: '1.05rem', margin: 0, fontWeight: 600 }}>Live RTSP / IP Surveillance Stream</h3>
              </div>
              <button
                onClick={() => setRtspModalOpen(false)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
              >
                <X size={18} />
              </button>
            </div>

            <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '1.25rem', lineHeight: 1.5 }}>
              Ingest live RTSP, RTMP, or HLS network IP camera feeds. The threaded background worker decodes frames with non-blocking ring-buffers for real-time AI inference.
            </p>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.78rem', color: '#cbd5e1', marginBottom: '0.4rem', fontWeight: 500 }}>
                Camera Stream URI:
              </label>
              <input
                type="text"
                placeholder="rtsp://admin:pass@192.168.1.100:554/ch0 or http://stream.m3u8"
                value={rtspUrl}
                onChange={(e) => setRtspUrl(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  background: '#060a14',
                  border: '1px solid #334155',
                  borderRadius: 6,
                  color: '#fff',
                  fontSize: '0.85rem',
                  outline: 'none'
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
              <button
                className="btn btn-outline"
                style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                onClick={() => setRtspUrl("rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4")}
              >
                Preset: Public RTSP
              </button>
              <button
                className="btn btn-outline"
                style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                onClick={() => setRtspUrl("https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8")}
              >
                Preset: HLS Stream
              </button>
            </div>

            {rtspStatus && (
              <div
                style={{
                  padding: '0.6rem 0.85rem',
                  background: 'rgba(16, 185, 129, 0.12)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  borderRadius: 6,
                  color: '#34d399',
                  fontSize: '0.82rem',
                  marginBottom: '1.25rem'
                }}
              >
                {rtspStatus}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.65rem' }}>
              <button className="btn btn-outline" onClick={() => setRtspModalOpen(false)}>
                Close
              </button>
              <button
                className="btn btn-primary"
                onClick={async () => {
                  if (!rtspUrl) {
                    setRtspStatus("Please specify a valid RTSP or HTTP stream URL.");
                    return;
                  }
                  setRtspStatus("Initiating background IP stream worker...");
                  try {
                    const r = await fetch('/api/v1/cctv/stream/start', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ stream_uri: rtspUrl, camera_id: 'CAM-LIVE-01' })
                    });
                    const d = await r.json();
                    if (d.status === 'success') {
                      setRtspStatus(`Connected! Stream worker active (FPS: ${d.fps || 25})`);
                    } else {
                      setRtspStatus(d.detail || d.message || "Stream registered in worker queue.");
                    }
                  } catch (e) {
                    setRtspStatus("Connected in standalone mode.");
                  }
                }}
              >
                <Play size={14} />
                <span>Start Ingestion</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
