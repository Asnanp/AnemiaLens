import { useEffect, useRef } from 'react';
import * as THREE from 'three';

// ── Three.js particle background ──────────────────────────────────────────────
export function ThreeBackground() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const renderer = new THREE.WebGLRenderer({ canvas: ref.current, alpha: true, antialias: false });
    // Cap at 1x DPR — biggest single perf win for WebGL
    renderer.setPixelRatio(1);
    renderer.setSize(window.innerWidth, window.innerHeight);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 30;

    const mkPts = (n: number, spread: number, size: number, color: number, opacity: number) => {
      const pos = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) {
        pos[i*3]   = (Math.random()-.5)*spread;
        pos[i*3+1] = (Math.random()-.5)*spread;
        pos[i*3+2] = (Math.random()-.5)*40;
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      return new THREE.Points(g, new THREE.PointsMaterial({ size, color, transparent: true, opacity }));
    };
    // Reduced: 600 + 60 particles (was 1200 + 120)
    const p1 = mkPts(600, 100, 0.06, 0x1a1020, 0.8);
    const p2 = mkPts(60,  80,  0.1,  0xC8001E, 0.3);
    scene.add(p1, p2);

    // Throttled mousemove — only update target, not camera directly
    let mx = 0, my = 0;
    let moveThrottle = 0;
    const onMove = (e: MouseEvent) => {
      const now = Date.now();
      if (now - moveThrottle < 32) return; // ~30fps throttle
      moveThrottle = now;
      mx = (e.clientX/window.innerWidth-.5)*2;
      my = -(e.clientY/window.innerHeight-.5)*2;
    };
    const onResize = () => {
      camera.aspect = window.innerWidth/window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('mousemove', onMove, { passive: true });
    window.addEventListener('resize', onResize, { passive: true });

    let raf: number;
    const tick = () => {
      raf = requestAnimationFrame(tick);
      camera.position.x += (mx*2 - camera.position.x) * 0.02;
      camera.position.y += (my*2 - camera.position.y) * 0.02;
      camera.lookAt(scene.position);
      p1.rotation.y += 0.0002;
      p2.rotation.y -= 0.0004;
      renderer.render(scene, camera);
    };
    tick();
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('resize', onResize);
      renderer.dispose();
    };
  }, []);
  return <canvas ref={ref} style={{ position:'fixed', inset:0, zIndex:0, pointerEvents:'none', opacity:0.5, willChange:'transform' }} />;
}

// ── JS Canvas Aurora — #2 cinematic blobs ─────────────────────────────────────
export function AuroraCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;

    // Render at 0.25x resolution — blobs are blurry anyway, no quality loss
    const SCALE = 0.25;
    let W = window.innerWidth, H = window.innerHeight;
    canvas.width  = Math.floor(W * SCALE);
    canvas.height = Math.floor(H * SCALE);

    const onResize = () => {
      W = window.innerWidth; H = window.innerHeight;
      canvas.width  = Math.floor(W * SCALE);
      canvas.height = Math.floor(H * SCALE);
    };
    window.addEventListener('resize', onResize, { passive: true });

    const sw = () => Math.floor(W * SCALE);
    const sh = () => Math.floor(H * SCALE);

    const blobs = [
      { cx: -0.15, cy: -0.15, rx: 0.35, ry: 0.28, color: '#8B0000', period: 25000, phase: 0,          orbitX: 0.10, orbitY: 0.07 },
      { cx:  1.08, cy:  1.08, rx: 0.30, ry: 0.30, color: '#2D0050', period:-30000, phase: Math.PI,     orbitX: 0.09, orbitY: 0.09 },
      { cx:  0.75, cy:  0.40, rx: 0.22, ry: 0.22, color: '#001040', period: 18000, phase: Math.PI/2,   orbitX: 0,    orbitY: 0    },
    ];

    let raf: number;
    // Throttle to ~30fps — aurora doesn't need 60fps
    let last = 0;
    const draw = (t: number) => {
      raf = requestAnimationFrame(draw);
      if (t - last < 33) return;
      last = t;

      const cw = sw(), ch = sh();
      ctx.clearRect(0, 0, cw, ch);

      blobs.forEach(b => {
        const angle = (t / Math.abs(b.period)) * Math.PI * 2 * Math.sign(b.period) + b.phase;
        const x = (b.cx + Math.cos(angle) * b.orbitX) * cw;
        const y = (b.cy + Math.sin(angle) * b.orbitY) * ch;
        const rx = b.rx * cw, ry = b.ry * ch;

        ctx.save();
        ctx.globalAlpha = 0.5;
        ctx.globalCompositeOperation = 'screen';
        const grad = ctx.createRadialGradient(x, y, 0, x, y, rx);
        grad.addColorStop(0, b.color);
        grad.addColorStop(1, 'transparent');
        ctx.beginPath();
        ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();
        ctx.restore();
      });
    };
    raf = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', onResize); };
  }, []);

  return (
    <canvas
      ref={ref}
      style={{
        position:'fixed', inset:0, zIndex:0, pointerEvents:'none',
        width:'100%', height:'100%',
        // CSS blur is GPU-accelerated and applied once per composite, not per frame
        filter:'blur(60px)',
        willChange:'transform',
      }}
    />
  );
}

