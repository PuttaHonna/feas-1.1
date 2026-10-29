import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { Eye, Shield, Cpu, RefreshCw, Box } from "lucide-react";

/**
 * ForensicScene3D: Interactive Three.js 3D viewport for evidence inspection,
 * holographic latent space visualization, and tamper-scanning grids.
 */
export default function ForensicScene3D({ activeMode = "vault", statusText = "SECURE VAULT MESH" }) {
  const containerRef = useRef(null);
  const [viewMode, setViewMode] = useState(activeMode); // 'vault' | 'latent' | 'scanner'
  const [hudStats, setHudStats] = useState({ nodes: 640, fps: 60, rot: "0.00" });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Scene, Camera, Renderer
    const width = container.clientWidth || 400;
    const height = container.clientHeight || 260;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, 7.5);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Group for objects
    const mainGroup = new THREE.Group();
    scene.add(mainGroup);

    // 1. Vault Mesh: Icosahedron wireframe with inner glowing core
    const icoGeo = new THREE.IcosahedronGeometry(2.0, 1);
    const icoMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.55,
    });
    const icoMesh = new THREE.Mesh(icoGeo, icoMat);
    mainGroup.add(icoMesh);

    // Inner core sphere
    const coreGeo = new THREE.SphereGeometry(0.9, 16, 16);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x0284c7,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    mainGroup.add(coreMesh);

    // 2. Latent Space Particles (512-D projection representation)
    const particleCount = 480;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      const radius = 2.4 + Math.random() * 1.6;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);

      // Cyan-blue-emerald gradient
      colors[i * 3] = 0.2 + Math.random() * 0.3;
      colors[i * 3 + 1] = 0.7 + Math.random() * 0.3;
      colors[i * 3 + 2] = 0.9;
    }

    particleGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    particleGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const particleMat = new THREE.PointsMaterial({
      size: 0.05,
      vertexColors: true,
      transparent: true,
      opacity: 0.75,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    mainGroup.add(particles);

    // 3. Laser Scanner Ring
    const ringGeo = new THREE.RingGeometry(2.3, 2.38, 64);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x34d399,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.8,
    });
    const scanRing = new THREE.Mesh(ringGeo, ringMat);
    scanRing.rotation.x = Math.PI / 2;
    mainGroup.add(scanRing);

    // 4. Outer Orbital Grid Ring
    const orbitGeo = new THREE.TorusGeometry(3.2, 0.015, 12, 100);
    const orbitMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.25,
    });
    const orbitMesh = new THREE.Mesh(orbitGeo, orbitMat);
    mainGroup.add(orbitMesh);

    // Mouse Tracking for subtle parallax
    let mouseX = 0, mouseY = 0;
    let targetX = 0, targetY = 0;

    const handleMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
      targetX = x * 0.5;
      targetY = y * 0.5;
    };

    container.addEventListener("mousemove", handleMouseMove);

    // Resize Handler
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener("resize", handleResize);

    // Animation Loop
    let animId;
    let clock = new THREE.Clock();
    let scanDirection = 1;
    let frameCount = 0;
    let lastFpsTime = performance.now();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Smooth mouse easing
      mouseX += (targetX - mouseX) * 0.05;
      mouseY += (targetY - mouseY) * 0.05;

      mainGroup.rotation.y = elapsedTime * 0.35 + mouseX;
      mainGroup.rotation.x = Math.sin(elapsedTime * 0.25) * 0.2 + mouseY;

      // Scan ring sweep
      scanRing.position.y += 0.02 * scanDirection;
      if (scanRing.position.y > 2.2) scanDirection = -1;
      if (scanRing.position.y < -2.2) scanDirection = 1;

      // Particle subtle expansion/breathing
      particles.rotation.y = -elapsedTime * 0.15;
      orbitMesh.rotation.z = elapsedTime * 0.2;

      // Mode adaptations
      if (viewMode === "vault") {
        icoMesh.visible = true;
        coreMesh.visible = true;
        particles.visible = true;
        scanRing.visible = true;
        icoMat.color.setHex(0x38bdf8);
      } else if (viewMode === "latent") {
        icoMesh.visible = false;
        coreMesh.visible = false;
        particles.visible = true;
        scanRing.visible = false;
        particleMat.size = 0.08;
      } else if (viewMode === "scanner") {
        icoMesh.visible = true;
        coreMesh.visible = false;
        particles.visible = false;
        scanRing.visible = true;
        icoMat.color.setHex(0xf59e0b);
      }

      renderer.render(scene, camera);

      // FPS calculation & stats
      frameCount++;
      const now = performance.now();
      if (now - lastFpsTime >= 500) {
        const curFps = Math.round((frameCount * 1000) / (now - lastFpsTime));
        setHudStats({
          nodes: particleCount,
          fps: Math.min(curFps, 60),
          rot: (mainGroup.rotation.y % (Math.PI * 2)).toFixed(2),
        });
        frameCount = 0;
        lastFpsTime = now;
      }
    };

    animate();

    // Cleanup
    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
      container.removeEventListener("mousemove", handleMouseMove);
      if (renderer.domElement && renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
      renderer.dispose();
      icoGeo.dispose();
      icoMat.dispose();
      coreGeo.dispose();
      coreMat.dispose();
      particleGeo.dispose();
      particleMat.dispose();
      ringGeo.dispose();
      ringMat.dispose();
      orbitGeo.dispose();
      orbitMat.dispose();
    };
  }, [viewMode]);

  return (
    <div style={{
      position: "relative",
      width: "100%",
      height: "260px",
      borderRadius: "14px",
      overflow: "hidden",
      background: "radial-gradient(circle at center, rgba(14,23,42,0.85) 0%, rgba(9,14,26,0.95) 100%)",
      border: "1px solid rgba(56,189,248,0.25)",
      boxShadow: "0 10px 30px rgba(0,0,0,0.5), inset 0 0 40px rgba(56,189,248,0.06)",
      marginBottom: "20px"
    }}>
      {/* 3D WebGL Canvas Container */}
      <div ref={containerRef} style={{ width: "100%", height: "100%", cursor: "grab" }} />

      {/* Top HUD Overlay */}
      <div style={{
        position: "absolute",
        top: 12,
        left: 16,
        right: 16,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        pointerEvents: "none",
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          background: "rgba(15, 23, 42, 0.75)",
          backdropFilter: "blur(8px)",
          padding: "4px 10px",
          borderRadius: "8px",
          border: "1px solid rgba(56, 189, 248, 0.3)",
          color: "#7dd3fc",
          fontSize: "11px",
          fontFamily: "'Space Grotesk', monospace",
          letterSpacing: "0.06em",
        }}>
          <Shield size={13} color="#38bdf8" />
          <span>THREE.JS FORENSIC VIEWPORT · {statusText}</span>
        </div>

        {/* View mode toggle buttons */}
        <div style={{ display: "flex", gap: 6, pointerEvents: "auto" }}>
          <button
            onClick={() => setViewMode("vault")}
            style={{
              background: viewMode === "vault" ? "rgba(56,189,248,0.25)" : "rgba(15,23,42,0.8)",
              border: `1px solid ${viewMode === "vault" ? "#38bdf8" : "rgba(255,255,255,0.1)"}`,
              color: viewMode === "vault" ? "#e0f2fe" : "#94a3b8",
              padding: "4px 8px",
              borderRadius: "6px",
              fontSize: "10px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <Box size={11} /> Vault
          </button>
          <button
            onClick={() => setViewMode("latent")}
            style={{
              background: viewMode === "latent" ? "rgba(56,189,248,0.25)" : "rgba(15,23,42,0.8)",
              border: `1px solid ${viewMode === "latent" ? "#38bdf8" : "rgba(255,255,255,0.1)"}`,
              color: viewMode === "latent" ? "#e0f2fe" : "#94a3b8",
              padding: "4px 8px",
              borderRadius: "6px",
              fontSize: "10px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <Cpu size={11} /> 512D Latent
          </button>
          <button
            onClick={() => setViewMode("scanner")}
            style={{
              background: viewMode === "scanner" ? "rgba(245,158,11,0.25)" : "rgba(15,23,42,0.8)",
              border: `1px solid ${viewMode === "scanner" ? "#f59e0b" : "rgba(255,255,255,0.1)"}`,
              color: viewMode === "scanner" ? "#fef3c7" : "#94a3b8",
              padding: "4px 8px",
              borderRadius: "6px",
              fontSize: "10px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <Eye size={11} /> Scan Grid
          </button>
        </div>
      </div>

      {/* Bottom HUD Telemetry */}
      <div style={{
        position: "absolute",
        bottom: 10,
        left: 16,
        right: 16,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        pointerEvents: "none",
        fontSize: "10px",
        color: "#64748b",
        fontFamily: "'Space Grotesk', monospace",
      }}>
        <div>NODES: <span style={{ color: "#38bdf8" }}>{hudStats.nodes}</span> | ROT_Y: <span style={{ color: "#38bdf8" }}>{hudStats.rot} rad</span></div>
        <div>RENDERER: <span style={{ color: "#34d399" }}>WEBGL2 ({hudStats.fps} FPS)</span></div>
      </div>
    </div>
  );
}
