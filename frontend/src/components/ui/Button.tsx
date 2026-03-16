import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cn } from '../../utils';

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'icon';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    
    const variants = {
      primary: 'btn-premium-primary',
      secondary: 'btn-premium-secondary',
      ghost: 'bg-transparent hover:bg-white/5 text-text-secondary hover:text-white',
      outline: 'bg-transparent border border-white/10 hover:border-white/30 text-white',
      danger: 'bg-red-500/20 text-red-500 border border-red-500/30 hover:bg-red-500/30',
    };

    const sizes = {
      sm: 'px-4 py-1.5 text-xs',
      md: 'px-8 py-3 text-sm',
      lg: 'px-10 py-4 text-base',
      icon: 'p-2.5',
    };

    return (
      <Comp
        className={cn(
          'btn-premium inline-flex items-center justify-center whitespace-nowrap',
          variants[variant],
          sizes[size],
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button };
