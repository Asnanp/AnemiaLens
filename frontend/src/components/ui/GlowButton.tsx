import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

export interface GlowButtonProps extends Omit<HTMLMotionProps<"button">, "className"> {
  children: React.ReactNode;
  className?: string;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export const GlowButton = React.forwardRef<HTMLButtonElement, GlowButtonProps>(
  ({ children, className = '', variant = 'primary', size = 'md', ...props }, ref) => {
    const baseStyles = "relative inline-flex items-center justify-center font-medium transition-all duration-300 rounded-full focus:outline-none focus:ring-2 focus:ring-accent-primary focus:ring-offset-2 focus:ring-offset-background disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden";
    
    const sizeStyles = {
      sm: "px-4 py-2 text-sm",
      md: "px-6 py-3 text-base",
      lg: "px-8 py-4 text-lg",
    };

    const variantStyles = {
      primary: "text-white bg-accent-primary border border-accent-primary/50 shadow-[0_0_20px_rgba(99,102,241,0.3)] hover:shadow-[0_0_30px_rgba(99,102,241,0.5)] hover:bg-indigo-500",
      secondary: "text-white bg-surface border border-glass-high hover:bg-surfaceHover hover:border-accent-primary/50 shadow-[0_4px_14px_rgba(0,0,0,0.25)]",
      ghost: "text-text-secondary hover:text-white hover:bg-glass-light border border-transparent",
    };

    return (
      <motion.button
        ref={ref}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
        {...props}
      >
        <span className="relative z-10 flex items-center gap-2">
          {children}
        </span>
        {variant === 'primary' && (
          <div className="absolute inset-0 z-0 bg-gradient-to-r from-accent-primary via-brand-purple to-brand-teal opacity-0 transition-opacity duration-500 hover:opacity-100 mix-blend-overlay" />
        )}
      </motion.button>
    );
  }
);

GlowButton.displayName = 'GlowButton';
