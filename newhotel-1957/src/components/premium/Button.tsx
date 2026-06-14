/**
 * Premium Button Component with luxury aesthetic
 * Multiple variants, sizes, and states for consistent UI
 */

import { ButtonHTMLAttributes, forwardRef } from 'react';
import { motion } from 'framer-motion';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'luxury';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  loading?: boolean;
  fullWidth?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
}

const variantStyles = {
  primary: 'bg-gradient-to-r from-amber-500 to-amber-600 text-white shadow-lg shadow-amber-500/30 hover:shadow-xl hover:shadow-amber-500/40',
  secondary: 'bg-gradient-to-r from-stone-700 to-stone-800 text-white shadow-lg shadow-stone-700/30 hover:shadow-xl hover:shadow-stone-700/40',
  outline: 'border-2 border-amber-500 text-amber-700 hover:bg-amber-50 hover:border-amber-600',
  ghost: 'text-stone-700 hover:bg-stone-100 hover:text-stone-900',
  luxury: 'bg-gradient-to-r from-amber-400 via-amber-500 to-amber-600 text-white shadow-xl shadow-amber-500/40 hover:shadow-2xl hover:shadow-amber-500/50 border border-amber-400/30'
};

const sizeStyles = {
  sm: 'px-4 py-2 text-sm',
  md: 'px-6 py-2.5 text-base',
  lg: 'px-8 py-3 text-lg',
  xl: 'px-10 py-4 text-xl'
};

const loadingSpinner = (
  <svg 
    className="animate-spin h-4 w-4" 
    xmlns="http://www.w3.org/2000/svg" 
    fill="none" 
    viewBox="0 0 24 24"
  >
    <circle 
      className="opacity-25" 
      cx="12" 
      cy="12" 
      r="10" 
      stroke="currentColor" 
      strokeWidth="4"
    />
    <path 
      className="opacity-75" 
      fill="currentColor" 
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
    />
  </svg>
);

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      loading = false,
      disabled = false,
      fullWidth = false,
      icon,
      iconPosition = 'left',
      className = '',
      ...props
    },
    ref
  ) => {
    const baseStyles = 'relative inline-flex items-center justify-center font-semibold rounded-2xl transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';
    
    const combinedClassName = `${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${fullWidth ? 'w-full' : ''} ${className}`;

    const content = (
      <>
        {loading && loadingSpinner}
        {!loading && icon && iconPosition === 'left' && <span className="mr-2">{icon}</span>}
        {children}
        {!loading && icon && iconPosition === 'right' && <span className="ml-2">{icon}</span>}
      </>
    );

    return (
      <motion.button
        ref={ref}
        className={combinedClassName}
        disabled={disabled || loading}
        whileHover={!disabled && !loading ? { scale: 1.02 } : {}}
        whileTap={!disabled && !loading ? { scale: 0.98 } : {}}
        transition={{ type: 'spring', stiffness: 400, damping: 17 }}
        {...(props as any)}
      >
        {content}
      </motion.button>
    );
  }
);

Button.displayName = 'Button';