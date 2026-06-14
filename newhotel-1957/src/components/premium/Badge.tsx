/**
 * Premium Badge Component for status indicators and tags
 * Luxury aesthetic with subtle animations and glass effects
 */

import { HTMLAttributes, forwardRef } from 'react';
import { motion } from 'framer-motion';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'luxury';
  size?: 'sm' | 'md' | 'lg';
  rounded?: boolean;
  dot?: boolean;
}

const variantStyles = {
  default: 'bg-stone-100 text-stone-700 border-stone-200',
  success: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-100 text-amber-700 border-amber-200',
  error: 'bg-red-100 text-red-700 border-red-200',
  info: 'bg-blue-100 text-blue-700 border-blue-200',
  luxury: 'bg-gradient-to-r from-amber-100 to-amber-200 text-amber-800 border-amber-300'
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
  lg: 'px-4 py-1.5 text-base'
};

const dotColors = {
  default: 'bg-stone-400',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  error: 'bg-red-500',
  info: 'bg-blue-500',
  luxury: 'bg-amber-500'
};

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      children,
      variant = 'default',
      size = 'md',
      rounded = false,
      dot = false,
      className = '',
      ...props
    },
    ref
  ) => {
    const baseStyles = 'inline-flex items-center font-medium border transition-all duration-300';
    const roundedStyles = rounded ? 'rounded-full' : 'rounded-lg';
    const combinedClassName = `${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${roundedStyles} ${className}`;

    return (
      <motion.span
        ref={ref}
        className={combinedClassName}
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 400, damping: 17 }}
        {...(props as any)}
      >
        {dot && (
          <span className={`w-2 h-2 rounded-full mr-2 ${dotColors[variant]}`} />
        )}
        {children}
      </motion.span>
    );
  }
);

Badge.displayName = 'Badge';