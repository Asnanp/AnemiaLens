/**
 * Physics-based spring animation utilities for AnemiaLens.
 *
 * Provides spring presets, micro-interaction variants, and
 * composition helpers built on framer-motion spring physics.
 */

import { type TargetAndTransition, type SpringOptions, type Variants } from 'framer-motion';

/* ─────────────────────────────────────────────────────────── */
/*  SPRING PRESETS                                              */
/* ─────────────────────────────────────────────────────────── */

export const springPresets = {
  /** Soft, gentle entrance – good for large sections */
  gentle: { stiffness: 80, damping: 22, mass: 0.9 } as SpringOptions,
  /** Balanced default – good for cards and panels */
  default: { stiffness: 120, damping: 18, mass: 0.8 } as SpringOptions,
  /** Quick and responsive – good for buttons and chips */
  snappy: { stiffness: 200, damping: 14, mass: 0.6 } as SpringOptions,
  /** Playful overshoot – good for decorative elements */
  bouncy: { stiffness: 160, damping: 10, mass: 0.7 } as SpringOptions,
  /** Tight, no-overshoot – good for progress bars and rails */
  stiff: { stiffness: 300, damping: 24, mass: 0.5 } as SpringOptions,
} as const;

export type SpringPresetKey = keyof typeof springPresets;

/** Resolve a preset name or passthrough a custom config */
export function resolveSpring(config: SpringPresetKey | SpringOptions): SpringOptions {
  if (typeof config === 'string') return springPresets[config];
  return config;
}

/* ─────────────────────────────────────────────────────────── */
/*  MICRO-INTERACTION VARIANTS                                  */
/* ─────────────────────────────────────────────────────────── */

/** Button tap + hover spring micro-interaction */
export const buttonSpring = {
  rest: { scale: 1, y: 0 } as TargetAndTransition,
  hover: { scale: 1.025, y: -2 } as TargetAndTransition,
  tap: { scale: 0.97, y: 1 } as TargetAndTransition,
} satisfies { rest: TargetAndTransition; hover: TargetAndTransition; tap: TargetAndTransition };

/** Card lift on hover with subtle glow */
export const cardLiftSpring = {
  rest: { y: 0, scale: 1 } as TargetAndTransition,
  hover: { y: -6, scale: 1.01 } as TargetAndTransition,
  tap: { y: 0, scale: 0.99 } as TargetAndTransition,
} satisfies { rest: TargetAndTransition; hover: TargetAndTransition; tap: TargetAndTransition };

/** Staggered list item entrance */
export function staggerListVariants({
  distance = 32,
  spring = 'default',
}: { distance?: number; spring?: SpringPresetKey } = {}): Variants {
  const springConfig = resolveSpring(spring);
  return {
    hidden: { opacity: 0, y: distance },
    visible: (i: number = 0) => ({
      opacity: 1,
      y: 0,
      transition: {
        delay: i * 0.08,
        ...springConfig,
      },
    }),
  };
}

/** Feature card fan-out entrance */
export function fanOutVariants({
  distance = 48,
  spring = 'default',
  staggerMs = 100,
}: { distance?: number; spring?: SpringPresetKey; staggerMs?: number } = {}): Variants {
  const springConfig = resolveSpring(spring);
  return {
    hidden: { opacity: 0, y: distance, scale: 0.92 },
    visible: (i: number = 0) => ({
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        delay: i * staggerMs / 1000,
        ...springConfig,
      },
    }),
  };
}

/** Orbital float – gentle continuous motion for decorative orbs */
export function orbitalFloat({
  amplitude = 12,
  duration = 6,
}: { amplitude?: number; duration?: number } = {}): TargetAndTransition {
  return {
    y: [0, -amplitude, 0],
    x: [0, amplitude * 0.4, 0],
    transition: {
      duration,
      repeat: Infinity,
      ease: 'easeInOut' as const,
    },
  };
}

/** Pulse glow – scale + opacity pulse for CTA emphasis */
export function pulseGlow({
  duration = 2.5,
  scale = 1.08,
  opacity = 0.5,
}: { duration?: number; scale?: number; opacity?: number } = {}): TargetAndTransition {
  return {
    scale: [1, scale, 1],
    opacity: [opacity * 0.5, opacity, opacity * 0.5],
    transition: {
      duration,
      repeat: Infinity,
      ease: 'easeInOut' as const,
    },
  };
}

/* ─────────────────────────────────────────────────────────── */
/*  SPRING TRANSITION SHORTCUTS                                 */
/* ─────────────────────────────────────────────────────────── */

/** Quick spring transition for `whileHover` / `whileTap` */
export function springTransition(preset: SpringPresetKey | SpringOptions = 'snappy') {
  return { type: 'spring' as const, ...resolveSpring(preset) };
}

/** Smooth spring transition for section-level layout changes */
export function layoutSpring(preset: SpringPresetKey | SpringOptions = 'default') {
  return { type: 'spring' as const, ...resolveSpring(preset), layout: true };
}
