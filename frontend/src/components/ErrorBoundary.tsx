import React from 'react';
import { ScanEye } from 'lucide-react';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  errorMessage: string | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, errorMessage: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[AnemiaLens] Rendering error:', error, info.componentStack);
  }

  handleRetry = () => {
    this.setState({ hasError: false, errorMessage: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--void, #04040A)',
          color: '#fff',
          fontFamily: 'system-ui, sans-serif',
        }}>
          <div style={{
            maxWidth: 480,
            textAlign: 'center',
            padding: '3rem 2rem',
            borderRadius: '1.5rem',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            backdropFilter: 'blur(20px)',
          }}>
            {/* Error icon */}
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              background: 'rgba(239,68,68,0.12)',
              border: '1px solid rgba(239,68,68,0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 1.5rem',
            }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2" strokeLinecap="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>

            <h2 style={{
              fontSize: '1.4rem', fontWeight: 700, marginBottom: '0.75rem',
              fontFamily: 'var(--serif, Georgia), serif',
            }}>
              Something went wrong
            </h2>

            <p style={{
              fontSize: '0.85rem', color: 'rgba(255,255,255,0.5)',
              lineHeight: 1.7, marginBottom: '0.75rem',
            }}>
              AnemiaLens encountered an unexpected error. Your data is safe — this is a display issue only.
            </p>

            {this.state.errorMessage && (
              <pre style={{
                fontSize: '0.65rem', color: 'rgba(239,68,68,0.7)',
                background: 'rgba(239,68,68,0.06)',
                borderRadius: '0.5rem', padding: '0.75rem',
                maxHeight: 80, overflow: 'auto',
                marginBottom: '1.5rem', textAlign: 'left',
                border: '1px solid rgba(239,68,68,0.15)',
                fontFamily: 'monospace',
              }}>
                {this.state.errorMessage}
              </pre>
            )}

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
              <button
                onClick={this.handleRetry}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  padding: '0.75rem 1.5rem', fontSize: '0.75rem',
                  fontWeight: 600, fontFamily: 'var(--mono, monospace)',
                  textTransform: 'uppercase', letterSpacing: '0.1em',
                  background: 'linear-gradient(135deg, #C8001E, #E8294A)',
                  color: '#fff', border: 'none', borderRadius: '0.75rem',
                  cursor: 'pointer', boxShadow: '0 4px 20px rgba(200,0,30,0.3)',
                }}
              >
                <ScanEye size={14} /> Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                style={{
                  padding: '0.75rem 1.5rem', fontSize: '0.75rem',
                  fontWeight: 600, fontFamily: 'var(--mono, monospace)',
                  textTransform: 'uppercase', letterSpacing: '0.1em',
                  background: 'rgba(255,255,255,0.06)',
                  color: 'rgba(255,255,255,0.6)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '0.75rem', cursor: 'pointer',
                }}
              >
                Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
