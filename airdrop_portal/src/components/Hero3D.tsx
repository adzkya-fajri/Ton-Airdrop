import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

export default function Hero3D() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hasWebGL, setHasWebGL] = useState(true);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let animId: number;
    let renderer: THREE.WebGLRenderer;

    const width = container.clientWidth || 600;
    const height = container.clientHeight || 450;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, 7.5);

    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      setHasWebGL(false);
      return;
    }

    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.appendChild(renderer.domElement);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.55);
    scene.add(ambientLight);

    const mainLight = new THREE.DirectionalLight(0xa78bfa, 2.5);
    mainLight.position.set(5, 6, 5);
    scene.add(mainLight);

    const rimLight = new THREE.DirectionalLight(0x0098ea, 2.0);
    rimLight.position.set(-6, -4, -3);
    scene.add(rimLight);

    const pointLight = new THREE.PointLight(0x8b5cf6, 2, 20);
    pointLight.position.set(0, 2, 4);
    scene.add(pointLight);

    // Star Particle dust
    const particleCount = 200;
    const particleGeom = new THREE.BufferGeometry();
    const pos = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount * 3; i += 3) {
      pos[i] = (Math.random() - 0.5) * 16;
      pos[i + 1] = (Math.random() - 0.5) * 16;
      pos[i + 2] = (Math.random() - 0.5) * 12;
    }
    particleGeom.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0x8b5cf6,
      size: 0.035,
      transparent: true,
      opacity: 0.35
    });
    const particles = new THREE.Points(particleGeom, particleMat);
    scene.add(particles);

    // Generate Official TON Coin Texture (Hi-Res 1024x1024)
    function createOfficialTonCoinTexture(): THREE.CanvasTexture {
      const canvas = document.createElement('canvas');
      canvas.width = 1024;
      canvas.height = 1024;
      const ctx = canvas.getContext('2d')!;

      // TON Blue Background
      ctx.fillStyle = '#0098ea';
      ctx.beginPath();
      ctx.arc(512, 512, 500, 0, Math.PI * 2);
      ctx.fill();

      // Subtle radial shine
      const grad = ctx.createRadialGradient(400, 380, 50, 512, 512, 500);
      grad.addColorStop(0, 'rgba(255, 255, 255, 0.22)');
      grad.addColorStop(0.65, 'rgba(0, 152, 234, 0)');
      grad.addColorStop(1, 'rgba(0, 70, 150, 0.45)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(512, 512, 500, 0, Math.PI * 2);
      ctx.fill();

      // Exact Official TON Emblem
      const topY = 350;
      const bottomY = 710;
      const leftX = 305;
      const rightX = 719;
      const midX = 512;

      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 52;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      // 1. Inverted Triangle Outline
      ctx.beginPath();
      ctx.moveTo(leftX, topY);
      ctx.lineTo(rightX, topY);
      ctx.lineTo(midX, bottomY);
      ctx.closePath();
      ctx.stroke();

      // 2. Center Vertical Divider Line
      ctx.beginPath();
      ctx.moveTo(midX, topY);
      ctx.lineTo(midX, bottomY);
      ctx.stroke();

      const texture = new THREE.CanvasTexture(canvas);
      texture.anisotropy = 16;
      texture.needsUpdate = true;
      return texture;
    }

    const tonTexture = createOfficialTonCoinTexture();

    // Model Group
    const modelGroup = new THREE.Group();

    // Metallic Obsidian Rim
    const rimMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      metalness: 0.95,
      roughness: 0.15
    });

    // Face Material (Double-sided for guaranteed visibility)
    const faceMat = new THREE.MeshStandardMaterial({
      map: tonTexture,
      metalness: 0.35,
      roughness: 0.25,
      side: THREE.DoubleSide
    });

    const coinHolder = new THREE.Group();

    // Rim cylinder
    const rimGeom = new THREE.CylinderGeometry(1.65, 1.65, 0.22, 64);
    const rimMesh = new THREE.Mesh(rimGeom, rimMat);
    rimMesh.rotation.x = Math.PI / 2;
    coinHolder.add(rimMesh);

    // Front Face (facing camera)
    const frontGeom = new THREE.CircleGeometry(1.58, 64);
    const frontMesh = new THREE.Mesh(frontGeom, faceMat);
    frontMesh.position.z = 0.112;
    coinHolder.add(frontMesh);

    // Back Face
    const backGeom = new THREE.CircleGeometry(1.58, 64);
    const backMesh = new THREE.Mesh(backGeom, faceMat);
    backMesh.position.z = -0.112;
    backMesh.rotation.y = Math.PI;
    coinHolder.add(backMesh);

    modelGroup.add(coinHolder);

    // Cincin Orbital 1 (TON Cyan) - Radius 2.45
    const ring1Mat = new THREE.MeshStandardMaterial({
      color: 0x0098ea,
      metalness: 0.95,
      roughness: 0.12
    });
    const ring1Geom = new THREE.TorusGeometry(2.45, 0.045, 16, 64);
    const ring1 = new THREE.Mesh(ring1Geom, ring1Mat);
    modelGroup.add(ring1);

    // Cincin Orbital 2 (Telegram Amethyst Violet) - Radius 2.85
    const ring2Mat = new THREE.MeshStandardMaterial({
      color: 0x7c3aed,
      metalness: 0.95,
      roughness: 0.14
    });
    const ring2Geom = new THREE.TorusGeometry(2.85, 0.04, 16, 64);
    const ring2 = new THREE.Mesh(ring2Geom, ring2Mat);
    ring2.rotation.x = Math.PI / 3;
    modelGroup.add(ring2);

    scene.add(modelGroup);

    // Cursor Parallax Tracker
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouseY = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length > 0) {
        const touch = e.touches[0];
        const rect = container.getBoundingClientRect();
        mouseX = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
        mouseY = -(((touch.clientY - rect.top) / rect.height) * 2 - 1);
      }
    };

    container.addEventListener('mousemove', handleMouseMove);
    container.addEventListener('touchmove', handleTouchMove, { passive: true });

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    const animate = () => {
      animId = requestAnimationFrame(animate);

      // Smooth floating motion
      modelGroup.position.y = Math.sin(Date.now() * 0.002) * 0.12;

      // Cursor Parallax interpolation (smooth damping)
      targetX += (mouseX * 0.35 - targetX) * 0.05;
      targetY += (mouseY * 0.25 - targetY) * 0.05;
      coinHolder.rotation.y = targetX;
      coinHolder.rotation.x = -targetY;

      // Orbital rings dynamic rotation
      ring1.rotation.x += 0.016;
      ring1.rotation.y += 0.009;
      ring2.rotation.y += 0.013;
      ring2.rotation.z += 0.011;

      // Particle idle rotation
      particles.rotation.y += 0.0006;

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      container.removeEventListener('mousemove', handleMouseMove);
      container.removeEventListener('touchmove', handleTouchMove);
      if (renderer && renderer.domElement) {
        container.removeChild(renderer.domElement);
        renderer.dispose();
      }
      particleGeom.dispose();
      particleMat.dispose();
      rimGeom.dispose();
      rimMat.dispose();
      frontGeom.dispose();
      backGeom.dispose();
      faceMat.dispose();
      tonTexture.dispose();
      ring1Geom.dispose();
      ring1Mat.dispose();
      ring2Geom.dispose();
      ring2Mat.dispose();
    };
  }, []);

  return (
    <div className="relative w-full overflow-hidden py-12 md:py-16 px-4 border-b border-obsidian-700 bg-radial-gradient">
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
        {/* Left: Text & Value Prop */}
        <div className="lg:col-span-7 z-10 text-center lg:text-left">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-obsidian-800 border border-obsidian-700 text-xs font-semibold text-amethyst mb-6 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            26 Bot Farmer & Airdrop Terverifikasi
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight mb-4">
            Telegram Web3 <span className="text-transparent bg-clip-text bg-gradient-to-r from-ton via-sky-300 to-amethyst">Airdrop & Mining Hub</span>
          </h1>

          <p className="text-slate-300 text-base sm:text-lg max-w-2xl leading-relaxed mb-8">
            Katalog miner dan MiniApp terbukti membayar di ekosistem The Open Network (TON). Akses langsung seluruh bot terpercaya dengan satu klik cepat dan aman.
          </p>

          <div className="flex flex-wrap gap-4 justify-center lg:justify-start">
            <a
              href="#catalog"
              className="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-amethyst hover:bg-amethyst-hover text-white font-semibold text-sm transition-all duration-150 shadow-lg shadow-amethyst-glow"
            >
              Jelajahi Katalog Airdrop
            </a>
            <div className="inline-flex items-center gap-2 px-4 py-3 rounded-xl bg-obsidian-850 border border-obsidian-700 text-slate-300 text-xs font-medium">
              <span className="text-emerald-400 font-bold">Auto-Payout</span>
              <span>Terhubung Langsung ke Wallet</span>
            </div>
          </div>
        </div>

        {/* Right: Interactive 3D TON Coin Canvas or SVG Fallback */}
        <div className="lg:col-span-5 h-[360px] sm:h-[420px] w-full flex items-center justify-center relative">
          {hasWebGL ? (
            <div
              ref={containerRef}
              className="w-full h-full cursor-grab active:cursor-grabbing flex items-center justify-center"
              aria-label="Interactive 3D TON Coin"
            />
          ) : (
            <div className="flex flex-col items-center justify-center gap-4 p-8 rounded-2xl bg-obsidian-850 border border-obsidian-700">
              <div className="w-32 h-32 rounded-full bg-ton flex items-center justify-center shadow-2xl shadow-ton/30">
                <svg viewBox="0 0 100 100" className="w-20 h-20">
                  <path d="M 30 35 L 70 35 L 50 72 Z" fill="none" stroke="#ffffff" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
                  <line x1="50" y1="35" x2="50" y2="72" stroke="#ffffff" strokeWidth="5" strokeLinecap="round"/>
                </svg>
              </div>
              <span className="text-xs font-semibold text-slate-400">Official TON Coin</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
