import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

export interface BentoCardProps extends Omit<HTMLMotionProps<"div">, "className"> {
  children: React.ReactNode;
  className?: string;
  glowColor?: string;
  hoverEffect?: boolean;
}

export const BentoCard = React.forwardRef<HTMLDivElement, BentoCardProps>(
  ({ children, className = '', glowColor = 'rgba(99, 102, 241, 0.15)', hoverEffect = true, ...props }, ref) => {
    return (
      <motion.div
        ref={ref}
        className={`relative rounded-3xl bg-surface border border-glass-medium overflow-hidden p-6 sm:p-8 backdrop-blur-glass ${className}`}
        whileHover={hoverEffect ? { y: -4, transition: { duration: 0.3 } } : undefined}
        {...props}
      >
        {hoverEffect && (
          <div 
            className="absolute -inset-px opacity-0 transition-opacity duration-500 hover:opacity-100 z-0 pointer-events-none rounded-[inherit]"
            style={{
              background: `radial-gradient(circle at 50% 0%, ${glowColor}, transparent 70%)`
            }}
          />
        )}
        <div className="absolute inset-0 bg-mesh-dark opacity-20 pointer-events-none z-0" />
        <div className="relative z-10 h-full flex flex-col">
          {children}
        </div>
      </motion.div>
    );
  }
);

BentoCard.displayName = 'BentoCard';
