/**
 * Premium Card Component with luxury aesthetic
 * Glass morphism, subtle animations, and elegant shadows
 */

import { HTMLAttributes, forwardRef } from 'react';
import { motion } from 'framer-motion';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'luxury' | 'minimal';
  hover?: boolean;
  clickable?: boolean;
  noPadding?: boolean;
}

const variantStyles = {
  default: 'bg-white border border-stone-200 shadow-lg',
  glass: 'bg-white/70 backdrop-blur-xl border border-white/20 shadow-xl',
  luxury: 'bg-gradient-to-br from-white via-stone-50 to-amber-50 border border-amber-200/50 shadow-2xl shadow-amber-900/10',
  minimal: 'bg-transparent border-0 shadow-none'
};

const hoverStyles = {
  default: 'hover:shadow-xl hover:border-amber-300 hover:-translate-y-1',
  glass: 'hover:bg-white/80 hover:shadow-2xl hover:-translate-y-1',
  luxury: 'hover:shadow-2xl hover:shadow-amber-900/20 hover:-translate-y-2',
  minimal: 'hover:bg-stone-50'
};

export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      variant = 'default',
      hover = false,
      clickable = false,
      noPadding = false,
      className = '',
      onClick,
      ...props
    },
    ref
  ) => {
    const baseStyles = 'rounded-3xl transition-all duration-500';
    const paddingStyles = noPadding ? '' : 'p-6';
    const cursorStyles = clickable ? 'cursor-pointer' : '';
    const interactiveStyles = hover ? hoverStyles[variant] : '';
    
    const combinedClassName = `${baseStyles} ${variantStyles[variant]} ${interactiveStyles} ${paddingStyles} ${cursorStyles} ${className}`;

    const motionProps = clickable ? {
      whileHover: { scale: 1.02 },
      whileTap: { scale: 0.98 },
      onClick
    } : {};

    return (
      <motion.div
        ref={ref}
        className={combinedClassName}
        {...motionProps}
        {...(props as any)}
      >
        {children}
      </motion.div>
    );
  }
);

Card.displayName = 'Card';

// Card sub-components for composition
export const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className = '', children, ...props }, ref) => (
    <div ref={ref} className={`mb-4 ${className}`} {...props}>
      {children}
    </div>
  )
);

CardHeader.displayName = 'CardHeader';

export const CardTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className = '', children, ...props }, ref) => (
    <h3 
      ref={ref} 
      className={`text-xl font-bold text-stone-900 font-display ${className}`} 
      {...props}
    >
      {children}
    </h3>
  )
);

CardTitle.displayName = 'CardTitle';

export const CardSubtitle = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className = '', children, ...props }, ref) => (
    <p 
      ref={ref} 
      className={`text-sm text-stone-600 mt-1 ${className}`} 
      {...props}
    >
      {children}
    </p>
  )
);

CardSubtitle.displayName = 'CardSubtitle';

export const CardBody = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className = '', children, ...props }, ref) => (
    <div ref={ref} className={`${className}`} {...props}>
      {children}
    </div>
  )
);

CardBody.displayName = 'CardBody';

export const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className = '', children, ...props }, ref) => (
    <div 
      ref={ref} 
      className={`mt-6 pt-4 border-t border-stone-200 flex items-center justify-between ${className}`} 
      {...props}
    >
      {children}
    </div>
  )
);

CardFooter.displayName = 'CardFooter';