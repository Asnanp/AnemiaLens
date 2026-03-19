/**
 * Lightweight toast notification system.
 * Usage: import { toast } from './Toast'; toast.success('Done!');
 */
import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
}

// Global state — simple pub/sub
let _listeners: Array<(t: ToastItem) => void> = [];
let _counter = 0;

function emit(type: ToastType, message: string) {
  const item: ToastItem = { id: `t${_counter++}`, type, message };
  _listeners.forEach(fn => fn(item));
}

export const toast = {
  success: (msg: string) => emit('success', msg),
  error: (msg: string) => emit('error', msg),
  warning: (msg: string) => emit('warning', msg),
  info: (msg: string) => emit('info', msg),
};

const COLORS: Record<ToastType, { bg: string; border: string; icon: string }> = {
  success: { bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.25)', icon: '#10B981' },
  error:   { bg: 'rgba(239,68,68,0.1)',  border: 'rgba(239,68,68,0.25)',  icon: '#EF4444' },
  warning: { bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.25)', icon: '#F59E0B' },
  info:    { bg: 'rgba(99,102,241,0.1)', border: 'rgba(99,102,241,0.25)', icon: '#818CF8' },
};

const ICONS: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle size={15} />,
  error:   <XCircle size={15} />,
  warning: <AlertTriangle size={15} />,
  info:    <Info size={15} />,
};

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const remove = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  useEffect(() => {
    const fn = (item: ToastItem) => {
      setToasts(prev => [...prev.slice(-4), item]); // max 5
      setTimeout(() => remove(item.id), 4000);
    };
    _listeners.push(fn);
    return () => { _listeners = _listeners.filter(l => l !== fn); };
  }, [remove]);

  return (
    <div style={{
      position: 'fixed', bottom: '1.5rem', right: '1.5rem',
      zIndex: 99999, display: 'flex', flexDirection: 'column', gap: '0.5rem',
      pointerEvents: 'none',
    }}>
      <AnimatePresence>
        {toasts.map(t => {
          const c = COLORS[t.type];
          return (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, x: 60, scale: 0.92 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 60, scale: 0.92 }}
              transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.625rem',
                padding: '0.75rem 1rem', borderRadius: '0.75rem',
                background: c.bg, border: `1px solid ${c.border}`,
                backdropFilter: 'blur(20px)',
                boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
                minWidth: 240, maxWidth: 340,
                pointerEvents: 'all',
              }}
            >
              <span style={{ color: c.icon, flexShrink: 0 }}>{ICONS[t.type]}</span>
              <span style={{ fontSize: '0.78rem', flex: 1, lineHeight: 1.4 }}>{t.message}</span>
              <button
                onClick={() => remove(t.id)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-dim)', padding: '0.1rem', flexShrink: 0 }}
              >
                <X size={12} />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
