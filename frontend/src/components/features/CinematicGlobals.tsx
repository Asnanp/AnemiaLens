import React, { useEffect, useState } from 'react';
import { motion, useSpring } from 'framer-motion';

export function MagneticCursor() {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);

  const cursorX = useSpring(mousePosition.x, { stiffness: 500, damping: 28, mass: 0.5 });
  const cursorY = useSpring(mousePosition.y, { stiffness: 500, damping: 28, mass: 0.5 });

  useEffect(() => {
    const updateMousePosition = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
      
      // Check if hovering over a magnetic element (buttons, links, glass cards)
      const target = e.target as HTMLElement;
      const isMagnetic = target.closest('button, a, .magnetic, .glass');
      setIsHovering(!!isMagnetic);
    };

    window.addEventListener('mousemove', updateMousePosition);
    return () => window.removeEventListener('mousemove', updateMousePosition);
  }, []);

  // Avoid rendering on touch devices
  if (typeof window !== 'undefined' && 'ontouchstart' in window) return null;

  return (
    <>
      <motion.div
        style={{
          position: 'fixed',
          top: -10, left: -10,
          width: 20, height: 20,
          borderRadius: '50%',
          backgroundColor: isHovering ? 'transparent' : 'rgba(255, 255, 255, 0.4)',
          border: isHovering ? '1px solid rgba(255,255,255,0.8)' : 'none',
          pointerEvents: 'none',
          zIndex: 99999,
          mixBlendMode: 'difference',
          x: cursorX,
          y: cursorY,
          scale: isHovering ? 2.5 : 1,
          transition: 'scale 0.15s ease-out, background-color 0.15s ease-out',
        }}
      />
      <motion.div
        style={{
          position: 'fixed',
          top: -150, left: -150,
          width: 300, height: 300,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(255,255,255,0.03) 0%, transparent 70%)',
          pointerEvents: 'none',
          zIndex: 99998,
          x: cursorX,
          y: cursorY,
          scale: isHovering ? 1.5 : 1,
          transition: 'scale 0.5s cubic-bezier(0.22, 1, 0.36, 1)',
        }}
      />
    </>
  );
}

export function GlobalCinematicBackground() {
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: -1, overflow: 'hidden', background: '#010204', pointerEvents: 'none' }}>
      <motion.div
        animate={{
          x: ['-5%', '5%', '-5%'],
          y: ['-5%', '5%', '-5%'],
          rotate: [0, 10, -10, 0]
        }}
        transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
        style={{
          position: 'absolute',
          top: '-20%', left: '-10%',
          width: '70vw', height: '70vw',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(190, 18, 60, 0.08) 0%, transparent 60%)',
          filter: 'blur(100px)',
          opacity: 0.6,
        }}
      />
      <motion.div
        animate={{
          x: ['5%', '-5%', '5%'],
          y: ['5%', '-5%', '5%'],
          rotate: [0, -10, 10, 0]
        }}
        transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
        style={{
          position: 'absolute',
          bottom: '-20%', right: '-10%',
          width: '60vw', height: '60vw',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(37, 99, 235, 0.05) 0%, transparent 60%)',
          filter: 'blur(100px)',
          opacity: 0.6,
        }}
      />
      
      {/* Film Grain overlay for premium texture */}
      <div style={{
        position: 'absolute',
        inset: 0,
        opacity: 0.03,
        pointerEvents: 'none',
        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
      }} />
    </div>
  );
}
