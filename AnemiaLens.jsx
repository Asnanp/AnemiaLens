import { useState, useEffect, useRef, useCallback } from "react";
import * as THREE from "three";
import { motion, AnimatePresence, useScroll, useTransform, useSpring } from "framer-motion";
import {
  LucideActivity, LucideShieldCheck, LucideCamera, LucideZap,
  LucideBrain, LucideMessageSquare, LucideChevronRight, LucideCheckCircle2,
  LucideDownload, LucideHeartPulse, LucideGlobe, LucideMicroscope,
  LucideStethoscope, LucideShare2, LucideLock, LucideArrowRight,
  LucideScanEye, LucideWifi, LucideShield
} from "lucide-react";

// ─── GLOBAL STYLES ───────────────────────────────────────────────────────────
const G = `
@import url('https://fonts.googleapis.com/css2?family=Barlow:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,300;1,400&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  --bg:        #03030A;
  --surface:   #07070F;
  --crimson:   #C8102E;
  --accent:    #E8294A;
  --accent2:   #FF6B8A;
  --glow:      rgba(200,16,46,0.35);
  --glow2:     rgba(232,41,74,0.2);
  --g0:        rgba(255,255,255,0.0);
  --g1:        rgba(255,255,255,0.03);
  --g2:        rgba(255,255,255,0.06);
  --g3:        rgba(255,255,255,0.10);
  --g4:        rgba(255,255,255,0.16);
  --b1:        rgba(255,255,255,0.04);
  --b2:        rgba(255,255,255,0.08);
  --b3:        rgba(255,255,255,0.14);
  --white:     #F5F5F7;
  --t1:        rgba(245,245,247,0.85);
  --t2:        rgba(245,245,247,0.55);
  --t3:        rgba(245,245,247,0.30);
  --t4:        rgba(245,245,247,0.15);
  --serif:     'Cormorant Garamond', Georgia, serif;
  --sans:      'Barlow', system-ui, sans-serif;
  --mono:      'IBM Plex Mono', monospace;
  --ease-out:  cubic-bezier(0.22, 1, 0.36, 1);
  --ease-in:   cubic-bezier(0.64, 0, 0.78, 0);
  --ease-io:   cubic-bezier(0.65, 0, 0.35, 1);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; -webkit-font-smoothing: antialiased; background: var(--bg); }
body { background: var(--bg); color: var(--white); font-family: var(--sans); overflow-x: hidden; }

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--g3); border-radius: 99px; }

/* ── GLASS SYSTEM ── */
.glass {
  background: linear-gradient(135deg, var(--g2) 0%, var(--g1) 100%);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--b2);
  border-radius: 1.5rem;
  position: relative;
  overflow: hidden;
}
.glass::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,0.06) 0%, transparent 60%);
  border-radius: inherit;
  pointer-events: none;
}
.glass-hover {
  transition: all 0.4s var(--ease-out);
  cursor: pointer;
}
.glass-hover:hover {
  background: linear-gradient(135deg, var(--g3) 0%, var(--g2) 100%);
  border-color: var(--b3);
  box-shadow: 0 24px 60px rgba(0,0,0,0.5), 0 0 0 1px var(--b2), inset 0 1px 0 rgba(255,255,255,0.08);
  transform: translateY(-3px);
}

/* ── GLOW ORBS ── */
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  z-index: 0;
}

/* ── BUTTONS ── */
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 0.6rem;
  padding: 0.9rem 2rem; border-radius: 0.875rem; font-weight: 700;
  font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase;
  border: none; cursor: pointer; transition: all 0.3s var(--ease-out);
  position: relative; overflow: hidden; font-family: var(--sans);
}
.btn::after {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(135deg, rgba(255,255,255,0.12) 0%, transparent 60%);
  opacity: 0; transition: opacity 0.3s;
}
.btn:hover::after { opacity: 1; }
.btn-red {
  background: linear-gradient(135deg, var(--crimson) 0%, var(--accent) 100%);
  color: #fff;
  box-shadow: 0 8px 24px var(--glow), 0 0 0 1px rgba(200,16,46,0.3);
}
.btn-red:hover {
  box-shadow: 0 12px 36px var(--glow), 0 0 0 1px rgba(232,41,74,0.5), 0 0 60px rgba(200,16,46,0.2);
  transform: translateY(-2px);
}
.btn-ghost {
  background: var(--g2);
  color: var(--t1);
  border: 1px solid var(--b2);
  backdrop-filter: blur(12px);
}
.btn-ghost:hover {
  background: var(--g3);
  border-color: var(--b3);
  transform: translateY(-2px);
}

/* ── SCAN BEAM ── */
@keyframes scan { 0%,100%{top:-2px;opacity:0} 5%,95%{opacity:1} 50%{top:calc(100% + 2px)} }
@keyframes scanH { 0%,100%{left:-2px;opacity:0} 5%,95%{opacity:1} 50%{left:calc(100% + 2px)} }
@keyframes pulse-ring { 0%{transform:scale(1);opacity:0.6} 100%{transform:scale(1.8);opacity:0} }
@keyframes float { 0%,100%{transform:translateY(0px)} 50%{transform:translateY(-12px)} }
@keyframes spin-slow { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
@keyframes spin-rev { from{transform:rotate(360deg)} to{transform:rotate(0deg)} }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
@keyframes marquee { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
@keyframes shimmer { 0%{background-position:-200% 0} 100%{background-position:200% 0} }
@keyframes data-flow { 0%{opacity:0;transform:translateY(8px)} 20%{opacity:1;transform:translateY(0)} 80%{opacity:1} 100%{opacity:0;transform:translateY(-8px)} }
@keyframes glow-pulse { 0%,100%{box-shadow:0 0 20px var(--glow)} 50%{box-shadow:0 0 50px var(--glow),0 0 100px rgba(200,16,46,0.15)} }
@keyframes border-flow {
  0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%}
}

/* ── NOISE TEXTURE ── */
.noise::after {
  content: '';
  position: absolute; inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events: none; border-radius: inherit; z-index: 1;
}

/* ── GRADIENT TEXT ── */
.grad-text {
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ── PROGRESS BAR ── */
.progress-track { height: 3px; background: var(--g2); border-radius: 99px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 99px; transition: width 1.2s var(--ease-out); }

/* ── ANIMATED BORDER ── */
.animated-border {
  position: relative;
}
.animated-border::before {
  content: '';
  position: absolute; inset: -1px;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--crimson), var(--accent), var(--accent2), var(--crimson));
  background-size: 300% 300%;
  animation: border-flow 4s ease infinite;
  z-index: -1;
}

/* ── TILT CARD ── */
.tilt-card { transform-style: preserve-3d; transition: transform 0.1s ease; }

/* ── REDUCED MOTION ── */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
`;

