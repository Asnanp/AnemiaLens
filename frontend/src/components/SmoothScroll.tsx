import { useEffect, useRef } from 'react';
import Lenis from 'lenis';
import { registerLenis } from '../utils/scroll';

export function SmoothScroll({ children }: { children: React.ReactNode }) {
  const lenisRef = useRef<Lenis | null>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isTouchViewport = window.matchMedia('(max-width: 900px)').matches;

    if (prefersReducedMotion) {
      registerLenis(null);
      return undefined;
    }

    const lenis = new Lenis({
      duration: isTouchViewport ? 0.82 : 1.05,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      orientation: 'vertical',
      gestureOrientation: 'vertical',
      smoothWheel: true,
      wheelMultiplier: 1,
      touchMultiplier: isTouchViewport ? 1.15 : 1.55,
      infinite: false,
    });

    lenisRef.current = lenis;
    registerLenis(lenis);

    let rafId = 0;
    function raf(time: number) {
      lenis.raf(time);
      rafId = requestAnimationFrame(raf);
    }

    rafId = requestAnimationFrame(raf);

    return () => {
      cancelAnimationFrame(rafId);
      registerLenis(null);
      lenis.destroy();
    };
  }, []);

  return <>{children}</>;
}
