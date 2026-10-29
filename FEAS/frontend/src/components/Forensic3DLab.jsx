import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import {
  Rotate3d,
  Layers,
  Sparkles,
  Cpu,
  Eye,
  Activity,
  Box,
  Sliders,
  Play,
  Pause,
  RefreshCw
} from 'lucide-react';

export default function Forensic3DLab({ initialMode = 'architecture', onSelectModule }) {
  const mountRef = useRef(null);
  const [activeMode, setActiveMode] = useState(initialMode); // 'architecture' | 'biometrics' | 'tamper' | 'wound'
  const [autoRotate, setAutoRotate] = useState(true);
  const [wireframe, setWireframe] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [elevationLevel, setElevationLevel] = useState(1.4);
  const [prevMode, setPrevMode] = useState(initialMode);

  if (initialMode !== prevMode) {
    setPrevMode(initialMode);
    setActiveMode(initialMode);
  }

  // References for Three.js instance
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const controlsRef = useRef(null);
  const animFrameId = useRef(null);
  const interactiveObjects = useRef([]);
  const dynamicMeshes = useRef([]);

  // Main Three.js Scene Setup & Lifecycle
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 900;
    const height = container.clientHeight || 560;

    // 1. Scene & Camera
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x060913);
    scene.fog = new THREE.FogExp2(0x060913, 0.0035);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    cameraRef.current = camera;
    camera.position.set(0, 45, 95);

    // 2. WebGL Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    rendererRef.current = renderer;
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.25;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 3. Orbit Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controlsRef.current = controls;
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 + 0.1;
    controls.minDistance = 15;
    controls.maxDistance = 220;

    // 4. Lighting Rig
    const ambientLight = new THREE.AmbientLight(0x0f172a, 2.5);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x00f0ff, 2.0);
    dirLight1.position.set(50, 80, 50);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xa855f7, 1.8);
    dirLight2.position.set(-50, 60, -50);
    scene.add(dirLight2);

    const dirLight3 = new THREE.DirectionalLight(0xff3366, 1.5);
    dirLight3.position.set(0, -40, 60);
    scene.add(dirLight3);

    // 5. Ambient Grid Ground Floor
    const gridHelper = new THREE.GridHelper(160, 40, 0x00f0ff, 0x1e293b);
    gridHelper.position.y = -18;
    scene.add(gridHelper);

    // 6. Build Mode Specific 3D Geometry
    buildSceneContent(scene, activeMode);

    // 7. Raycasting for Click / Hover interaction
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onPointerDown = (event) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveObjects.current, true);

      if (intersects.length > 0) {
        let hit = intersects[0].object;
        while (hit && !hit.userData?.isNode && hit.parent) {
          hit = hit.parent;
        }
        if (hit && hit.userData?.nodeData) {
          setSelectedNode(hit.userData.nodeData);
          if (onSelectModule) {
            onSelectModule(hit.userData.nodeData.id);
          }
        }
      }
    };

    renderer.domElement.addEventListener('pointerdown', onPointerDown);

    // 8. Animation Render Loop
    let clock = new THREE.Clock();
    const animate = () => {
      animFrameId.current = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      controls.autoRotate = autoRotate;
      controls.autoRotateSpeed = 1.0;
      controls.update();

      // Dynamic animations for particle streams & pulsing nodes
      dynamicMeshes.current.forEach((obj) => {
        if (obj.userData?.update) {
          obj.userData.update(elapsedTime);
        }
      });

      renderer.render(scene, camera);
    };

    animate();

    // 9. Resize Listener
    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      renderer.domElement.removeEventListener('pointerdown', onPointerDown);
      cancelAnimationFrame(animFrameId.current);
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [activeMode, autoRotate, wireframe, elevationLevel]);

  // Helper: Build 3D objects according to the active mode
  function buildSceneContent(scene, mode) {
    interactiveObjects.current = [];
    dynamicMeshes.current = [];

    // Clear old mode objects (keep lights & grid)
    const objectsToRemove = [];
    scene.children.forEach((child) => {
      if (child.isMesh || child.isPoints || child.isGroup) {
        if (!child.isLight && !(child instanceof THREE.GridHelper)) {
          objectsToRemove.push(child);
        }
      }
    });
    objectsToRemove.forEach((obj) => scene.remove(obj));

    if (mode === 'architecture') {
      buildArchitectureHologram(scene);
    } else if (mode === 'biometrics') {
      buildBiometricFaceMesh(scene);
    } else if (mode === 'tamper') {
      buildTamperTopography(scene);
    } else if (mode === 'wound') {
      buildWoundTissueTopology(scene);
    }
  };

  // =========================================================================
  // SCENE 1: 3D HOLOGRAPHIC ARCHITECTURE PIPELINE
  // Renders the 5 pipeline stages floating in 3D with glowing neon data pipes
  // =========================================================================
  function buildArchitectureHologram(scene) {
    cameraRef.current?.position.set(0, 50, 110);
    controlsRef.current?.target.set(0, 0, 0);

    const stages = [
      {
        id: 'input',
        title: 'Input Layer',
        sub: 'Multi-Modal Intake',
        color: 0x38bdf8,
        pos: new THREE.Vector3(-46, 0, 0),
        desc: 'Suspected Image, 32x32 Face, Wound Photo (JPG/PNG/MP4)',
        stats: '3 Ingestion Streams Active'
      },
      {
        id: 'preprocess',
        title: 'Preprocessing',
        sub: 'Deterministic Pipeline',
        color: 0x10b981,
        pos: new THREE.Vector3(-23, 0, 0),
        desc: 'Resizing, Noise Removal, Normalization, Augmentation, Format Conversion',
        stats: 'FP32 Tensor Conversion @ 224x224'
      },
      {
        id: 'forgery',
        title: '1. Forgery Engine',
        sub: 'VGG16 + YOLOv8',
        color: 0xff3366,
        pos: new THREE.Vector3(3, 14, -12),
        desc: 'Deep feature extraction & bounding-box splicing localization',
        stats: 'Tamper Confidence: 94.2%'
      },
      {
        id: 'diffusion',
        title: '2. Diffusion Face SR',
        sub: 'Diffusers + FaceNet',
        color: 0x00f0ff,
        pos: new THREE.Vector3(3, 0, 0),
        desc: 'Stable Diffusion inpainting (x32 SR) + 512-D identity cosine distance',
        stats: 'Identity Match: 99.4%'
      },
      {
        id: 'wound',
        title: '3. Wound Triage',
        sub: 'EfficientNet-B4',
        color: 0xa855f7,
        pos: new THREE.Vector3(3, -14, 12),
        desc: 'Multi-label clinical classification (Burn, Moderate, 2-3 Days)',
        stats: 'Clinical Severity: 91.2%'
      },
      {
        id: 'fusion',
        title: 'Decision Fusion',
        sub: 'Cryptographic Aggregation',
        color: 0xf59e0b,
        pos: new THREE.Vector3(28, 0, 0),
        desc: 'Cross-module scoring, tamper indexing & forensic report compiler',
        stats: 'SHA-256 Seal Validated'
      },
      {
        id: 'output',
        title: 'Output & Results',
        sub: 'Court-Admissible Dossier',
        color: 0x38bdf8,
        pos: new THREE.Vector3(48, 0, 0),
        desc: 'Red bounding boxes, biometric match, wound classification & PDF dossier',
        stats: 'PDF Dossier Ready for Court'
      }
    ];

    // Create 3D Nodes
    stages.forEach((st) => {
      const group = new THREE.Group();
      group.position.copy(st.pos);
      group.userData = { isNode: true, nodeData: st };

      // Base Pedestal Cylinder
      const cylGeo = new THREE.CylinderGeometry(5.2, 5.8, 1.8, 32);
      const cylMat = new THREE.MeshStandardMaterial({
        color: 0x0b1329,
        roughness: 0.25,
        metalness: 0.85,
        wireframe: wireframe
      });
      const baseMesh = new THREE.Mesh(cylGeo, cylMat);
      group.add(baseMesh);

      // Glowing Neon Accent Ring
      const ringGeo = new THREE.TorusGeometry(5.4, 0.22, 16, 48);
      const ringMat = new THREE.MeshBasicMaterial({ color: st.color });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.rotation.x = Math.PI / 2;
      ringMesh.position.y = 0.9;
      group.add(ringMesh);

      // Holographic Floating Crystal Core
      const coreGeo = new THREE.OctahedronGeometry(2.4, 0);
      const coreMat = new THREE.MeshStandardMaterial({
        color: st.color,
        emissive: st.color,
        emissiveIntensity: 0.65,
        roughness: 0.15,
        metalness: 0.9,
        wireframe: wireframe
      });
      const coreMesh = new THREE.Mesh(coreGeo, coreMat);
      coreMesh.position.y = 4.2;
      group.add(coreMesh);

      // Rotating Orbital Wire Ring
      const orbGeo = new THREE.RingGeometry(3.6, 3.8, 32);
      const orbMat = new THREE.MeshBasicMaterial({ color: st.color, side: THREE.DoubleSide, transparent: true, opacity: 0.5 });
      const orbMesh = new THREE.Mesh(orbGeo, orbMat);
      orbMesh.position.y = 4.2;
      group.add(orbMesh);

      // Dynamic animation for node crystal
      group.userData.update = (time) => {
        coreMesh.rotation.y = time * 0.8;
        coreMesh.rotation.x = Math.sin(time * 0.5) * 0.3;
        coreMesh.position.y = 4.2 + Math.sin(time * 2 + st.pos.x * 0.1) * 0.5;
        orbMesh.rotation.z = -time * 0.6;
        orbMesh.rotation.x = Math.PI / 2 + Math.sin(time * 0.8) * 0.2;
      };

      scene.add(group);
      interactiveObjects.current.push(group);
      dynamicMeshes.current.push(group);
    });

    // Create Data Pipelines (Curved Tubing + Animated Data Particles)
    const connections = [
      ['input', 'preprocess'],
      ['preprocess', 'forgery'],
      ['preprocess', 'diffusion'],
      ['preprocess', 'wound'],
      ['forgery', 'fusion'],
      ['diffusion', 'fusion'],
      ['wound', 'fusion'],
      ['fusion', 'output']
    ];

    connections.forEach(([fromId, toId]) => {
      const fromSt = stages.find((s) => s.id === fromId);
      const toSt = stages.find((s) => s.id === toId);
      if (!fromSt || !toSt) return;

      const p1 = fromSt.pos.clone().add(new THREE.Vector3(0, 2, 0));
      const p2 = toSt.pos.clone().add(new THREE.Vector3(0, 2, 0));
      const mid = p1.clone().lerp(p2, 0.5).add(new THREE.Vector3(0, 4, 0));

      const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
      const tubeGeo = new THREE.TubeGeometry(curve, 32, 0.25, 8, false);
      const tubeMat = new THREE.MeshBasicMaterial({
        color: 0x1e293b,
        transparent: true,
        opacity: 0.45
      });
      const tubeMesh = new THREE.Mesh(tubeGeo, tubeMat);
      scene.add(tubeMesh);

      // Data Particle Pulses
      const particleCount = 14;
      const particleGeo = new THREE.BufferGeometry();
      const posArray = new Float32Array(particleCount * 3);
      particleGeo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));

      const particleMat = new THREE.PointsMaterial({
        color: toSt.color,
        size: 1.4,
        transparent: true,
        blending: THREE.AdditiveBlending
      });
      const particles = new THREE.Points(particleGeo, particleMat);

      particles.userData = {
        update: (time) => {
          const positions = particles.geometry.attributes.position.array;
          for (let i = 0; i < particleCount; i++) {
            const t = (time * 0.4 + i / particleCount) % 1.0;
            const pt = curve.getPoint(t);
            positions[i * 3] = pt.x;
            positions[i * 3 + 1] = pt.y;
            positions[i * 3 + 2] = pt.z;
          }
          particles.geometry.attributes.position.needsUpdate = true;
        }
      };

      scene.add(particles);
      dynamicMeshes.current.push(particles);
    });
  };

  // =========================================================================
  // SCENE 2: 3D BIOMETRIC FACIAL MESH & POINT CLOUD (FaceNet 512-D)
  // =========================================================================
  function buildBiometricFaceMesh(scene) {
    cameraRef.current?.position.set(0, 15, 65);
    controlsRef.current?.target.set(0, 0, 0);

    const rows = 28;
    const cols = 28;
    const geometry = new THREE.PlaneGeometry(36, 44, cols - 1, rows - 1);
    const pos = geometry.attributes.position;

    // Sculpt parametric 3D face ellipsoid with nose, orbits, cheeks, lips
    for (let i = 0; i < pos.count; i++) {
      let x = pos.getX(i);
      let y = pos.getY(i);

      // Oval masking
      const r = Math.sqrt((x / 18) ** 2 + (y / 22) ** 2);
      let z = Math.cos(Math.min(r, 1.2) * (Math.PI / 2.4)) * 14;

      // Nose bridge and tip
      if (Math.abs(x) < 4.2 && y > -4 && y < 8) {
        z += (1 - Math.abs(x) / 4.2) * (8 - Math.abs(y - 2) * 0.8);
      }
      // Eye sockets (recessed)
      if (Math.abs(Math.abs(x) - 7.5) < 3.8 && Math.abs(y - 6.5) < 3.2) {
        z -= 3.2;
      }
      // Cheeks
      if (Math.abs(x) > 6 && Math.abs(x) < 14 && y > -2 && y < 6) {
        z += 2.2;
      }
      // Mouth / Lips
      if (Math.abs(x) < 5.8 && Math.abs(y + 8) < 2.8) {
        z += (1 - Math.abs(x) / 5.8) * 2.8;
      }
      // Chin
      if (Math.abs(x) < 5 && y < -14) {
        z += 3.0;
      }

      pos.setZ(i, z);
    }
    geometry.computeVertexNormals();

    // 1. Wireframe Surface Mesh
    const meshMat = new THREE.MeshStandardMaterial({
      color: 0x00f0ff,
      emissive: 0x052e3d,
      roughness: 0.3,
      metalness: 0.8,
      wireframe: true,
      side: THREE.DoubleSide
    });
    const faceMesh = new THREE.Mesh(geometry, meshMat);
    scene.add(faceMesh);

    // 2. High-Density Biometric Point Cloud (512-D FaceNet anchors)
    const pointsMat = new THREE.PointsMaterial({
      color: 0x38bdf8,
      size: 0.9,
      blending: THREE.AdditiveBlending
    });
    const pointsMesh = new THREE.Points(geometry, pointsMat);
    scene.add(pointsMesh);

    // 3. Key Biometric Landmark Pins
    const landmarks = [
      { name: 'Nose Tip [L0]', pos: new THREE.Vector3(0, 2, 17.5), color: 0xff3366 },
      { name: 'Left Pupil [L1]', pos: new THREE.Vector3(-7.5, 6.5, 9.5), color: 0x00f0ff },
      { name: 'Right Pupil [L2]', pos: new THREE.Vector3(7.5, 6.5, 9.5), color: 0x00f0ff },
      { name: 'Left Lip Corner [L3]', pos: new THREE.Vector3(-5.5, -8, 12), color: 0xa855f7 },
      { name: 'Right Lip Corner [L4]', pos: new THREE.Vector3(5.5, -8, 12), color: 0xa855f7 },
      { name: 'Menton / Chin [L5]', pos: new THREE.Vector3(0, -17, 9), color: 0x10b981 },
      { name: 'Glabella / Forehead [L6]', pos: new THREE.Vector3(0, 16, 12.5), color: 0xf59e0b }
    ];

    landmarks.forEach((lm) => {
      const pinGeo = new THREE.SphereGeometry(0.85, 16, 16);
      const pinMat = new THREE.MeshBasicMaterial({ color: lm.color });
      const pinMesh = new THREE.Mesh(pinGeo, pinMat);
      pinMesh.position.copy(lm.pos);

      // Pulsing halo ring
      const haloGeo = new THREE.RingGeometry(1.2, 1.45, 24);
      const haloMat = new THREE.MeshBasicMaterial({ color: lm.color, side: THREE.DoubleSide, transparent: true, opacity: 0.6 });
      const haloMesh = new THREE.Mesh(haloGeo, haloMat);
      haloMesh.position.copy(lm.pos);
      haloMesh.position.z += 0.2;

      pinMesh.userData = {
        update: (time) => {
          const s = 1.0 + Math.sin(time * 3) * 0.25;
          pinMesh.scale.set(s, s, s);
          haloMesh.scale.set(s * 1.2, s * 1.2, s * 1.2);
        }
      };

      scene.add(pinMesh);
      scene.add(haloMesh);
      dynamicMeshes.current.push(pinMesh);
    });

    // 4. Connecting Geodesic Distance Vector lines
    const lineGeo = new THREE.BufferGeometry().setFromPoints([
      landmarks[1].pos, landmarks[2].pos, // Inter-pupillary distance
      landmarks[0].pos, landmarks[5].pos, // Facial height axis
      landmarks[3].pos, landmarks[4].pos  // Lip width
    ]);
    const lineMat = new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.75, linewidth: 2 });
    const vectorLines = new THREE.LineSegments(lineGeo, lineMat);
    scene.add(vectorLines);
  };

  // =========================================================================
  // SCENE 3: 3D FORGERY TOPOGRAPHY / TAMPER ELEVATION
  // Renders the landscape tampered regions as extruded 3D volcanic peaks
  // =========================================================================
  function buildTamperTopography(scene) {
    cameraRef.current?.position.set(0, 42, 65);
    controlsRef.current?.target.set(0, 0, 0);

    const width = 64;
    const depth = 48;
    const segX = 64;
    const segY = 48;

    const geometry = new THREE.PlaneGeometry(width, depth, segX, segY);
    geometry.rotateX(-Math.PI / 2);

    const pos = geometry.attributes.position;
    const colors = [];

    // Coordinates of Tampered Bounding Box Regions:
    // Box 1: Mountain Peak (Splicing) -> x: ~8, z: ~-12
    // Box 2: Lake Reflection (Altered Inpainting) -> x: ~6, z: ~10
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);

      // Base terrain undulation
      let y = Math.sin(x * 0.12) * Math.cos(z * 0.15) * 1.5;

      // Tamper Peak 1: Mountain Spliced Anomaly
      const d1 = Math.sqrt((x - 8) ** 2 + (z - (-11)) ** 2);
      if (d1 < 10) {
        y += Math.exp(-(d1 ** 2) / 18) * 16 * elevationLevel;
      }

      // Tamper Peak 2: Lake Inpainting Anomaly
      const d2 = Math.sqrt((x - 5) ** 2 + (z - 11) ** 2);
      if (d2 < 8) {
        y += Math.exp(-(d2 ** 2) / 14) * 12 * elevationLevel;
      }

      pos.setY(i, y);

      // Vertex Color: Cyan for authentic flat areas, Crimson Red for tamper anomalies
      if (d1 < 9 || d2 < 7.5) {
        colors.push(1.0, 0.2, 0.4); // Crimson
      } else {
        colors.push(0.0, 0.5, 0.8); // Ambient Cyan / Slate
      }
    }

    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    geometry.computeVertexNormals();

    // 1. Shaded Surface
    const terrainMat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.35,
      metalness: 0.6,
      wireframe: wireframe,
      side: THREE.DoubleSide
    });
    const terrainMesh = new THREE.Mesh(geometry, terrainMat);
    scene.add(terrainMesh);

    // 2. Tamper Radar Bounding Wire Boxes in 3D
    const box1Geo = new THREE.BoxGeometry(16, 18, 14);
    const box1Mat = new THREE.MeshBasicMaterial({ color: 0xff3366, wireframe: true });
    const box1Mesh = new THREE.Mesh(box1Geo, box1Mat);
    box1Mesh.position.set(8, 9, -11);
    scene.add(box1Mesh);

    const box2Geo = new THREE.BoxGeometry(14, 14, 12);
    const box2Mat = new THREE.MeshBasicMaterial({ color: 0xff3366, wireframe: true });
    const box2Mesh = new THREE.Mesh(box2Geo, box2Mat);
    box2Mesh.position.set(5, 7, 11);
    scene.add(box2Mesh);

    // 3. Scanning Laser Line Sweeper
    const scanLineGeo = new THREE.PlaneGeometry(width + 4, 0.8);
    scanLineGeo.rotateX(-Math.PI / 2);
    const scanLineMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.85
    });
    const scanLine = new THREE.Mesh(scanLineGeo, scanLineMat);
    scanLine.position.y = 8;
    scene.add(scanLine);

    scanLine.userData = {
      update: (time) => {
        scanLine.position.z = Math.sin(time * 1.5) * (depth / 2 - 2);
      }
    };
    dynamicMeshes.current.push(scanLine);
  };

  // =========================================================================
  // SCENE 4: 3D TRAUMA TISSUE TOPOLOGY / WOUND DEPTH
  // Renders biological tissue layers with wound crater and erythema halo
  // =========================================================================
  function buildWoundTissueTopology(scene) {
    cameraRef.current?.position.set(0, 38, 55);
    controlsRef.current?.target.set(0, 0, 0);

    const size = 48;
    const segs = 60;
    const geometry = new THREE.PlaneGeometry(size, size, segs, segs);
    geometry.rotateX(-Math.PI / 2);

    const pos = geometry.attributes.position;
    const colors = [];

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      const dist = Math.sqrt(x * x + z * z);

      // Deep crater lesion at center
      let y = 0;
      if (dist < 14) {
        // Deep wound depression
        y = -Math.cos((dist / 14) * (Math.PI / 2)) * 8.5;
        // Irregular wound edges
        y += Math.sin(x * 1.4) * Math.cos(z * 1.4) * 0.9;
      } else if (dist < 18) {
        // Swelling / erythema margin elevation
        y = Math.sin(((dist - 14) / 4) * Math.PI) * 1.8;
      }

      pos.setY(i, y);

      // Color mapping: Necrotic core (dark red/purple) -> Erythema halo (orange/red) -> Healthy tissue (tan)
      if (dist < 7) {
        colors.push(0.35, 0.05, 0.12); // Deep necrotic wound bed
      } else if (dist < 14) {
        colors.push(0.85, 0.15, 0.22); // Active laceration margin
      } else if (dist < 20) {
        colors.push(0.95, 0.45, 0.15); // Inflammatory erythema zone
      } else {
        colors.push(0.2, 0.35, 0.5); // Baseline skin tissue mesh
      }
    }

    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    geometry.computeVertexNormals();

    const woundMat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.4,
      metalness: 0.3,
      wireframe: wireframe,
      side: THREE.DoubleSide
    });
    const woundMesh = new THREE.Mesh(geometry, woundMat);
    scene.add(woundMesh);

    // 3D Depth Ruler / Caliper pins
    const caliperPts = [
      new THREE.Vector3(-12, 1, 0),
      new THREE.Vector3(12, 1, 0)
    ];
    const rulerGeo = new THREE.BufferGeometry().setFromPoints(caliperPts);
    const rulerMat = new THREE.LineBasicMaterial({ color: 0x00f0ff, linewidth: 2 });
    const rulerLine = new THREE.Line(rulerGeo, rulerMat);
    scene.add(rulerLine);

    // Crater depth measurement needle
    const needleGeo = new THREE.CylinderGeometry(0.2, 0.2, 9, 8);
    const needleMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b });
    const needle = new THREE.Mesh(needleGeo, needleMat);
    needle.position.set(0, -4.25, 0);
    scene.add(needle);
  };

  // Quick Camera Presets
  const setCameraPreset = (preset) => {
    if (!cameraRef.current || !controlsRef.current) return;
    if (preset === 'iso') {
      cameraRef.current.position.set(45, 45, 45);
    } else if (preset === 'top') {
      cameraRef.current.position.set(0, 85, 0);
    } else if (preset === 'front') {
      cameraRef.current.position.set(0, 15, 75);
    }
    controlsRef.current.target.set(0, 0, 0);
    controlsRef.current.update();
  };

  const resetLab = () => {
    setSelectedNode(null);
    setAutoRotate(true);
    setWireframe(false);
    setElevationLevel(1.4);
    setCameraPreset('iso');
  };

  return (
    <div className="forensic-3d-lab-wrapper">
      {/* 3D Viewport Navigation Header */}
      <div className="lab-hud-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="pulse-dot pulse-cyan" />
          <span style={{ fontWeight: 800, fontSize: 14, color: '#fff', letterSpacing: 1 }}>
            3D FORENSIC SPATIAL INTELLIGENCE LAB
          </span>
          <span className="badge-mono" style={{ background: 'rgba(0,240,255,0.12)', color: '#00f0ff', borderColor: 'rgba(0,240,255,0.3)' }}>
            THREE.JS WEBGL RENDERER
          </span>
        </div>

        {/* Mode Switcher Tabs */}
        <div className="lab-mode-tabs">
          <button
            onClick={() => setActiveMode('architecture')}
            className={`lab-mode-btn ${activeMode === 'architecture' ? 'active' : ''}`}
          >
            <Rotate3d size={14} />
            <span>3D System Architecture</span>
          </button>
          <button
            onClick={() => setActiveMode('biometrics')}
            className={`lab-mode-btn ${activeMode === 'biometrics' ? 'active' : ''}`}
          >
            <Eye size={14} />
            <span>3D FaceNet Biometrics</span>
          </button>
          <button
            onClick={() => setActiveMode('tamper')}
            className={`lab-mode-btn ${activeMode === 'tamper' ? 'active' : ''}`}
          >
            <Box size={14} />
            <span>3D Tamper Topography</span>
          </button>
          <button
            onClick={() => setActiveMode('wound')}
            className={`lab-mode-btn ${activeMode === 'wound' ? 'active' : ''}`}
          >
            <Activity size={14} />
            <span>3D Trauma Depth</span>
          </button>
        </div>
      </div>

      {/* Main 3D Canvas Viewport */}
      <div className="lab-viewport-container">
        <div ref={mountRef} className="lab-canvas-mount" />

        {/* Viewport Floating HUD Controls (Top Right) */}
        <div className="lab-hud-overlay-controls">
          <button
            onClick={() => setAutoRotate(!autoRotate)}
            className="hud-ctrl-btn"
            title="Toggle 360° Auto-Rotation"
            style={{ color: autoRotate ? '#00f0ff' : '#94a3b8' }}
          >
            {autoRotate ? <Pause size={15} /> : <Play size={15} />}
            <span>{autoRotate ? 'Rotating' : 'Paused'}</span>
          </button>

          <button
            onClick={() => setWireframe(!wireframe)}
            className="hud-ctrl-btn"
            title="Toggle Wireframe Matrix"
            style={{ color: wireframe ? '#10b981' : '#94a3b8' }}
          >
            <Sliders size={15} />
            <span>{wireframe ? 'Wireframe' : 'Shaded'}</span>
          </button>

          <div style={{ display: 'flex', gap: 4 }}>
            <button onClick={() => setCameraPreset('iso')} className="hud-ctrl-btn-mini" title="Isometric Preset">ISO</button>
            <button onClick={() => setCameraPreset('front')} className="hud-ctrl-btn-mini" title="Front Preset">FRONT</button>
            <button onClick={() => setCameraPreset('top')} className="hud-ctrl-btn-mini" title="Top-Down Preset">TOP</button>
            <button onClick={resetLab} className="hud-ctrl-btn-mini" style={{ color: '#f87171' }} title="Reset 3D Lab Scene">RESET</button>
          </div>
        </div>

        {/* Real-time Telemetry Overlay (Bottom Left) */}
        <div className="lab-hud-telemetry">
          <div style={{ color: '#00f0ff', fontWeight: 700, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Cpu size={13} />
            <span>VIEWPORT GPU METRICS</span>
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: 11, lineHeight: 1.5 }}>
            • Mode: <span style={{ color: '#fff', textTransform: 'uppercase' }}>{activeMode}</span><br />
            • Precision: 64-Bit Vertex Shaders<br />
            • Controls: Left Click Orbit • Right Click Pan • Scroll Zoom<br />
            {activeMode === 'tamper' && (
              <div style={{ marginTop: 6 }}>
                <span>Extrusion Scale: </span>
                <input
                  type="range"
                  min="0.5"
                  max="2.5"
                  step="0.1"
                  value={elevationLevel}
                  onChange={(e) => setElevationLevel(parseFloat(e.target.value))}
                  style={{ width: 90, verticalAlign: 'middle', accentColor: '#ff3366' }}
                />
              </div>
            )}
          </div>
        </div>

        {/* Selected 3D Node Detail Card (Bottom Right, if clicked) */}
        {selectedNode && (
          <div className="lab-hud-node-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div style={{ color: '#fff', fontWeight: 800, fontSize: 13 }}>{selectedNode.title}</div>
              <span className="badge-mono" style={{ background: 'rgba(56,189,248,0.2)', color: '#38bdf8', fontSize: 10 }}>
                {selectedNode.sub}
              </span>
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 6 }}>{selectedNode.desc}</div>
            <div style={{ color: '#10b981', fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
              &gt; {selectedNode.stats}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