// ─── THREE.JS BACKGROUND ─────────────────────────────────────────────────────
function Background({ canvasRef }) {
  useEffect(() => {
    if (!canvasRef.current) return;
    const renderer = new THREE.WebGLRenderer({ canvas: canvasRef.current, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 30;

    // Particles — two layers: dim base + red accent
    const mkParticles = (count, spread, size, color, opacity) => {
      const pos = new Float32Array(count * 3);
      for (let i = 0; i < count; i++) {
        pos[i*3]   = (Math.random()-0.5)*spread;
        pos[i*3+1] = (Math.random()-0.5)*spread;
        pos[i*3+2] = (Math.random()-0.5)*40;
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      return new THREE.Points(geo, new THREE.PointsMaterial({ size, color, transparent: true, opacity }));
    };
    const p1 = mkParticles(1400, 90, 0.07, 0x1a1a22, 0.7);
    const p2 = mkParticles(180, 70, 0.12, 0xC8102E, 0.4);
    scene.add(p1, p2);

    // Grid lines
    const gridPts = [];
    for (let i = -30; i <= 30; i += 5) {
      gridPts.push(-70, i, -25, 70, i, -25);
      gridPts.push(i*2.3, -70, -25, i*2.3, 70, -25);
    }
    const gridGeo = new THREE.BufferGeometry();
    gridGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(gridPts), 3));
    scene.add(new THREE.LineSegments(gridGeo, new THREE.LineBasicMaterial({ color: 0x0d0d14, transparent: true, opacity: 0.5 })));

    let mx = 0, my = 0;
    const onMove = e => { mx = (e.clientX/window.innerWidth-0.5)*2; my = -(e.clientY/window.innerHeight-0.5)*2; };
    const onResize = () => { camera.aspect = window.innerWidth/window.innerHeight; camera.updateProjectionMatrix(); renderer.setSize(window.innerWidth, window.innerHeight); };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('resize', onResize);

    let raf;
    const animate = () => {
      raf = requestAnimationFrame(animate);
      camera.position.x += (mx*2.5 - camera.position.x)*0.025;
      camera.position.y += (my*2.5 - camera.position.y)*0.025;
      camera.lookAt(scene.position);
      p1.rotation.y += 0.0003;
      p2.rotation.y -= 0.0006;
      renderer.render(scene, camera);
    };
    animate();
    return () => { cancelAnimationFrame(raf); window.removeEventListener('mousemove', onMove); window.removeEventListener('resize', onResize); renderer.dispose(); };
  }, [canvasRef]);

  return <canvas ref={canvasRef} style={{ position:'fixed', inset:0, zIndex:0, pointerEvents:'none' }} />;
}

// ─── THREE.JS EYE ─────────────────────────────────────────────────────────────
function EyeScanner({ canvasRef }) {
  useEffect(() => {
    if (!canvasRef.current) return;
    const W = 480, H = 480;
    const renderer = new THREE.WebGLRenderer({ canvas: canvasRef.current, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(W, H);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    camera.position.z = 5.5;

    scene.add(new THREE.AmbientLight(0xffffff, 0.25));
    const pl1 = new THREE.PointLight(0xffffff, 2, 18); pl1.position.set(5, 4, 6); scene.add(pl1);
    const pl2 = new THREE.PointLight(0xC8102E, 1.8, 12); pl2.position.set(-4, -3, 5); scene.add(pl2);
    const pl3 = new THREE.PointLight(0x4040ff, 0.6, 10); pl3.position.set(0, 5, 3); scene.add(pl3);

    // Eyeball
    const globe = new THREE.Mesh(
      new THREE.SphereGeometry(1.7, 96, 96),
      new THREE.MeshPhongMaterial({ color: 0x080810, emissive: 0x040408, shininess: 200, specular: 0x404060 })
    );
    scene.add(globe);

    // Iris rings — gradient from red to dark
    for (let i = 0; i < 10; i++) {
      const t = i / 9;
      const col = new THREE.Color().lerpColors(new THREE.Color(0xC8102E), new THREE.Color(0x0a0a14), t);
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(0.22 + i*0.18, 0.006 + (i<3?0.003:0), 16, 140),
        new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.15 + (1-t)*0.35 })
      );
      ring.rotation.x = Math.PI/2;
      scene.add(ring);
    }

    // Pupil
    const pupil = new THREE.Mesh(new THREE.CircleGeometry(0.52, 80), new THREE.MeshBasicMaterial({ color: 0x000000 }));
    pupil.position.z = 1.68;
    scene.add(pupil);

    // Cornea gloss
    const cornea = new THREE.Mesh(
      new THREE.SphereGeometry(1.72, 64, 64),
      new THREE.MeshPhongMaterial({ color: 0x000000, transparent: true, opacity: 0.0, shininess: 400, specular: 0xffffff })
    );
    scene.add(cornea);

    // Scan beam
    const beam = new THREE.Mesh(
      new THREE.PlaneGeometry(4, 0.04),
      new THREE.MeshBasicMaterial({ color: 0xE8294A, transparent: true, opacity: 0.7, side: THREE.DoubleSide })
    );
    scene.add(beam);

    // Scan beam glow (wider, dimmer)
    const beamGlow = new THREE.Mesh(
      new THREE.PlaneGeometry(4, 0.3),
      new THREE.MeshBasicMaterial({ color: 0xC8102E, transparent: true, opacity: 0.12, side: THREE.DoubleSide })
    );
    scene.add(beamGlow);

    let raf, t = 0;
    const animate = () => {
      raf = requestAnimationFrame(animate);
      t += 0.012;
      globe.rotation.y = Math.sin(t*0.25)*0.12;
      globe.rotation.x = Math.cos(t*0.18)*0.07;
      const scanY = Math.sin(t*0.7)*1.55;
      beam.position.y = scanY;
      beamGlow.position.y = scanY;
      beam.material.opacity = 0.4 + Math.abs(Math.sin(t*0.7))*0.5;
      beamGlow.material.opacity = 0.05 + Math.abs(Math.sin(t*0.7))*0.12;
      pl2.intensity = 1.2 + Math.sin(t*1.2)*0.6;
      renderer.render(scene, camera);
    };
    animate();
    return () => { cancelAnimationFrame(raf); renderer.dispose(); };
  }, [canvasRef]);

  return <canvas ref={canvasRef} style={{ borderRadius:'50%', display:'block' }} />;
}

// ─── TILT HOOK ────────────────────────────────────────────────────────────────
function useTilt(ref, strength = 12) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const onMove = e => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      el.style.transform = `perspective(800px) rotateY(${x*strength}deg) rotateX(${-y*strength}deg) scale3d(1.02,1.02,1.02)`;
    };
    const onLeave = () => { el.style.transform = 'perspective(800px) rotateY(0deg) rotateX(0deg) scale3d(1,1,1)'; };
    el.addEventListener('mousemove', onMove);
    el.addEventListener('mouseleave', onLeave);
    return () => { el.removeEventListener('mousemove', onMove); el.removeEventListener('mouseleave', onLeave); };
  }, [ref, strength]);
}

// ─── DATA ─────────────────────────────────────────────────────────────────────
const WORKFLOW = [
  { id:'capture', title:'Capture', desc:'High-res macro image of the inner lower eyelid conjunctiva.', icon:<LucideCamera size={22}/> },
  { id:'quality', title:'Quality Gate', desc:'Vision algorithms reject blurry, dark, or misframed images.', icon:<LucideShieldCheck size={22}/> },
  { id:'risk', title:'AI Prediction', desc:'EfficientNet-B0 estimates hemoglobin levels from pallor.', icon:<LucideBrain size={22}/> },
  { id:'symptoms', title:'Symptom Fusion', desc:'Fatigue, dizziness signals fused with image biomarkers.', icon:<LucideHeartPulse size={22}/> },
  { id:'guidance', title:'GenAI Guidance', desc:'Qwen-2.5 translates AI data into safe, actionable steps.', icon:<LucideMessageSquare size={22}/> }
];