// ── Blood Cell Canvas — #4 particle field ─────────────────────────────────────
export function BloodCellCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    const SIZE = 420;
    canvas.width = SIZE; canvas.height = SIZE;
    const CX = SIZE / 2, CY = SIZE / 2;

    type Particle = { x: number; y: number; vx: number; vy: number; r: number; alpha: number; orbit: boolean; angle: number; orbitR: number; speed: number };

    const spawn = (): Particle => {
      const orbit = Math.random() > 0.5;
      if (orbit) {
        const orbitR = 60 + Math.random() * 120;
        const angle = Math.random() * Math.PI * 2;
        return { x: CX + Math.cos(angle) * orbitR, y: CY + Math.sin(angle) * orbitR, vx: 0, vy: 0, r: 2 + Math.random() * 2, alpha: 0.3 + Math.random() * 0.4, orbit: true, angle, orbitR, speed: (Math.random() > 0.5 ? 1 : -1) * (0.003 + Math.random() * 0.005) };
      }
      const angle = Math.random() * Math.PI * 2;
      const speed = 0.15 + Math.random() * 0.3;
      return { x: CX, y: CY, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, r: 1.5 + Math.random() * 2.5, alpha: 0.5 + Math.random() * 0.4, orbit: false, angle: 0, orbitR: 0, speed: 0 };
    };

    // Reduced: 24 particles (was 40)
    const particles: Particle[] = Array.from({ length: 24 }, spawn);

    let raf: number;
    let visible = true;
    const obs = new IntersectionObserver(([e]) => { visible = e.isIntersecting; }, { threshold: 0 });
    obs.observe(canvas);

    const tick = () => {
      raf = requestAnimationFrame(tick);
      if (!visible) return; // pause when scrolled off-screen

      ctx.clearRect(0, 0, SIZE, SIZE);
      // Set shadow once per frame, not per particle
      ctx.shadowBlur = 8;
      ctx.shadowColor = 'rgba(200,0,30,0.6)';

      particles.forEach((p, i) => {
        if (p.orbit) {
          p.angle += p.speed;
          p.x = CX + Math.cos(p.angle) * p.orbitR;
          p.y = CY + Math.sin(p.angle) * p.orbitR;
        } else {
          p.x += p.vx;
          p.y += p.vy;
          const dx = p.x - CX, dy = p.y - CY;
          // Avoid sqrt — compare squared distance
          if (dx*dx + dy*dy > SIZE * SIZE * 0.2) { particles[i] = spawn(); return; }
          p.alpha = Math.max(0, p.alpha - 0.003);
          if (p.alpha <= 0) { particles[i] = spawn(); return; }
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(192,0,26,${p.alpha})`;
        ctx.fill();
      });

      ctx.shadowBlur = 0;
    };
    raf = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(raf); obs.disconnect(); };
  }, []);

  return (
    <canvas
      ref={ref}
      style={{ position:'absolute', inset:0, width:'100%', height:'100%', pointerEvents:'none', zIndex:0, borderRadius:'50%', willChange:'transform' }}
    />
  );
}

// ── Eye Scanner — #5 full upgrade ─────────────────────────────────────────────
const NEURAL_TEXT = 'NEURAL DIAGNOSTICS ACTIVE';

export function EyeScanner() {
  return (
    <div className="eye-wrap animate-float" style={{ filter:'drop-shadow(0 0 80px rgba(200,0,30,0.4))', position:'relative' }}>
      {/* Blood cell particle canvas behind everything */}
      <BloodCellCanvas />

      {/* Extra faint outer rings */}
      <div className="eye-ring-outer" />
      <div className="eye-ring-outer" />

      {/* 5 concentric rings */}
      <div className="eye-ring" />
      <div className="eye-ring" />
      <div className="eye-ring" />
      <div className="eye-ring" />
      <div className="eye-ring" />

      {/* Orbit rings — outer dashed 20s, inner counter 15s */}
      <div className="eye-orbit-outer" style={{ width:'115%', height:'115%' }}>
        <div className="eye-orbit-dot" />
      </div>
      <div className="eye-orbit-outer" style={{ width:'132%', height:'132%' }}>
        <div className="eye-orbit-dot" style={{ background:'rgba(200,0,30,0.5)', boxShadow:'0 0 6px rgba(200,0,30,0.5)' }} />
      </div>

      {/* Crosshairs */}
      <div className="eye-crosshair-h" />
      <div className="eye-crosshair-v" />

      {/* Scan beam */}
      <div className="eye-scan-beam" />

      {/* Center core — radial-gradient + blur + glow */}
      <div className="eye-core" />

      {/* Corner HUD brackets with breathe */}
      {([
        { top:0, left:0, borderTop:'2px solid', borderLeft:'2px solid' },
        { top:0, right:0, borderTop:'2px solid', borderRight:'2px solid' },
        { bottom:0, left:0, borderBottom:'2px solid', borderLeft:'2px solid' },
        { bottom:0, right:0, borderBottom:'2px solid', borderRight:'2px solid' },
      ] as React.CSSProperties[]).map((s, i) => (
        <div key={i} className="eye-bracket" style={{
          position:'absolute', width:20, height:20,
          borderColor:'rgba(200,0,30,0.6)',
          animationDelay: `${i * 0.75}s`,
          ...s
        }} />
      ))}

      {/* HUD label with character flicker */}
      <div style={{
        position:'absolute', bottom:'-3.5rem', left:'50%', transform:'translateX(-50%)',
        textAlign:'center', whiteSpace:'nowrap',
      }}>
        <div className="label-tag" style={{ color:'rgba(242,240,236,0.35)' }}>Scanning Conjunctival ROI</div>
        <div className="label-tag animate-blink" style={{ color:'var(--accent-bright)', marginTop:'0.3rem' }}>
          ●{' '}
          {NEURAL_TEXT.split('').map((ch, i) => (
            <span
              key={i}
              className="neural-text-char"
              style={{ animationDelay: `${(i * 0.15) % 4}s` }}
            >{ch}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
