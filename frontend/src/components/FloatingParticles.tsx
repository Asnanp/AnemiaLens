import { useEffect, useRef, useCallback } from 'react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  alpha: number;
  baseAlpha: number;
  color: string;
  pulse: number;
  pulseSpeed: number;
}

interface FloatingParticlesProps {
  count?: number;
  colors?: string[];
  className?: string;
  style?: React.CSSProperties;
}

const DEFAULT_COLORS = [
  'rgba(94, 234, 212, VAL)',   // teal
  'rgba(200, 0, 30, VAL)',    // crimson
  'rgba(255, 107, 138, VAL)', // pink-glow
  'rgba(255, 255, 255, VAL)', // white
];

export function FloatingParticles({
  count = 40,
  colors = DEFAULT_COLORS,
  className,
  style,
}: FloatingParticlesProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const rafRef = useRef(0);
  const scrollRef = useRef(0);

  const initParticles = useCallback(
    (width: number, height: number) => {
      const particles: Particle[] = [];
      for (let i = 0; i < count; i++) {
        const baseAlpha = 0.12 + Math.random() * 0.22;
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.25,
          vy: (Math.random() - 0.5) * 0.18 - 0.06,
          radius: 1.2 + Math.random() * 2.8,
          alpha: baseAlpha,
          baseAlpha,
          color: colors[Math.floor(Math.random() * colors.length)],
          pulse: Math.random() * Math.PI * 2,
          pulseSpeed: 0.008 + Math.random() * 0.018,
        });
      }
      particlesRef.current = particles;
    },
    [count, colors],
  );

  useEffect(() => {
    const prefersReduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduce) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let dpr = window.devicePixelRatio || 1;
    let width = 0;
    let height = 0;

    const resize = () => {
      dpr = window.devicePixelRatio || 1;
      const rect = canvas.parentElement?.getBoundingClientRect();
      width = rect?.width ?? window.innerWidth;
      height = rect?.height ?? window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      if (particlesRef.current.length === 0) {
        initParticles(width, height);
      }
    };

    const onScroll = () => {
      scrollRef.current = window.scrollY / (document.body.scrollHeight - window.innerHeight);
    };

    resize();
    window.addEventListener('resize', resize, { passive: true });
    window.addEventListener('scroll', onScroll, { passive: true });

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      const scroll = scrollRef.current;

      for (const p of particlesRef.current) {
        p.pulse += p.pulseSpeed;
        const pulseFactor = 0.7 + 0.3 * Math.sin(p.pulse);
        const scrollInfluence = 1 - Math.abs(scroll - 0.5) * 0.4;
        const alpha = p.baseAlpha * pulseFactor * scrollInfluence;

        p.x += p.vx;
        p.y += p.vy + scroll * -0.15;

        // Wrap around
        if (p.x < -10) p.x = width + 10;
        if (p.x > width + 10) p.x = -10;
        if (p.y < -10) p.y = height + 10;
        if (p.y > height + 10) p.y = -10;

        const colorStr = p.color.replace('VAL', String(alpha));

        // Soft glow
        ctx.beginPath();
        const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.radius * 3);
        gradient.addColorStop(0, colorStr);
        gradient.addColorStop(1, 'transparent');
        ctx.fillStyle = gradient;
        ctx.arc(p.x, p.y, p.radius * 3, 0, Math.PI * 2);
        ctx.fill();

        // Core dot
        ctx.beginPath();
        ctx.fillStyle = colorStr;
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fill();
      }

      // Draw connections (neural/plexus effect)
      for (let i = 0; i < particlesRef.current.length; i++) {
        for (let j = i + 1; j < particlesRef.current.length; j++) {
          const p1 = particlesRef.current[i];
          const p2 = particlesRef.current[j];
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const distSq = dx * dx + dy * dy;
          // Connecting range ~120px
          if (distSq < 14400) {
            const dist = Math.sqrt(distSq);
            // Opacity scales down inversely with distance
            const linkAlpha = (1 - dist / 120) * 0.15;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = p1.color.replace('VAL', String(linkAlpha));
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }
      }

      rafRef.current = requestAnimationFrame(draw);
    };

    rafRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('resize', resize);
      window.removeEventListener('scroll', onScroll);
    };
  }, [initParticles]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 0,
        ...style,
      }}
      aria-hidden="true"
    />
  );
}