const DEMOS = [
  { hb:14.1, status:'OPTIMAL', label:'Normal Baseline', color:'#10B981', colorDim:'rgba(16,185,129,0.15)', conf:94,
    signals:[{n:'Vascular Density',v:'High',pct:92},{n:'Conjunctival Pallor',v:'Absent',pct:88},{n:'Chromatic Index',v:'Normal',pct:95}],
    guide:"Hemoglobin within peak clinical range. Conjunctival micro-vessel analysis indicates optimal oxygen-carrying capacity. No further screening required at this time." },
  { hb:9.8, status:'MODERATE', label:'Mild Anemia', color:'#F59E0B', colorDim:'rgba(245,158,11,0.15)', conf:88,
    signals:[{n:'Vascular Density',v:'Reduced',pct:48},{n:'Conjunctival Pallor',v:'Moderate',pct:42},{n:'Chromatic Index',v:'Shifted',pct:55}],
    guide:"Indicators of mild anemia detected. Vascular density shows significant deviation from baseline. Recommend dietary iron adjustment and confirmatory CBC lab test." },
  { hb:6.9, status:'CRITICAL', label:'Severe Anemia', color:'#EF4444', colorDim:'rgba(239,68,68,0.15)', conf:85,
    signals:[{n:'Vascular Density',v:'Critical',pct:12},{n:'Conjunctival Pallor',v:'Severe',pct:15},{n:'Chromatic Index',v:'Anemic',pct:18}],
    guide:"Critical anemia markers identified. Severe conjunctival pallor and minimal capillary visibility detected. Immediate medical evaluation is strongly recommended." }
];

const TECH_STACK = [
  { icon:<LucideBrain size={22}/>, title:'Vision Screening Layer', desc:'EfficientNet-B0 trained on 710 clinical specimens to analyze micro-vessel density and conjunctival pallor with sub-millimeter precision.' },
  { icon:<LucideZap size={22}/>, title:'Grounded GenAI Layer', desc:'Qwen-2.5 constrained by deterministic medical rules to provide safe, personalized next-step guidance without hallucination.' },
  { icon:<LucideLock size={22}/>, title:'Safety Triage System', desc:'Four-band triage architecture (Low, Moderate, High, Retake) designed to prioritize user safety over false confidence.' }
];

// ─── NAV ──────────────────────────────────────────────────────────────────────
function Nav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', fn);
    return () => window.removeEventListener('scroll', fn);
  }, []);

  return (
    <motion.nav
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.7, ease: [0.22,1,0.36,1] }}
      style={{
        position:'fixed', top: scrolled ? '0.75rem' : '1.5rem',
        left: scrolled ? '1rem' : '2rem', right: scrolled ? '1rem' : '2rem',
        zIndex:100, transition:'all 0.5s cubic-bezier(0.22,1,0.36,1)',
        borderRadius: scrolled ? '1.25rem' : '1.5rem',
        padding: scrolled ? '0.875rem 1.75rem' : '1.25rem 2.5rem',
        background: scrolled ? 'rgba(3,3,10,0.85)' : 'transparent',
        backdropFilter: scrolled ? 'blur(24px) saturate(180%)' : 'none',
        WebkitBackdropFilter: scrolled ? 'blur(24px) saturate(180%)' : 'none',
        border: scrolled ? '1px solid rgba(255,255,255,0.07)' : '1px solid transparent',
        boxShadow: scrolled ? '0 8px 40px rgba(0,0,0,0.4)' : 'none',
        display:'flex', justifyContent:'space-between', alignItems:'center',
      }}
    >
      {/* Logo */}
      <div style={{ display:'flex', alignItems:'center', gap:'0.875rem' }}>
        <div style={{
          width:38, height:38,
          background:'linear-gradient(135deg, #C8102E 0%, #E8294A 100%)',
          borderRadius:'10px', display:'flex', alignItems:'center', justifyContent:'center',
          boxShadow:'0 6px 20px rgba(200,16,46,0.4)',
          fontSize:'0.7rem', fontWeight:900, color:'#fff', letterSpacing:'0.05em'
        }}>AL</div>
        <span style={{ fontSize:'1.1rem', fontWeight:800, letterSpacing:'-0.02em' }}>
          Anemia<span style={{ color:'var(--accent)' }}>Lens</span>
        </span>
      </div>

      {/* Links */}
      <div style={{ display:'flex', gap:'2.5rem', fontSize:'0.7rem', fontWeight:700, textTransform:'uppercase', letterSpacing:'0.1em' }}>
        {['Technology','Workflow','Live Screening'].map(l => (
          <a key={l} href={`#${l.toLowerCase().replace(' ','-')}`}
            style={{ color:'var(--t2)', textDecoration:'none', transition:'color 0.2s' }}
            onMouseEnter={e=>e.target.style.color='var(--white)'}
            onMouseLeave={e=>e.target.style.color='var(--t2)'}
          >{l}</a>
        ))}
      </div>

      <button className="btn btn-ghost" style={{ padding:'0.6rem 1.4rem', fontSize:'0.65rem' }}>
        Login Provider
      </button>
    </motion.nav>
  );
}

