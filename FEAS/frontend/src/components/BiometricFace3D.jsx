import React, { useEffect, useRef, useState } from 'react';
import { Rotate3d, Compass, Eye, ShieldCheck, Sparkles } from 'lucide-react';

/**
 * 3D Biometric Facial Topology Mesh & Point Cloud Canvas
 * Renders an interactive 3D rotatable facial wireframe with FaceNet 512-d biometric anchors.
 */
export default function BiometricFace3D({ embedding = [], subjectName = 'Subject Evidence #01', similarity = 0.88 }) {
  const canvasRef = useRef(null);
  const [rotX, setRotX] = useState(0.2);
  const [rotY, setRotY] = useState(0.3);
  const [isDragging, setIsDragging] = useState(false);
  const [autoRotate, setAutoRotate] = useState(true);
  const dragStart = useRef({ x: 0, y: 0 });

  // Generate 3D wireframe mesh points for human face
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;
    let currentY = rotY;

    // Canonical 3D face mesh anchors (u, v ellipsoidal grid + nose + eyes + mouth)
    const points = [];
    const rows = 14;
    const cols = 14;

    for (let i = 0; i < rows; i++) {
      const u = (i / (rows - 1) - 0.5) * Math.PI;
      for (let j = 0; j < cols; j++) {
        const v = (j / (cols - 1) - 0.5) * Math.PI;
        let x = 110 * Math.cos(u) * Math.cos(v);
        let y = 140 * Math.sin(u);
        let z = 95 * Math.cos(u) * Math.sin(v);

        // Perturb based on embedding if present
        const embIdx = (i * cols + j) % (embedding.length || 64);
        const embVal = embedding[embIdx] !== undefined ? embedding[embIdx] : Math.sin(i * 0.5 + j * 0.3) * 0.3;
        z += embVal * 30;

        // Nose protrusion
        if (Math.abs(y) < 30 && Math.abs(x) < 25) {
          z += 35;
        }

        points.push({ x, y, z, i, j });
      }
    }

    // Key biometric landmarks
    const landmarks = [
      { name: 'L-Eye', x: -38, y: 24, z: 28, color: '#00f0ff' },
      { name: 'R-Eye', x: 38, y: 24, z: 28, color: '#00f0ff' },
      { name: 'Nose Tip', x: 0, y: -2, z: 62, color: '#ff3366' },
      { name: 'L-Mouth', x: -28, y: -45, z: 32, color: '#a855f7' },
      { name: 'R-Mouth', x: 28, y: -45, z: 32, color: '#a855f7' },
      { name: 'Chin', x: 0, y: -90, z: 18, color: '#10b981' },
      { name: 'Forehead', x: 0, y: 85, z: 20, color: '#38bdf8' },
    ];

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (autoRotate && !isDragging) {
        currentY += 0.008;
      }

      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const fov = 400;

      // Projection helper
      const project = (pt) => {
        // Rotate around Y
        const cosY = Math.cos(currentY);
        const sinY = Math.sin(currentY);
        const x1 = pt.x * cosY + pt.z * sinY;
        const z1 = -pt.x * sinY + pt.z * cosY;

        // Rotate around X
        const cosX = Math.cos(rotX);
        const sinX = Math.sin(rotX);
        const y2 = pt.y * cosX - z1 * sinX;
        const z2 = pt.y * sinX + z1 * cosX;

        const depth = z2 + 300;
        const scale = fov / Math.max(1, depth);
        return {
          px: centerX + x1 * scale,
          py: centerY - y2 * scale,
          scale,
          depth,
        };
      };

      // Draw Wireframe Lines
      ctx.lineWidth = 1;
      for (let i = 0; i < points.length; i++) {
        const pt1 = points[i];
        const pr1 = project(pt1);

        // Connect to right neighbor
        if (pt1.j < cols - 1) {
          const ptRight = points[i + 1];
          const prRight = project(ptRight);
          ctx.strokeStyle = `rgba(0, 240, 255, ${Math.max(0.1, 0.45 - pr1.depth / 800)})`;
          ctx.beginPath();
          ctx.moveTo(pr1.px, pr1.py);
          ctx.lineTo(prRight.px, prRight.py);
          ctx.stroke();
        }

        // Connect to down neighbor
        if (pt1.i < rows - 1) {
          const ptDown = points[i + cols];
          const prDown = project(ptDown);
          ctx.strokeStyle = `rgba(56, 189, 248, ${Math.max(0.08, 0.35 - pr1.depth / 800)})`;
          ctx.beginPath();
          ctx.moveTo(pr1.px, pr1.py);
          ctx.lineTo(prDown.px, prDown.py);
          ctx.stroke();
        }

        // Draw Point Node
        ctx.fillStyle = pt1.j % 2 === 0 ? 'rgba(0, 240, 255, 0.6)' : 'rgba(168, 85, 247, 0.5)';
        ctx.beginPath();
        ctx.arc(pr1.px, pr1.py, Math.max(1, pr1.scale * 1.5), 0, Math.PI * 2);
        ctx.fill();
      }

      // Draw Biometric Anchor Nodes
      landmarks.forEach((lm) => {
        const pr = project(lm);
        ctx.fillStyle = lm.color;
        ctx.shadowColor = lm.color;
        ctx.shadowBlur = 10;
        ctx.beginPath();
        ctx.arc(pr.px, pr.py, 4.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;

        // Label
        ctx.font = '10px "JetBrains Mono", monospace';
        ctx.fillStyle = '#f8fafc';
        ctx.fillText(lm.name, pr.px + 7, pr.py - 3);
      });

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => cancelAnimationFrame(animationId);
  }, [rotX, rotY, autoRotate, isDragging, embedding]);

  // Mouse interaction for orbit controls
  const handleMouseDown = (e) => {
    setIsDragging(true);
    setAutoRotate(false);
    dragStart.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStart.current.x;
    const dy = e.clientY - dragStart.current.y;
    setRotY((prev) => prev + dx * 0.008);
    setRotX((prev) => Math.max(-1.2, Math.min(1.2, prev + dy * 0.008)));
    dragStart.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseUp = () => setIsDragging(false);

  return (
    <div className="hud-card" style={{ position: 'relative' }}>
      <div className="hud-card-accent-top" />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Rotate3d size={18} color="#00f0ff" />
            <span>3D Biometric Facial Topology Mesh</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            FaceNet 512-D Canonical Coordinate Projection
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => setAutoRotate(!autoRotate)}
            className="btn-outline"
            style={{ padding: '4px 10px', fontSize: 11 }}
          >
            <Compass size={12} /> {autoRotate ? 'Pause Orbit' : 'Auto Rotate'}
          </button>
        </div>
      </div>

      <div
        style={{
          position: 'relative',
          background: 'linear-gradient(180deg, #060a14 0%, #03060c 100%)',
          borderRadius: 12,
          border: '1px solid rgba(56, 189, 248, 0.2)',
          cursor: isDragging ? 'grabbing' : 'grab',
          overflow: 'hidden',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <canvas ref={canvasRef} width={540} height={340} style={{ maxWidth: '100%', display: 'block' }} />

        {/* HUD Overlay telemetry on canvas */}
        <div style={{ position: 'absolute', top: 12, left: 12, fontFamily: 'var(--font-mono)', fontSize: 10, color: '#00f0ff', background: 'rgba(0,0,0,0.6)', padding: '4px 8px', borderRadius: 4, border: '1px solid rgba(0,240,255,0.3)' }}>
          ROT_Y: {(rotY % (Math.PI * 2)).toFixed(2)} rad • 196 SURFACE NODES
        </div>

        <div style={{ position: 'absolute', bottom: 12, right: 12, fontFamily: 'var(--font-mono)', fontSize: 11, color: '#10b981', background: 'rgba(0,0,0,0.6)', padding: '4px 10px', borderRadius: 4, border: '1px solid #10b981' }}>
          CONFIDENCE: {(similarity * 100).toFixed(1)}%
        </div>
      </div>

      <div style={{ marginTop: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, color: 'var(--text-muted)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Eye size={14} color="#00f0ff" />
          <span>Subject: <strong style={{ color: '#fff' }}>{subjectName}</strong></span>
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#a855f7' }}>
          DRAG MOUSE TO ORBIT 3D PERSPECTIVE
        </div>
      </div>
    </div>
  );
}
