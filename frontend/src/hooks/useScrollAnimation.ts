/**
 * Premium scroll-driven animation hooks for AnemiaLens.
 *
 * Three hooks:
 *   1. useScrollReveal    - Intersection Observer with spring-style entrance presets
 *   2. useParallax        - Parallax offset for background elements
 *   3. useScrollProgress  - Per-section scroll progress tracking
 */

import { useRef, useCallback, useMemo, useEffect } from 'react';
import {
  useInView,
  useScroll,
  useSpring,
  useTransform,
  useMotionValue,
  type SpringOptions,
  type MotionValue,
} from 'framer-motion';

/* ------------------------------------------------------------------ */
/*  SPRING PRESETS                                                     */
/* ------------------------------------------------------------------ */

const SPRING_PRESETS = {
  gentle:  { stiffness: 80,  damping: 22, mass: 0.9 } as SpringOptions,
  default: { stiffness: 120, damping: 18, mass: 0.8 } as SpringOptions,
  snappy:  { stiffness: 200, damping: 14, mass: 0.6 } as SpringOptions,
  bouncy:  { stiffness: 160, damping: 10, mass: 0.7 } as SpringOptions,
  stiff:   { stiffness: 300, damping: 24, mass: 0.5 } as SpringOptions,
} as const;

export type SpringPreset = keyof typeof SPRING_PRESETS;

/* ------------------------------------------------------------------ */
/*  Shared scroll offset type                                          */
/* ------------------------------------------------------------------ */

type ScrollOffset =
  | 'start' | 'end' | 'center'
  | 'start start' | 'start center' | 'start end'
  | 'center start' | 'center center' | 'center end'
  | 'end start' | 'end center' | 'end end';

/* ------------------------------------------------------------------ */
/*  1. useScrollReveal - Intersection Observer hook                    */
/* ------------------------------------------------------------------ */

export interface UseScrollRevealOptions {
  /** Distance to travel on entrance (px). Default 64 */
  distance?: number;
  /** Stagger delay per sibling (ms). Default 0 */
  stagger?: number;
  /** Index for stagger calculations */
  index?: number;
  /** Animation direction */
  direction?: 'up' | 'down' | 'left' | 'right' | 'scale' | 'none';
  /** Whether to animate only once */
  once?: boolean;
  /** Intersection threshold (0-1). Default 0.15 */
  threshold?: number;
  /** Spring preset name or custom config */
  spring?: SpringPreset | SpringOptions;
  /** Initial opacity before reveal. Default 0 */
  initialOpacity?: number;
}

export interface ScrollRevealState {
  ref: React.RefObject<HTMLDivElement>;
  isInView: boolean;
  y: MotionValue<number>;
  x: MotionValue<number>;
  opacity: MotionValue<number>;
  scale: MotionValue<number>;
  delay: number;
}

export function useScrollReveal({
  distance = 64,
  stagger = 0,
  index = 0,
  direction = 'up',
  once = true,
  threshold = 0.15,
  spring = 'default',
  initialOpacity = 0,
}: UseScrollRevealOptions = {}): ScrollRevealState {
  const ref = useRef<HTMLDivElement>(null!);
  const isInView = useInView(ref, { once, amount: threshold });
  const delay = stagger * index;

  const springConfig = typeof spring === 'string'
    ? SPRING_PRESETS[spring]
    : spring;

  const rawY = useMotionValue(direction === 'up' ? distance : direction === 'down' ? -distance : 0);
  const rawX = useMotionValue(direction === 'left' ? distance : direction === 'right' ? -distance : 0);
  const rawOpacity = useMotionValue(initialOpacity);
  const rawScale = useMotionValue(direction === 'scale' ? 0.85 : 1);

  const springY = useSpring(rawY, springConfig);
  const springX = useSpring(rawX, springConfig);
  const springOpacity = useSpring(rawOpacity, springConfig);
  const springScale = useSpring(rawScale, { ...springConfig, stiffness: 180, damping: 16 });

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (isInView) {
        rawY.set(0);
        rawX.set(0);
        rawOpacity.set(1);
        rawScale.set(1);
      } else if (!once) {
        rawY.set(direction === 'up' ? distance : direction === 'down' ? -distance : 0);
        rawX.set(direction === 'left' ? distance : direction === 'right' ? -distance : 0);
        rawOpacity.set(initialOpacity);
        rawScale.set(direction === 'scale' ? 0.85 : 1);
      }
    }, delay);
    return () => clearTimeout(timeout);
  }, [isInView, once, delay, direction, distance, initialOpacity, rawY, rawX, rawOpacity, rawScale]);

  return { ref, isInView, y: springY, x: springX, opacity: springOpacity, scale: springScale, delay };
}