// ─── HERO ─────────────────────────────────────────────────────────────────────
function Hero({ eyeRef }) {
  const { scrollY } = useScroll();
  const y = useTransform(scrollY, [0, 600], [0, -80]);
  const opacity = useTransform(scrollY, [0, 400], [1, 0]);

  return (
    <section style={{ position:'relative', zIndex:1, minHeight:'100vh', display:'flex', alignItems:'center', padding:'0 4rem', overflow:'hidden' }}>
      {/* Ambient orbs */}
      <div className="orb" style={{ width:600, height:600, background:'radial-gradient(circle, rgba(200,16,46,0.18) 0%, transparent 70%)', top:'-10%', left:'-5%' }} />
      <div className="orb" style={{ width:400, height:400, background:'radial-gradient(circle, rgba(64,64,255,0.08) 0%, transparent 70%)', bottom:'10%', right:'5%' }} />

      <motion.div style={{ y, opacity, display:'grid', gridTemplateColumns:'1.15fr 0.85fr', gap:'5rem', width:'100%', maxWidth:1400, margin:'0 auto' }}>
        {/* Left */}
        <motion.div
          initial={{ opacity:0, x:-40 }}
          animate={{ opacity:1, x:0 }}
          transition={{ duration:0.9, ease:[0.22,1,0.36,1] }}
          style={{ display:'flex', flexDirection:'column', gap:'2.5rem', paddingTop:'6rem' }}
        >
          {/* Badge */}
          <motion.div
            initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.2, duration:0.6 }}
            style={{
              display:'inline-flex', alignSelf:'flex-start', alignItems:'center', gap:'0.6rem',
              padding:'0.45rem 1rem', borderRadius:'99px',
              background:'linear-gradient(135deg, rgba(200,16,46,0.15) 0%, rgba(232,41,74,0.08) 100%)',
              border:'1px solid rgba(200,16,46,0.3)',
              fontSize:'0.6rem', fontWeight:800, textTransform:'uppercase', letterSpacing:'0.15em', color:'var(--accent2)'
            }}
          >
            <div style={{ width:6, height:6, borderRadius:'50%', background:'var(--accent)', animation:'blink 1.5s infinite' }} />
            AI-Powered Screening Hub
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity:0, y:30 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.3, duration:0.8 }}
            style={{ fontSize:'clamp(3.2rem, 7vw, 6.8rem)', fontWeight:900, lineHeight:0.88, letterSpacing:'-0.04em' }}
          >
            See what<br/>
            <span style={{ color:'var(--t3)', fontStyle:'italic', fontWeight:300, fontFamily:'var(--serif)', fontSize:'0.9em' }}>your blood</span><br/>
            <span className="grad-text">reveals.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.45, duration:0.7 }}
            style={{ fontSize:'1.1rem', color:'var(--t2)', lineHeight:1.65, maxWidth:480, fontWeight:400 }}
          >
            AnemiaLens transforms your smartphone into a first-pass screening tool. Clinical-grade vision AI analyzes conjunctival pallor so you can act sooner, safely.
          </motion.p>

          <motion.div
            initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.55, duration:0.7 }}
            style={{ display:'flex', gap:'1rem' }}
          >
            <button className="btn btn-red" onClick={() => document.getElementById('live-screening')?.scrollIntoView({ behavior:'smooth' })}>
              <LucideScanEye size={16} /> Start Screening
            </button>
            <button className="btn btn-ghost">
              Read Impact Story <LucideArrowRight size={14} />
            </button>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ delay:0.7, duration:0.8 }}
            style={{ display:'flex', gap:'3.5rem', paddingTop:'2.5rem', borderTop:'1px solid var(--b2)', marginTop:'0.5rem' }}
          >
            {[['1.92B+','Anemia Cases Globally'],['92%','Model Sensitivity'],['710','Clinical Specimens']].map(([val, label]) => (
              <div key={label}>
                <div style={{ fontSize:'2.2rem', fontWeight:300, fontFamily:'var(--serif)', color:'var(--white)' }}>
                  {val.replace(/[^0-9.]/g,'')}
                  <span className="grad-text" style={{ fontSize:'1.4rem' }}>{val.replace(/[0-9.]/g,'')}</span>
                </div>
                <div style={{ fontSize:'0.6rem', textTransform:'uppercase', letterSpacing:'0.1em', color:'var(--t4)', marginTop:'0.4rem' }}>{label}</div>
              </div>
            ))}
          </motion.div>
        </motion.div>

        {/* Right — Eye */}
        <motion.div
          initial={{ opacity:0, scale:0.85 }} animate={{ opacity:1, scale:1 }}
          transition={{ duration:1.1, delay:0.15, ease:[0.22,1,0.36,1] }}
          style={{ display:'flex', alignItems:'center', justifyContent:'center', position:'relative', paddingTop:'5rem' }}
        >
          <div style={{ position:'relative', width:480, height:480 }}>
            {/* Pulse rings */}
            {[0,1,2].map(i => (
              <div key={i} style={{
                position:'absolute', inset:`${-20-i*22}px`, borderRadius:'50%',
                border:`1px solid rgba(200,16,46,${0.15-i*0.04})`,
                animation:`pulse-ring ${2+i*0.8}s ease-out ${i*0.6}s infinite`
              }} />
            ))}
            {/* Orbit rings */}
            <div style={{ position:'absolute', inset:-30, borderRadius:'50%', border:'1px solid rgba(255,255,255,0.04)', animation:'spin-slow 25s linear infinite' }}>
              <div style={{ position:'absolute', top:-4, left:'50%', width:8, height:8, borderRadius:'50%', background:'var(--accent)', boxShadow:'0 0 12px var(--accent)', transform:'translateX(-50%)' }} />
            </div>
            <div style={{ position:'absolute', inset:-55, borderRadius:'50%', border:'1px solid rgba(200,16,46,0.08)', animation:'spin-rev 40s linear infinite' }}>
              <div style={{ position:'absolute', bottom:-4, left:'50%', width:5, height:5, borderRadius:'50%', background:'rgba(200,16,46,0.6)', transform:'translateX(-50%)' }} />
            </div>

            <EyeScanner canvasRef={eyeRef} />

            {/* HUD labels */}
            <div style={{ position:'absolute', bottom:'-3.5rem', left:'50%', transform:'translateX(-50%)', textAlign:'center', whiteSpace:'nowrap' }}>
              <div style={{ fontSize:'0.6rem', fontWeight:700, textTransform:'uppercase', letterSpacing:'0.2em', color:'var(--t3)' }}>Scanning Conjunctival ROI</div>
              <div style={{ fontSize:'0.5rem', color:'var(--accent)', marginTop:'0.4rem', animation:'blink 2s infinite', letterSpacing:'0.15em' }}>● NEURAL DIAGNOSTICS ACTIVE</div>
            </div>

            {/* Corner HUD decorations */}
            {[{top:8,left:8},{top:8,right:8},{bottom:8,left:8},{bottom:8,right:8}].map((pos,i) => (
              <div key={i} style={{
                position:'absolute', ...pos, width:20, height:20,
                borderTop: (i<2)?'2px solid rgba(200,16,46,0.5)':undefined,
                borderBottom: (i>=2)?'2px solid rgba(200,16,46,0.5)':undefined,
                borderLeft: (i===0||i===2)?'2px solid rgba(200,16,46,0.5)':undefined,
                borderRight: (i===1||i===3)?'2px solid rgba(200,16,46,0.5)':undefined,
              }} />
            ))}
          </div>
        </motion.div>
      </motion.div>
    </section>
  );
}

