import { useEffect, useRef } from 'react';

/**
 * Premium custom cursor with teal glow dot and lagging ring.
 * Hides automatically on touch devices via CSS.
 */
export function CustomCursor() {
  const dot = useRef<HTMLDivElement>(null);
  const ring = useRef<HTMLDivElement>(null);
  const pos = useRef({ x: -100, y: -100 });
  const rpos = useRef({ x: -100, y: -100 });

  useEffect(() => {
    // Skip on touch devices
    if (window.matchMedia('(hover: none)').matches) return;

    const onMove = (e: MouseEvent) => {
      pos.current = { x: e.clientX, y: e.clientY };
      if (e.target instanceof HTMLElement) {
        const isClickable = e.target.closest('button, a, input, [role="button"], label, select');
        if (isClickable && ring.current) {
          ring.current.classList.add('cursor-hover');
        } else if (ring.current) {
          ring.current.classList.remove('cursor-hover');
        }
      }
    };
    window.addEventListener('mousemove', onMove, { passive: true });

    let raf: number;
    const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

    const tick = () => {
      raf = requestAnimationFrame(tick);
      // Ring follows with more lag for premium feel
      rpos.current.x = lerp(rpos.current.x, pos.current.x, 0.08);
      rpos.current.y = lerp(rpos.current.y, pos.current.y, 0.08);

      if (dot.current) {
        dot.current.style.transform = `translate(calc(${pos.current.x}px - 50%), calc(${pos.current.y}px - 50%))`;
      }
      if (ring.current) {
        ring.current.style.transform = `translate(calc(${rpos.current.x}px - 50%), calc(${rpos.current.y}px - 50%))`;
      }
    };
    tick();

    return () => {
      window.removeEventListener('mousemove', onMove);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <>
      <div id="cursor-dot" ref={dot} />
      <div id="cursor-ring" ref={ring} />
    </>
  );
}