/* ------------------------------------------------------------------ */
/*  2. useParallax - Parallax offset for background elements           */
/* ------------------------------------------------------------------ */

export interface UseParallaxOptions {
  /** Parallax speed factor. 0 = locked, 1 = 1:1 scroll, 2 = 2x scroll. Default 0.4 */
  speed?: number;
  /** Spring preset or custom config. Default 'gentle' */
  spring?: SpringPreset | SpringOptions;
  /** Clamp output range [min, max] in px. Default [-200, 200] */
  range?: [number, number];
  /** Scroll container offset. Default ['start end', 'end start'] */
  offset?: [ScrollOffset, ScrollOffset];
}

export interface ParallaxState {
  ref: React.RefObject<HTMLDivElement>;
  y: MotionValue<number>;
  scrollYProgress: MotionValue<number>;
}

export function useParallax({
  speed = 0.4,
  spring = 'gentle',
  range = [-200, 200],
  offset = ['start end', 'end start'],
}: UseParallaxOptions = {}): ParallaxState {
  const ref = useRef<HTMLDivElement>(null!);
  const { scrollYProgress } = useScroll({ target: ref, offset });

  const springConfig = typeof spring === 'string'
    ? SPRING_PRESETS[spring]
    : spring;

  const rawY = useTransform(scrollYProgress, [0, 1], [0, speed * 500]);
  const clampedY = useTransform(rawY, (v: number) => Math.min(range[1], Math.max(range[0], v)));
  const y = useSpring(clampedY, springConfig);

  return { ref, y, scrollYProgress };
}

/* ------------------------------------------------------------------ */
/*  3. useScrollProgress - Per-section progress tracking               */
/* ------------------------------------------------------------------ */

export interface UseScrollProgressOptions {
  spring?: SpringPreset | SpringOptions;
  offset?: [ScrollOffset, ScrollOffset];
}

export interface ScrollProgressState {
  ref: React.RefObject<HTMLDivElement>;
  progress: MotionValue<number>;
  rawProgress: MotionValue<number>;
  progressPct: MotionValue<string>;
}

export function useScrollProgress({
  spring = 'stiff',
  offset = ['start end', 'end start'],
}: UseScrollProgressOptions = {}): ScrollProgressState {
  const ref = useRef<HTMLDivElement>(null!);
  const { scrollYProgress } = useScroll({ target: ref, offset });

  const springConfig = typeof spring === 'string'
    ? SPRING_PRESETS[spring]
    : spring;

  const progress = useSpring(scrollYProgress, springConfig);
  const progressPct = useTransform(scrollYProgress, (v: number) => `${Math.round(v * 100)}%`);

  return { ref, progress, rawProgress: scrollYProgress, progressPct };
}

/* ------------------------------------------------------------------ */
/*  UTILITY: Staggered children helper                                 */
/* ------------------------------------------------------------------ */

export function useStaggeredReveal(
  count: number,
  options?: Omit<UseScrollRevealOptions, 'index' | 'stagger'> & { staggerMs?: number }
): ScrollRevealState[] {
  const staggerMs = options?.staggerMs ?? 80;

  return useMemo(
    () =>
      Array.from({ length: count }, (_, i) =>
        useScrollReveal({ ...options, index: i, stagger: staggerMs })
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [count, staggerMs, options?.distance, options?.direction, options?.once, options?.threshold, options?.spring]
  );
}