// ─── IMPACT SECTION ───────────────────────────────────────────────────────────
function Impact() {
  const ref = useRef(null);
  useTilt(ref, 8);

  return (
    <section id="impact" style={{ position:'relative', zIndex:1, padding:'10rem 4rem', borderTop:'1px solid var(--b1)' }}>
      <div className="orb" style={{ width:500, height:500, background:'radial-gradient(circle, rgba(200,16,46,0.1) 0%, transparent 70%)', top:'20%', right:'-10%' }} />
      <div style={{ maxWidth:1200, margin:'0 auto' }}>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'7rem', alignItems:'center' }}>

          {/* Left card */}
          <motion.div
            ref={ref}
            className="glass noise tilt-card"
            initial={{ opacity:0, x:-30 }} whileInView={{ opacity:1, x:0 }}
            viewport={{ once:true }} transition={{ duration:0.8, ease:[0.22,1,0.36,1] }}
            style={{ padding:'3.5rem', borderLeft:'3px solid var(--crimson)', boxShadow:'0 0 0 1px var(--b2), 0 40px 80px rgba(0,0,0,0.4), -4px 0 40px rgba(200,16,46,0.1)' }}
          >
            <div style={{ fontSize:'0.65rem', fontWeight:800, color:'var(--accent)', textTransform:'uppercase', letterSpacing:'0.2em', marginBottom:'1.5rem' }}>The Challenge</div>
            <h2 style={{ fontSize:'2.8rem', fontWeight:900, lineHeight:1.05, letterSpacing:'-0.03em', marginBottom:'1.75rem' }}>
              Bridging the<br/>
              <span style={{ color:'var(--t3)', fontStyle:'italic', fontWeight:300, fontFamily:'var(--serif)' }}>Screening Gap.</span>
            </h2>
            <p style={{ fontSize:'1rem', color:'var(--t2)', lineHeight:1.7, marginBottom:'2.5rem' }}>
              Anemia affects 25% of the world's population, yet detection remains expensive and slow. Early action is delayed by clinic distance, blood testing costs, and lack of specialized hardware.
            </p>
            <div style={{ display:'flex', gap:'2.5rem' }}>
              {[['$0','Marginal Cost'],['100%','Smartphone-First']].map(([v,l]) => (
                <div key={l}>
                  <div style={{ fontSize:'2rem', fontWeight:700 }}>{v}</div>
                  <div style={{ fontSize:'0.58rem', textTransform:'uppercase', letterSpacing:'0.1em', color:'var(--t4)', marginTop:'0.3rem' }}>{l}</div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Right cards */}
          <div style={{ display:'flex', flexDirection:'column', gap:'1.25rem' }}>
            {[
              { icon:<LucideGlobe size={20}/>, title:'Global Impact', desc:'Designed for low-resource settings and remote health workers worldwide.' },
              { icon:<LucideMicroscope size={20}/>, title:'Clinical Credibility', desc:'EfficientNet-B0 backbone validated on 710 clinical specimens.' },
              { icon:<LucideStethoscope size={20}/>, title:'Safety-First Triage', desc:'Non-diagnostic triage language with grounded GenAI guidance.' }
            ].map((item, i) => (
              <motion.div
                key={item.title}
                className="glass glass-hover"
                initial={{ opacity:0, x:30 }} whileInView={{ opacity:1, x:0 }}
                viewport={{ once:true }} transition={{ duration:0.6, delay:i*0.1, ease:[0.22,1,0.36,1] }}
                style={{ padding:'1.75rem 2rem', display:'flex', gap:'1.5rem', alignItems:'center' }}
              >
                <div style={{
                  width:48, height:48, borderRadius:'0.875rem', flexShrink:0,
                  background:'linear-gradient(135deg, rgba(200,16,46,0.2) 0%, rgba(200,16,46,0.05) 100%)',
                  border:'1px solid rgba(200,16,46,0.2)',
                  display:'flex', alignItems:'center', justifyContent:'center', color:'var(--accent)'
                }}>{item.icon}</div>
                <div>
                  <h4 style={{ fontWeight:800, fontSize:'0.95rem', marginBottom:'0.3rem' }}>{item.title}</h4>
                  <p style={{ fontSize:'0.78rem', color:'var(--t3)', lineHeight:1.5 }}>{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── WORKFLOW SECTION ─────────────────────────────────────────────────────────
function Workflow() {
  const [active, setActive] = useState(null);

  return (
    <section id="workflow" style={{ position:'relative', zIndex:1, padding:'10rem 4rem', background:'linear-gradient(180deg, var(--bg) 0%, var(--surface) 50%, var(--bg) 100%)' }}>
      <div style={{ maxWidth:1200, margin:'0 auto' }}>
        <motion.div
          initial={{ opacity:0, y:30 }} whileInView={{ opacity:1, y:0 }}
          viewport={{ once:true }} transition={{ duration:0.7 }}
          style={{ textAlign:'center', marginBottom:'7rem' }}
        >
          <div style={{ fontSize:'0.65rem', fontWeight:800, color:'var(--accent)', textTransform:'uppercase', letterSpacing:'0.2em', marginBottom:'1.25rem' }}>The Architecture</div>
          <h2 style={{ fontSize:'clamp(2.5rem,5vw,4rem)', fontWeight:900, letterSpacing:'-0.04em', lineHeight:1.05 }}>
            Five Steps to<br/>
            <span style={{ color:'var(--t3)', fontStyle:'italic', fontWeight:300, fontFamily:'var(--serif)' }}>Screening Clarity.</span>
          </h2>
        </motion.div>

        <div style={{ display:'grid', gridTemplateColumns:'repeat(5,1fr)', gap:'1.5rem', position:'relative' }}>
          {/* Connector line */}
          <div style={{ position:'absolute', top:52, left:'10%', right:'10%', height:1, background:'linear-gradient(90deg, transparent, var(--b2) 20%, var(--b2) 80%, transparent)', zIndex:0 }} />

          {WORKFLOW.map((step, idx) => (
            <motion.div
              key={step.id}
              className="glass glass-hover"
              initial={{ opacity:0, y:40 }} whileInView={{ opacity:1, y:0 }}
              viewport={{ once:true }} transition={{ duration:0.6, delay:idx*0.1 }}
              onMouseEnter={() => setActive(idx)}
              onMouseLeave={() => setActive(null)}
              style={{
                padding:'2.25rem 1.5rem', textAlign:'center', display:'flex', flexDirection:'column', gap:'1.25rem',
                position:'relative', zIndex:1,
                boxShadow: active===idx ? `0 20px 60px rgba(0,0,0,0.5), 0 0 30px rgba(200,16,46,0.1)` : 'none',
                borderColor: active===idx ? 'rgba(200,16,46,0.25)' : undefined,
              }}
            >
              <div style={{
                width:56, height:56, borderRadius:'1.25rem', margin:'0 auto',
                background: active===idx
                  ? 'linear-gradient(135deg, rgba(200,16,46,0.3) 0%, rgba(200,16,46,0.1) 100%)'
                  : 'var(--g2)',
                border: `1px solid ${active===idx ? 'rgba(200,16,46,0.3)' : 'var(--b2)'}`,
                display:'flex', alignItems:'center', justifyContent:'center',
                color: active===idx ? 'var(--accent)' : 'var(--t2)',
                transition:'all 0.3s var(--ease-out)',
                boxShadow: active===idx ? '0 0 20px rgba(200,16,46,0.2)' : 'none'
              }}>{step.icon}</div>

              <div style={{ fontSize:'0.55rem', fontWeight:800, color:'var(--t4)', textTransform:'uppercase', letterSpacing:'0.15em' }}>Step {idx+1}</div>
              <h4 style={{ fontWeight:800, fontSize:'0.85rem', textTransform:'uppercase', letterSpacing:'0.05em', color: active===idx ? 'var(--white)' : 'var(--t1)' }}>{step.title}</h4>
              <p style={{ fontSize:'0.72rem', color:'var(--t3)', lineHeight:1.6 }}>{step.desc}</p>

              {idx < 4 && (
                <div style={{ position:'absolute', top:48, right:-12, zIndex:10, color:'var(--t4)' }}>
                  <LucideChevronRight size={20} />
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── LIVE SCREENING SECTION ───────────────────────────────────────────────────
function LiveScreening() {
  const [activeDemo, setActiveDemo] = useState(0);
  const [scanState, setScanState] = useState('idle');
  const [guideText, setGuideText] = useState('');
  const [progress, setProgress] = useState(0);
  const d = DEMOS[activeDemo];

  useEffect(() => {
    if (scanState !== 'result') return;
    setGuideText('');
    let i = 0;
    const iv = setInterval(() => {
      if (i < d.guide.length) setGuideText(p => p + d.guide[i++]);
      else clearInterval(iv);
    }, 14);
    return () => clearInterval(iv);
  }, [activeDemo, scanState, d.guide]);

  useEffect(() => {
    if (scanState !== 'scanning') { setProgress(0); return; }
    setProgress(0);
    const iv = setInterval(() => setProgress(p => { if (p >= 100) { clearInterval(iv); return 100; } return p + 2; }), 55);
    return () => clearInterval(iv);
  }, [scanState]);

  const triggerScan = () => {
    setScanState('scanning');
    setTimeout(() => setScanState('result'), 3000);
  };

  const nextProfile = () => {
    setActiveDemo(p => (p+1) % DEMOS.length);
    setScanState('idle');
    setGuideText('');
  };

  const SCAN_STEPS = ['Initializing camera feed...','Detecting conjunctival region...','Extracting vascular features...','Running EfficientNet-B0...','Generating clinical brief...'];
  const stepIdx = Math.floor(progress / 20);

  return (
    <section id="live-screening" style={{ position:'relative', zIndex:1, padding:'10rem 4rem' }}>
      <div className="orb" style={{ width:600, height:600, background:'radial-gradient(circle, rgba(200,16,46,0.08) 0%, transparent 70%)', top:'30%', left:'-15%' }} />
      <div style={{ maxWidth:1200, margin:'0 auto' }}>
        <motion.div
          initial={{ opacity:0, y:30 }} whileInView={{ opacity:1, y:0 }}
          viewport={{ once:true }} transition={{ duration:0.7 }}
          style={{ textAlign:'center', marginBottom:'5rem' }}
        >
          <div style={{ fontSize:'0.65rem', fontWeight:800, color:'var(--accent)', textTransform:'uppercase', letterSpacing:'0.2em', marginBottom:'1.25rem' }}>Diagnostic Hub</div>
          <h2 style={{ fontSize:'clamp(2.5rem,5vw,4rem)', fontWeight:900, letterSpacing:'-0.04em', lineHeight:1.05 }}>
            Interactive<br/>
            <span style={{ color:'var(--t3)', fontStyle:'italic', fontWeight:300, fontFamily:'var(--serif)' }}>Screening Experience.</span>
          </h2>
        </motion.div>

        {/* Demo selector */}
        <div style={{ display:'flex', gap:'0.75rem', justifyContent:'center', marginBottom:'3rem' }}>
          {DEMOS.map((demo, i) => (
            <button
              key={i}
              onClick={() => { setActiveDemo(i); setScanState('idle'); setGuideText(''); }}
              className="btn"
              style={{
                padding:'0.6rem 1.4rem', fontSize:'0.65rem',
                background: activeDemo===i ? demo.colorDim : 'var(--g1)',
                border: `1px solid ${activeDemo===i ? demo.color+'55' : 'var(--b2)'}`,
                color: activeDemo===i ? demo.color : 'var(--t2)',
                boxShadow: activeDemo===i ? `0 0 20px ${demo.color}22` : 'none',
              }}
            >{demo.label}</button>
          ))}
        </div>

        {/* Main panel */}
        <motion.div
          className="glass noise"
          initial={{ opacity:0, y:30 }} whileInView={{ opacity:1, y:0 }}
          viewport={{ once:true }} transition={{ duration:0.8 }}
          style={{ overflow:'hidden', display:'grid', gridTemplateColumns:'1fr 1.25fr', boxShadow:'0 40px 100px rgba(0,0,0,0.5), 0 0 0 1px var(--b2)' }}
        >
          {/* Left — Camera simulator */}
          <div style={{ background:'#020208', position:'relative', minHeight:580, borderRight:'1px solid var(--b1)' }}>
            {/* macOS dots */}
            <div style={{ position:'absolute', top:'1.25rem', left:'1.25rem', display:'flex', gap:'0.4rem', zIndex:5 }}>
              {['#FF5F57','#FFBD2E','#28C840'].map(c => <div key={c} style={{ width:9, height:9, borderRadius:'50%', background:c }} />)}
            </div>

            {/* Status bar */}
            <div style={{ position:'absolute', top:'1.25rem', right:'1.25rem', display:'flex', alignItems:'center', gap:'0.5rem', zIndex:5 }}>
              <LucideWifi size={12} style={{ color:'var(--t4)' }} />
              <div style={{ fontSize:'0.5rem', color:'var(--t4)', fontFamily:'var(--mono)', fontWeight:600 }}>1080p/60fps</div>
            </div>

            {/* Scan frame overlay */}
            <div style={{ position:'absolute', inset:0, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', padding:'3rem' }}>
              <AnimatePresence mode="wait">
                {scanState === 'idle' && (
                  <motion.div key="idle" initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }}
                    style={{ textAlign:'center', display:'flex', flexDirection:'column', alignItems:'center', gap:'2rem' }}
                  >
                    <div style={{
                      width:110, height:110, borderRadius:'50%',
                      border:'1px solid var(--b3)',
                      display:'flex', alignItems:'center', justifyContent:'center', color:'var(--t3)',
                      background:'radial-gradient(circle, var(--g2) 0%, transparent 70%)'
                    }}>
                      <LucideCamera size={42} />
                    </div>
                    <div>
                      <h4 style={{ fontSize:'0.85rem', fontWeight:700, textTransform:'uppercase', letterSpacing:'0.1em', marginBottom:'0.5rem' }}>Camera Standby</h4>
                      <p style={{ fontSize:'0.7rem', color:'var(--t3)' }}>Align lower eyelid within frame</p>
                    </div>
                    <button className="btn btn-red" onClick={triggerScan} style={{ marginTop:'0.5rem' }}>
                      <LucideScanEye size={15} /> Begin Analysis
                    </button>
                  </motion.div>
                )}

                {scanState === 'scanning' && (
                  <motion.div key="scanning" initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }}
                    style={{ width:'100%', display:'flex', flexDirection:'column', alignItems:'center', gap:'2rem' }}
                  >
                    {/* Scan target */}
                    <div style={{ position:'relative', width:240, height:170, border:'1px solid rgba(200,16,46,0.3)', borderRadius:'1rem', overflow:'hidden', background:'rgba(200,16,46,0.03)' }}>
                      {/* Corner brackets */}
                      {[{top:0,left:0},{top:0,right:0},{bottom:0,left:0},{bottom:0,right:0}].map((pos,i) => (
                        <div key={i} style={{
                          position:'absolute', ...pos, width:16, height:16,
                          borderTop:(i<2)?'2px solid var(--accent)':undefined,
                          borderBottom:(i>=2)?'2px solid var(--accent)':undefined,
                          borderLeft:(i===0||i===2)?'2px solid var(--accent)':undefined,
                          borderRight:(i===1||i===3)?'2px solid var(--accent)':undefined,
                        }} />
                      ))}
                      {/* Scan beam */}
                      <div style={{ position:'absolute', left:0, right:0, height:2, background:'linear-gradient(90deg, transparent, var(--crimson), transparent)', boxShadow:'0 0 12px var(--crimson)', animation:'scan 1.8s ease-in-out infinite' }} />
                      <div style={{ position:'absolute', left:0, right:0, height:20, background:'linear-gradient(180deg, transparent, rgba(200,16,46,0.08), transparent)', animation:'scan 1.8s ease-in-out infinite' }} />
                    </div>

                    {/* Progress */}
                    <div style={{ width:'80%' }}>
                      <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'0.5rem' }}>
                        <span style={{ fontSize:'0.55rem', color:'var(--accent)', fontFamily:'var(--mono)', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.1em', animation:'blink 1s infinite' }}>
                          {SCAN_STEPS[Math.min(stepIdx, SCAN_STEPS.length-1)]}
                        </span>
                        <span style={{ fontSize:'0.55rem', color:'var(--t3)', fontFamily:'var(--mono)' }}>{progress}%</span>
                      </div>
                      <div className="progress-track">
                        <div className="progress-fill" style={{ width:`${progress}%`, background:'linear-gradient(90deg, var(--crimson), var(--accent))' }} />
                      </div>
                    </div>
                    <div style={{ fontSize:'0.5rem', color:'var(--t4)', fontFamily:'var(--mono)', letterSpacing:'0.1em' }}>EFFICIENTNET-B0 MODEL v1.4.2</div>
                  </motion.div>
                )}

                {scanState === 'result' && (
                  <motion.div key="result" initial={{ opacity:0, scale:0.85 }} animate={{ opacity:1, scale:1 }}
                    transition={{ duration:0.5, ease:[0.22,1,0.36,1] }}
                    style={{ textAlign:'center', display:'flex', flexDirection:'column', alignItems:'center', gap:'1.5rem' }}
                  >
                    <div style={{
                      width:90, height:90, borderRadius:'50%',
                      background:`radial-gradient(circle, ${d.colorDim} 0%, transparent 70%)`,
                      border:`1px solid ${d.color}44`,
                      display:'flex', alignItems:'center', justifyContent:'center',
                      color:d.color, boxShadow:`0 0 30px ${d.color}33`
                    }}>
                      <LucideCheckCircle2 size={36} />
                    </div>
                    <div>
                      <h4 style={{ fontSize:'0.9rem', fontWeight:800, textTransform:'uppercase', letterSpacing:'0.1em', color:d.color }}>Analysis Complete</h4>
                      <p style={{ fontSize:'0.65rem', color:'var(--t3)', marginTop:'0.4rem' }}>Confidence: {d.conf}%</p>
                    </div>
                    <button className="btn btn-ghost" onClick={triggerScan} style={{ fontSize:'0.6rem', padding:'0.5rem 1.2rem' }}>
                      <LucideScanEye size={13} /> Re-scan
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Right — Results */}
          <div style={{ padding:'3.5rem', opacity: scanState==='scanning' ? 0.35 : 1, transition:'opacity 0.4s ease' }}>
            {/* Hb reading */}
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'2.5rem' }}>
              <div>
                <div style={{ fontSize:'0.58rem', fontWeight:800, color:'var(--t4)', textTransform:'uppercase', letterSpacing:'0.15em', marginBottom:'0.4rem' }}>Hb Estimation</div>
                <div style={{ display:'flex', alignItems:'baseline', gap:'0.5rem' }}>
                  <motion.span
                    key={`${activeDemo}-${scanState}`}
                    initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }}
                    style={{ fontSize:'5.5rem', fontWeight:900, lineHeight:1, color: scanState==='result' ? d.color : 'var(--white)', fontFamily:'var(--serif)', transition:'color 0.5s' }}
                  >{scanState==='result' ? d.hb.toFixed(1) : '--.-'}</motion.span>
                  <span style={{ fontSize:'1rem', fontWeight:700, color:'var(--t3)' }}>g/dL</span>
                </div>
              </div>
              <div style={{ textAlign:'right' }}>
                <div style={{ fontSize:'0.58rem', fontWeight:800, color:'var(--t4)', textTransform:'uppercase', letterSpacing:'0.15em', marginBottom:'0.4rem' }}>Triage Status</div>
                <div style={{
                  fontSize:'1rem', fontWeight:800, padding:'0.4rem 1rem', borderRadius:'0.5rem',
                  background: scanState==='result' ? d.colorDim : 'var(--g1)',
                  border: `1px solid ${scanState==='result' ? d.color+'44' : 'var(--b2)'}`,
                  color: scanState==='result' ? d.color : 'var(--t2)',
                  transition:'all 0.5s'
                }}>{scanState==='result' ? d.status : 'PENDING'}</div>
              </div>
            </div>

            {/* Signal bars */}
            <div style={{ marginBottom:'2.5rem', display:'flex', flexDirection:'column', gap:'1.25rem' }}>
              {d.signals.map((sig, i) => (
                <div key={sig.n}>
                  <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'0.5rem', fontSize:'0.65rem', fontWeight:700, textTransform:'uppercase', letterSpacing:'0.05em' }}>
                    <span style={{ color:'var(--t2)' }}>{sig.n}</span>
                    <span style={{ color: scanState==='result' ? d.color : 'var(--t3)', transition:'color 0.5s' }}>{scanState==='result' ? sig.v : '--'}</span>
                  </div>
                  <div className="progress-track">
                    <motion.div
                      className="progress-fill"
                      initial={{ width:0 }}
                      animate={{ width: scanState==='result' ? `${sig.pct}%` : '0%' }}
                      transition={{ duration:1.2, delay:i*0.15, ease:[0.22,1,0.36,1] }}
                      style={{ background: scanState==='result' ? `linear-gradient(90deg, ${d.color}88, ${d.color})` : 'var(--g2)' }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* AI insight */}
            <div className="glass" style={{ padding:'1.5rem', marginBottom:'2rem', borderRadius:'1rem' }}>
              <div style={{ display:'flex', alignItems:'center', gap:'0.6rem', marginBottom:'0.875rem' }}>
                <div style={{ width:6, height:6, background:'var(--accent)', borderRadius:'50%', animation: scanState==='result' ? 'blink 1.5s infinite' : 'none' }} />
                <span style={{ fontSize:'0.58rem', fontWeight:800, color:'var(--accent)', textTransform:'uppercase', letterSpacing:'0.12em' }}>AI Clinical Insight</span>
              </div>
              <p style={{ fontSize:'0.82rem', color:'var(--t2)', lineHeight:1.65, minHeight:'4.5em' }}>
                {scanState==='result'
                  ? guideText
                  : 'Awaiting biometric analysis. Complete conjunctival capture to generate automated medical guidance.'}
                {scanState==='result' && guideText.length < d.guide.length && (
                  <span style={{ display:'inline-block', width:2, height:'1em', background:'var(--accent)', marginLeft:2, verticalAlign:'middle', animation:'blink 0.7s infinite' }} />
                )}
              </p>
            </div>

            {/* Actions */}
            <div style={{ display:'flex', gap:'0.875rem' }}>
              <button className="btn btn-red" style={{ flex:1 }} onClick={triggerScan} disabled={scanState==='scanning'}>
                <LucideScanEye size={15} /> {scanState==='scanning' ? 'Processing...' : 'Run New Scan'}
              </button>
              <button className="btn btn-ghost" style={{ flex:1 }} onClick={nextProfile}>
                Next Case <LucideArrowRight size={14} />
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ─── TECH SECTION ─────────────────────────────────────────────────────────────
function TechSection() {
  const cardRef = useRef(null);
  useTilt(cardRef, 6);

  return (
    <section id="technology" style={{ position:'relative', zIndex:1, padding:'10rem 4rem', background:'linear-gradient(180deg, var(--bg) 0%, var(--surface) 100%)' }}>
      <div className="orb" style={{ width:500, height:500, background:'radial-gradient(circle, rgba(200,16,46,0.1) 0%, transparent 70%)', bottom:'0%', right:'-10%' }} />
      <div style={{ maxWidth:1200, margin:'0 auto' }}>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'7rem', alignItems:'center' }}>

          {/* Left */}
          <div style={{ display:'flex', flexDirection:'column', gap:'3rem' }}>
            <motion.div initial={{ opacity:0, y:30 }} whileInView={{ opacity:1, y:0 }} viewport={{ once:true }} transition={{ duration:0.7 }}>
              <div style={{ fontSize:'0.65rem', fontWeight:800, color:'var(--accent)', textTransform:'uppercase', letterSpacing:'0.2em', marginBottom:'1.25rem' }}>Architecture</div>
              <h2 style={{ fontSize:'clamp(2.2rem,4vw,3.5rem)', fontWeight:900, letterSpacing:'-0.04em', lineHeight:1.05 }}>
                The Intelligence<br/>
                <span style={{ color:'var(--t3)', fontStyle:'italic', fontWeight:300, fontFamily:'var(--serif)' }}>Framework.</span>
              </h2>
            </motion.div>

            <div style={{ display:'flex', flexDirection:'column', gap:'2rem' }}>
              {TECH_STACK.map((item, i) => (
                <motion.div
                  key={item.title}
                  initial={{ opacity:0, x:-20 }} whileInView={{ opacity:1, x:0 }}
                  viewport={{ once:true }} transition={{ duration:0.6, delay:i*0.1 }}
                  style={{ display:'flex', gap:'1.75rem' }}
                >
                  <div style={{
                    width:56, height:56, borderRadius:'1rem', flexShrink:0,
                    background:'linear-gradient(135deg, var(--g2) 0%, var(--g1) 100%)',
                    border:'1px solid var(--b2)',
                    display:'flex', alignItems:'center', justifyContent:'center', color:'var(--accent)'
                  }}>{item.icon}</div>
                  <div>
                    <h4 style={{ fontSize:'1rem', fontWeight:700, marginBottom:'0.4rem' }}>{item.title}</h4>
                    <p style={{ fontSize:'0.85rem', color:'var(--t2)', lineHeight:1.6 }}>{item.desc}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Right — Clinical brief card */}
          <motion.div
            ref={cardRef}
            className="glass noise tilt-card"
            initial={{ opacity:0, x:30 }} whileInView={{ opacity:1, x:0 }}
            viewport={{ once:true }} transition={{ duration:0.8 }}
            style={{ padding:'3rem', borderLeft:'3px solid var(--crimson)', boxShadow:'0 40px 80px rgba(0,0,0,0.4), 4px 0 40px rgba(200,16,46,0.08)' }}
          >
            <div style={{ display:'flex', alignItems:'center', gap:'0.75rem', marginBottom:'1.5rem' }}>
              <LucideShield size={18} style={{ color:'var(--accent)' }} />
              <h4 style={{ fontWeight:800, fontSize:'1.1rem' }}>Clinician-Ready Handoff</h4>
            </div>
            <p style={{ fontSize:'0.95rem', color:'var(--t2)', lineHeight:1.65, marginBottom:'2rem' }}>
              AnemiaLens generates a structured "Clinical Brief" for formal medical follow-up, ensuring screening data is properly communicated to healthcare professionals.
            </p>

            {/* Code block */}
            <div style={{
              background:'rgba(0,0,0,0.5)', padding:'1.5rem', borderRadius:'0.875rem',
              fontFamily:'var(--mono)', fontSize:'0.68rem', color:'var(--t2)',
              border:'1px solid var(--b2)', lineHeight:1.8
            }}>
              {[
                ['Provider', 'EfficientNet-B0'],
                ['Risk Score', '68.4% (Moderate)'],
                ['Hb Estimate', '9.8 g/dL'],
                ['Confidence', '88%'],
                ['Triage Band', 'Band 2 — Monitor'],
              ].map(([k,v]) => (
                <div key={k} style={{ display:'flex', gap:'1rem' }}>
                  <span style={{ color:'var(--t4)', minWidth:90 }}>{k}:</span>
                  <span style={{ color:'var(--accent2)' }}>{v}</span>
                </div>
              ))}
            </div>

            <div style={{ display:'flex', gap:'0.875rem', marginTop:'2rem' }}>
              <button className="btn btn-ghost" style={{ flex:1, padding:'0.7rem', fontSize:'0.65rem' }}>
                <LucideShare2 size={14} /> Share Summary
              </button>
              <button className="btn btn-ghost" style={{ flex:1, padding:'0.7rem', fontSize:'0.65rem' }}>
                <LucideDownload size={14} /> Export Report
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

// ─── FOOTER ───────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer style={{ position:'relative', zIndex:1, padding:'6rem 4rem 4rem', background:'var(--surface)', borderTop:'1px solid var(--b1)' }}>
      <div style={{ maxWidth:1400, margin:'0 auto' }}>
        <div style={{ display:'grid', gridTemplateColumns:'2fr 1fr 1fr', gap:'6rem', marginBottom:'5rem' }}>
          <div>
            <div style={{ display:'flex', alignItems:'center', gap:'0.875rem', marginBottom:'1.75rem' }}>
              <div style={{ width:34, height:34, background:'linear-gradient(135deg, var(--crimson), var(--accent))', borderRadius:'9px', display:'flex', alignItems:'center', justifyContent:'center', color:'#fff', fontWeight:900, fontSize:'0.65rem', boxShadow:'0 4px 16px rgba(200,16,46,0.35)' }}>AL</div>
              <span style={{ fontSize:'1.05rem', fontWeight:800 }}>Anemia<span style={{ color:'var(--accent)' }}>Lens</span></span>
            </div>
            <p style={{ fontSize:'0.82rem', color:'var(--t3)', lineHeight:1.8, maxWidth:380, marginBottom:'2rem' }}>
              Smartphone-first anemia screening powered by computer vision and grounded GenAI. Designed for accessibility, safety, and clinical credibility.
            </p>
            <div style={{ display:'flex', gap:'0.75rem', flexWrap:'wrap' }}>
              {['UN SDG 3: GOOD HEALTH','UN SDG 10: REDUCED INEQUALITY'].map(tag => (
                <div key={tag} style={{ padding:'0.4rem 0.875rem', background:'var(--g1)', border:'1px solid var(--b2)', borderRadius:'0.5rem', fontSize:'0.55rem', fontWeight:700, color:'var(--t4)', letterSpacing:'0.05em' }}>{tag}</div>
              ))}
            </div>
          </div>

          {[
            { title:'Technology', links:['Vision Backbone','GenAI Grounding','Safety Gating','Clinical Brief'] },
            { title:'Resources', links:['Impact Narrative','Research Hub','Deployment Guide','Legal Disclaimer'] }
          ].map(col => (
            <div key={col.title}>
              <h5 style={{ fontSize:'0.65rem', fontWeight:800, textTransform:'uppercase', letterSpacing:'0.15em', marginBottom:'1.75rem', color:'var(--t1)' }}>{col.title}</h5>
              <ul style={{ listStyle:'none', display:'flex', flexDirection:'column', gap:'0.875rem' }}>
                {col.links.map(l => (
                  <li key={l} style={{ fontSize:'0.82rem', color:'var(--t3)', cursor:'pointer', transition:'color 0.2s' }}
                    onMouseEnter={e=>e.target.style.color='var(--t1)'}
                    onMouseLeave={e=>e.target.style.color='var(--t3)'}
                  >{l}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div style={{ paddingTop:'2.5rem', borderTop:'1px solid var(--b1)', display:'flex', justifyContent:'space-between', alignItems:'center', gap:'2rem', flexWrap:'wrap' }}>
          <div style={{ fontSize:'0.58rem', color:'var(--t4)', fontWeight:600, letterSpacing:'0.05em' }}>© 2026 ANEMIALENS AI DIAGNOSTICS. ALL RIGHTS RESERVED.</div>
          <div style={{ fontSize:'0.58rem', color:'var(--t4)', maxWidth:560, textAlign:'right', fontStyle:'italic', lineHeight:1.6 }}>
            Disclaimer: AnemiaLens is a screening tool, not a diagnostic device. Results must be confirmed with clinical blood testing.
          </div>
        </div>
      </div>
    </footer>
  );
}

// ─── ROOT ─────────────────────────────────────────────────────────────────────
export default function AnemiaLens() {
  const bgRef = useRef(null);
  const eyeRef = useRef(null);

  return (
    <div style={{ position:'relative', minHeight:'100vh', background:'var(--bg)' }}>
      <style>{G}</style>
      <Background canvasRef={bgRef} />
      <Nav />
      <Hero eyeRef={eyeRef} />
      <Impact />
      <Workflow />
      <LiveScreening />
      <TechSection />
      <Footer />
    </div>
  );
}
