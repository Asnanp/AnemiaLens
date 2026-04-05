import { useRef, useEffect, type ReactNode, type CSSProperties } from 'react';

interface TiltCardProps {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  tiltMax?: number;
  glowColor?: string;
}

/**
 * 3D tilt card with mouse-position-based perspective rotation,
 * glow highlight following cursor, and lift on hover.
 */
export function TiltCard({
  children,
  className = '',
  style = {},
  tiltMax = 6,
  glowColor = 'rgba(94,234,212,0.08)',
}: TiltCardProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const prefersReduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduce) return;

    let raf: number | null = null;

    const onMove = (e: MouseEvent) => {
      const r = el.getBoundingClientRect();
      const shimX = e.clientX - r.left;
      const shimY = e.clientY - r.top;
      const tiltX = ((shimY / r.height) - 0.5) * -tiltMax;
      const tiltY = ((shimX / r.width) - 0.5) * tiltMax;

      el.style.transform = `perspective(800px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translateY(-4px) scale(1.005)`;
      el.style.setProperty('--glow-x', `${shimX}px`);
      el.style.setProperty('--glow-y', `${shimY}px`);
    };

    const onLeave = () => {
      el.style.transform = 'perspective(800px) rotateX(0) rotateY(0) translateY(0) scale(1)';
      el.style.setProperty('--glow-x', '50%');
      el.style.setProperty('--glow-y', '50%');
      if (raf) { cancelAnimationFrame(raf); raf = null; }
    };

    el.addEventListener('mousemove', onMove, { passive: true });
    el.addEventListener('mouseleave', onLeave);
    return () => {
      el.removeEventListener('mousemove', onMove);
      el.removeEventListener('mouseleave', onLeave);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [tiltMax]);

  return (
    <div
      ref={ref}
      className={`glass glass-hover ${className}`}
      style={{
        ...style,
        '--glow-x': '50%',
        '--glow-y': '50%',
        transition: 'transform 0.45s cubic-bezier(0.22,1,0.36,1), box-shadow 0.45s',
      } as CSSProperties}
    >
      {/* Cursor-following glow */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: 'inherit',
          pointerEvents: 'none',
          zIndex: 4,
          background: `radial-gradient(280px at var(--glow-x, 50%) var(--glow-y, 50%), ${glowColor}, transparent 70%)`,
        }}
      />
      {children}
    </div>
  );
}
