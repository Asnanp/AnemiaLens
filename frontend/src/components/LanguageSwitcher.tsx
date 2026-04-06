import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { Languages, Check } from 'lucide-react';
import { SUPPORTED_LANGUAGES, type LanguageCode } from '../i18n';

const E = [0.22, 1, 0.36, 1] as const;

interface LanguageSwitcherProps {
  variant?: 'inline' | 'floating';
}

export function LanguageSwitcher({ variant = 'inline' }: LanguageSwitcherProps) {
  const { i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const current = SUPPORTED_LANGUAGES.find((l) => l.code === i18n.language) ?? SUPPORTED_LANGUAGES[0];

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selectLanguage = (code: LanguageCode) => {
    void i18n.changeLanguage(code);
    setOpen(false);
  };

  if (variant === 'floating') {
    return (
      <div ref={ref} style={{ position: 'relative', display: 'inline-block' }}>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label="Switch language"
          aria-expanded={open}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 0.85rem',
            borderRadius: '0.75rem',
            border: '1px solid rgba(255,255,255,0.1)',
            background: 'rgba(255,255,255,0.03)',
            color: 'var(--text-muted)',
            fontSize: '0.7rem',
            fontFamily: 'var(--mono)',
            cursor: 'pointer',
            transition: 'all 0.2s',
          }}
        >
          <Languages size={14} />
          <span>{current.native}</span>
        </button>

        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.96 }}
              transition={{ duration: 0.2, ease: E }}
              style={{
                position: 'absolute',
                bottom: 'calc(100% + 0.5rem)',
                left: 0,
                zIndex: 1000,
                minWidth: 160,
                borderRadius: '0.75rem',
                background: 'rgba(14,17,28,0.96)',
                backdropFilter: 'blur(24px)',
                border: '1px solid rgba(255,255,255,0.08)',
                boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
                overflow: 'hidden',
              }}
            >
              {SUPPORTED_LANGUAGES.map((lang) => {
                const active = lang.code === i18n.language;
                return (
                  <button
                    key={lang.code}
                    type="button"
                    onClick={() => selectLanguage(lang.code)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      width: '100%',
                      padding: '0.7rem 1rem',
                      border: 'none',
                      background: active ? 'rgba(200,0,30,0.12)' : 'transparent',
                      color: active ? 'var(--accent-bright)' : 'var(--text)',
                      fontSize: '0.78rem',
                      cursor: 'pointer',
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={(e) => {
                      if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                    }}
                    onMouseLeave={(e) => {
                      if (!active) e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <span>{lang.native}</span>
                    {active && <Check size={13} />}
                  </button>
                );
              })}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  // Inline variant — compact pill-style toggle
  return (
    <div
      ref={ref}
      style={{
        display: 'flex',
        borderRadius: '0.625rem',
        overflow: 'hidden',
        border: '1px solid rgba(255,255,255,0.1)',
      }}
    >
      {SUPPORTED_LANGUAGES.map((lang) => {
        const active = lang.code === i18n.language;
        return (
          <button
            key={lang.code}
            type="button"
            onClick={() => selectLanguage(lang.code)}
            style={{
              padding: '0.35rem 0.75rem',
              fontSize: '0.62rem',
              fontFamily: 'var(--mono)',
              fontWeight: 600,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              cursor: 'pointer',
              background: active ? 'rgba(200,0,30,0.2)' : 'rgba(255,255,255,0.03)',
              color: active ? 'var(--accent-bright)' : 'var(--text-dim)',
              border: 'none',
              transition: 'all 0.2s',
            }}
          >
            {lang.code.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}
