import { motion } from 'framer-motion';
import React from 'react';

interface CardProps {
  children: React.ReactNode;
  variant?: 'default' | 'glass' | 'elevated' | 'bordered';
  hover?: boolean;
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
}

export function Card({
  children,
  variant = 'default',
  hover = false,
  className = '',
  style,
  onClick,
}: CardProps) {
  const baseStyles: React.CSSProperties = {
    borderRadius: 'var(--radius-xl)',
    transition: 'all 0.3s cubic-bezier(0.22, 1, 0.36, 1)',
    position: 'relative',
    overflow: 'hidden',
  };

  const variantStyles: Record<string, React.CSSProperties> = {
    default: {
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
    },
    glass: {
      background: 'var(--glass-white)',
      backdropFilter: 'blur(20px) saturate(180%)',
      WebkitBackdropFilter: 'blur(20px) saturate(180%)',
      border: '1px solid var(--glass-border)',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
    },
    elevated: {
      background: 'var(--color-surface)',
      boxShadow: 'var(--shadow-lg)',
    },
    bordered: {
      background: 'transparent',
      border: '1px solid var(--color-border)',
    },
  };

  const hoverStyles: React.CSSProperties = hover
    ? {
        cursor: 'pointer',
      }
    : {};

  const combinedStyle: React.CSSProperties = {
    ...baseStyles,
    ...variantStyles[variant],
    ...hoverStyles,
    ...style,
  };

  const Wrapper = onClick ? motion.div : 'div';
  const wrapperProps = onClick
    ? {
        whileHover: { y: -4, scale: 1.01 },
        whileTap: { scale: 0.99 },
        onClick,
      }
    : {};

  return (
    <Wrapper className={className} style={combinedStyle} {...wrapperProps}>
      {/* Top shine effect for glass cards */}
      {variant === 'glass' && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '1px',
            background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)',
            pointerEvents: 'none',
          }}
        />
      )}
      {children}
    </Wrapper>
  );
}
