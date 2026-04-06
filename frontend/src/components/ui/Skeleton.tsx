import { motion } from 'framer-motion';

interface SkeletonProps {
  variant?: 'text' | 'circular' | 'rectangular' | 'image';
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton({
  variant = 'text',
  width,
  height,
  borderRadius,
  className = '',
  style = {},
}: SkeletonProps) {
  const baseStyle: React.CSSProperties = {
    width,
    height,
    borderRadius: borderRadius ?? (variant === 'circular' ? '50%' : variant === 'image' ? '0.75rem' : '0.5rem'),
    background: 'linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.5s ease-in-out infinite',
    position: 'relative',
    overflow: 'hidden',
    ...style,
  };

  return (
    <div className={className} style={baseStyle}>
      <motion.div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent)',
        }}
        animate={{ x: ['-100%', '100%'] }}
        transition={{ duration: 2, ease: 'easeInOut', repeat: Infinity }}
      />
    </div>
  );
}

// Pre-built skeleton components for common use cases
export function SkeletonText({ lines = 3, className = '' }: { lines?: number; className?: string }) {
  return (
    <div className={className} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          variant="text"
          height="1rem"
          width={i === lines - 1 ? '60%' : '100%'}
        />
      ))}
    </div>
  );
}

export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={className} style={{ padding: '1.5rem', borderRadius: '1rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
      <Skeleton variant="text" width="40%" height="1.25rem" style={{ marginBottom: '1rem' }} />
      <SkeletonText lines={3} />
    </div>
  );
}

export function SkeletonMetric({ className = '' }: { className?: string }) {
  return (
    <div className={className} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
      <Skeleton variant="circular" width="80px" height="80px" />
      <Skeleton variant="text" width="60px" height="0.75rem" />
    </div>
  );
}
