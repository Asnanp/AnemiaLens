import React, { useRef, useState, useEffect } from 'react';
import { motion, useSpring, useTransform, useReducedMotion } from 'framer-motion';
import { useRipple } from './RippleEffect';
import { E } from './screening/SharedUI';

import { HTMLMotionProps } from 'framer-motion';

interface MagneticButtonProps extends HTMLMotionProps<"button"> {
  children: React.ReactNode;
  className?: string;
  magneticStrength?: number;
}

export function MagneticButton({
  children,
  className = '',
  magneticStrength = 15,
  onClick,
  onPointerMove,
  onPointerLeave,
  ...props
}: MagneticButtonProps) {
  const ref = useRef<HTMLButtonElement>(null);
  const reduceMotion = useReducedMotion();
  const { addRipple, RippleElements } = useRipple();
  
  const [hovered, setHovered] = useState(false);

  const mouseX = useSpring(0, { stiffness: 150, damping: 15, mass: 0.5 });
  const mouseY = useSpring(0, { stiffness: 150, damping: 15, mass: 0.5 });

  const handlePointerMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (reduceMotion) return;
    const { clientX, clientY } = e;
    const { left, top, width, height } = e.currentTarget.getBoundingClientRect();
    const centerX = left + width / 2;
    const centerY = top + height / 2;
    // Calculate the distance from center
    const x = ((clientX - centerX) / width) * magneticStrength;
    const y = ((clientY - centerY) / height) * magneticStrength;

    mouseX.set(x);
    mouseY.set(y);
    setHovered(true);
    
    onPointerMove?.(e);
  };

  const handlePointerLeave = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (reduceMotion) return;
    mouseX.set(0);
    mouseY.set(0);
    setHovered(false);
    
    onPointerLeave?.(e);
  };
  
  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    addRipple(e);
    onClick?.(e);
  };

  return (
    <motion.button
      ref={ref}
      className={`btn ${className}`}
      onClick={handleClick}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      style={{
        x: reduceMotion ? 0 : mouseX,
        y: reduceMotion ? 0 : mouseY,
      }}
      whileTap={reduceMotion ? undefined : { scale: 0.97 }}
      {...props}
    >
      {RippleElements}
      <div style={{ position: 'relative', zIndex: 1, display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
        {children}
      </div>
    </motion.button>
  );
}
