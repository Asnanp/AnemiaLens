import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';
import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
  size?: 'sm' | 'md' | 'lg';
  icon?: LucideIcon;
  iconPosition?: 'left' | 'right';
  loading?: boolean;
  fullWidth?: boolean;
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon: Icon,
  iconPosition = 'left',
  loading = false,
  fullWidth = false,
  disabled,
  className = '',
  style,
  ...props
}: ButtonProps) {
  const baseStyles: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.5rem',
    fontFamily: 'var(--font-sans)',
    fontWeight: 600,
    border: 'none',
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    transition: 'all 0.3s cubic-bezier(0.22, 1, 0.36, 1)',
    position: 'relative',
    overflow: 'hidden',
    width: fullWidth ? '100%' : 'auto',
    opacity: disabled ? 0.5 : 1,
  };

  const sizeStyles: Record<string, React.CSSProperties> = {
    sm: { padding: '0.5rem 1rem', fontSize: '0.875rem', borderRadius: 'var(--radius-md)' },
    md: { padding: '0.75rem 1.5rem', fontSize: '0.9375rem', borderRadius: 'var(--radius-lg)' },
    lg: { padding: '1rem 2rem', fontSize: '1rem', borderRadius: 'var(--radius-xl)' },
  };

  const variantStyles: Record<string, React.CSSProperties> = {
    primary: {
      background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%)',
      color: 'white',
      boxShadow: '0 4px 20px rgba(200, 0, 30, 0.3)',
    },
    secondary: {
      background: 'rgba(255, 255, 255, 0.05)',
      color: 'var(--color-text)',
      border: '1px solid var(--color-border)',
      backdropFilter: 'blur(10px)',
    },
    ghost: {
      background: 'transparent',
      color: 'var(--color-text-secondary)',
    },
    danger: {
      background: 'linear-gradient(135deg, var(--color-error) 0%, var(--color-error-light) 100%)',
      color: 'white',
      boxShadow: '0 4px 20px rgba(239, 68, 68, 0.3)',
    },
    success: {
      background: 'linear-gradient(135deg, var(--color-success) 0%, var(--color-success-light) 100%)',
      color: 'white',
      boxShadow: '0 4px 20px rgba(16, 185, 129, 0.3)',
    },
  };

  const combinedStyle: React.CSSProperties = {
    ...baseStyles,
    ...sizeStyles[size],
    ...variantStyles[variant],
    ...style,
  };

  const motionProps = !disabled && !loading
    ? { whileHover: { scale: 1.02, y: -2 } as const, whileTap: { scale: 0.98 } as const }
    : {};

  return (
    <motion.button
      className={className}
      style={combinedStyle}
      {...(motionProps as any)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          style={{ width: '1em', height: '1em', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%' }}
        />
      )}
      {!loading && Icon && iconPosition === 'left' && <Icon size={16} />}
      {children}
      {!loading && Icon && iconPosition === 'right' && <Icon size={16} />}
    </motion.button>
  );
}
