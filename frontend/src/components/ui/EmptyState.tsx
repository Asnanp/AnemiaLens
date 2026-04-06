import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}: EmptyStateProps) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '4rem 2rem',
        textAlign: 'center',
        minHeight: '400px',
      }}
    >
      {Icon && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
          style={{
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.06)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '1.5rem',
          }}
        >
          <Icon size={32} style={{ color: 'var(--text-muted)' }} />
        </motion.div>
      )}
      
      <h3 style={{
        fontFamily: 'var(--serif)',
        fontSize: '1.5rem',
        fontWeight: 600,
        color: 'var(--text)',
        marginBottom: '0.75rem',
      }}>
        {title}
      </h3>
      
      <p style={{
        fontSize: '0.95rem',
        color: 'var(--text-secondary)',
        lineHeight: 1.6,
        maxWidth: '400px',
        marginBottom: actionLabel ? '2rem' : 0,
      }}>
        {description}
      </p>
      
      {actionLabel && onAction && (
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onAction}
          style={{
            padding: '0.875rem 2rem',
            borderRadius: '999px',
            background: 'linear-gradient(135deg, var(--crimson) 0%, var(--crimson-bright) 100%)',
            color: 'white',
            border: 'none',
            fontSize: '0.9rem',
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 4px 20px rgba(200, 0, 30, 0.3)',
          }}
        >
          {actionLabel}
        </motion.button>
      )}
    </motion.div>
  );
}
