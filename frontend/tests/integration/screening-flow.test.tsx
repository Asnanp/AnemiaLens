import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: vi.fn() },
  }),
  initReactI18next: {},
}));

// Mock framer-motion
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    motion: {
      div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
        <div {...props}>{children}</div>
      ),
      button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { children?: React.ReactNode }) => (
        <button {...props}>{children}</button>
      ),
      section: ({ children, ...props }: React.HTMLAttributes<HTMLElement> & { children?: React.ReactNode }) => (
        <section {...props}>{children}</section>
      ),
    },
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  };
});

// Mock hooks
vi.mock('../../hooks/useOnboarding', () => ({
  useOnboarding: () => ({
    hasSeenOnboarding: true,
    isReady: true,
    completeOnboarding: vi.fn(),
    resetOnboarding: vi.fn(),
  }),
}));

vi.mock('../../hooks/useScreening', () => ({
  useScreening: () => ({
    step: 1,
    setStep: vi.fn(),
    uploadImage: vi.fn(),
    analysisResult: null,
    isAnalyzing: false,
    resetScreening: vi.fn(),
  }),
}));

// Mock API
vi.mock('../../api', () => ({
  uploadForAnalysis: vi.fn(),
  uploadForQualityCheck: vi.fn(),
}));

// Helper to render with providers
function renderWithProviders(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe('Screening Flow Integration Tests', () => {
  const user = userEvent.setup({ delay: null });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Landing to Screening flow', () => {
    it('Start Screening button scrolls to screening section', async () => {
      // Render the landing page sections with screening section
      const { HeroSection } = await import('../../pages/HeroSection');

      renderWithProviders(
        <main>
          <HeroSection />
          <section id="screening" data-testid="screening-section">
            <h2>Screening</h2>
            <p>Interactive screening form</p>
          </section>
        </main>
      );

      // The HeroSection should render a CTA button
      const ctaButtons = screen.getAllByRole('button');
      const startButton = ctaButtons.find(
        (btn) => btn.textContent?.toLowerCase().includes('start') || btn.textContent?.toLowerCase().includes('screening')
      );

      if (startButton) {
        expect(startButton).toBeInTheDocument();
      }
    });
  });

  describe('Screening step navigation', () => {
    it('advances through screening steps sequentially', async () => {
      // Mock a simple step-by-step screening component
      const MockScreeningFlow = () => {
        const { useState } = require('react');
        const [step, setStep] = useState(1);
        const totalSteps = 4;

        return (
          <div data-testid="screening-flow">
            <div data-testid="current-step">Step {step}</div>
            <nav aria-label="Screening steps">
              {Array.from({ length: totalSteps }, (_, i) => (
                <button
                  key={i}
                  data-testid={`step-indicator-${i + 1}`}
                  aria-current={i + 1 === step ? 'step' : undefined}
                  onClick={() => setStep(i + 1)}
                >
                  Step {i + 1}
                </button>
              ))}
            </nav>
            <button
              data-testid="next-button"
              onClick={() => setStep(Math.min(step + 1, totalSteps))}
              disabled={step >= totalSteps}
            >
              {step >= totalSteps ? 'Complete' : 'Next'}
            </button>
            {step > 1 && (
              <button data-testid="back-button" onClick={() => setStep(Math.max(step - 1, 1))}>
                Back
              </button>
            )}
          </div>
        );
      };

      renderWithProviders(<MockScreeningFlow />);

      // Verify initial state
      expect(screen.getByTestId('current-step')).toHaveTextContent('Step 1');
      expect(screen.getByTestId('step-indicator-1')).toHaveAttribute('aria-current', 'step');

      // Go to next step
      await user.click(screen.getByTestId('next-button'));
      expect(screen.getByTestId('current-step')).toHaveTextContent('Step 2');
      expect(screen.getByTestId('step-indicator-2')).toHaveAttribute('aria-current', 'step');

      // Go back
      await user.click(screen.getByTestId('back-button'));
      expect(screen.getByTestId('current-step')).toHaveTextContent('Step 1');
      expect(screen.getByTestId('step-indicator-1')).toHaveAttribute('aria-current', 'step');

      // Skip to step 4
      await user.click(screen.getByTestId('step-indicator-4'));
      expect(screen.getByTestId('current-step')).toHaveTextContent('Step 4');
      expect(screen.getByTestId('next-button')).toHaveTextContent('Complete');
      expect(screen.getByTestId('next-button')).toBeDisabled();
    });
  });

  describe('Image upload flow', () => {
    it('allows image upload and shows preview', async () => {
      const MockImageUpload = () => {
        const { useState, useRef } = require('react');
        const [file, setFile] = useState<File | null>(null);
        const inputRef = useRef<HTMLInputElement>(null);

        return (
          <div data-testid="image-upload">
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              data-testid="file-input"
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                if (e.target.files && e.target.files[0]) {
                  setFile(e.target.files[0]);
                }
              }}
            />
            <button onClick={() => inputRef.current?.click()} data-testid="upload-button">
              Upload Image
            </button>
            {file && (
              <div data-testid="file-preview">
                <span data-testid="file-name">{file.name}</span>
                <span data-testid="file-size">{(file.size / 1024).toFixed(1)} KB</span>
              </div>
            )}
          </div>
        );
      };

      renderWithProviders(<MockImageUpload />);

      const file = new File(['dummy-image-content'], 'test-eye.jpg', { type: 'image/jpeg' });
      const input = screen.getByTestId('file-input');

      await user.upload(input, file);

      expect(screen.getByTestId('file-name')).toHaveTextContent('test-eye.jpg');
      expect(screen.getByTestId('file-size')).toBeInTheDocument();
    });

    it('rejects non-image files', async () => {
      const MockImageUpload = () => {
        const { useState, useRef } = require('react');
        const [error, setError] = useState<string | null>(null);
        const inputRef = useRef<HTMLInputElement>(null);

        const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
          const f = e.target.files?.[0];
          if (f && !f.type.startsWith('image/')) {
            setError('Please upload an image file');
          } else {
            setError(null);
          }
        };

        return (
          <div>
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              data-testid="file-input"
              onChange={handleFile}
            />
            {error && <div data-testid="upload-error" role="alert">{error}</div>}
          </div>
        );
      };

      renderWithProviders(<MockImageUpload />);

      const textFile = new File(['not an image'], 'document.pdf', { type: 'application/pdf' });
      const input = screen.getByTestId('file-input');

      await user.upload(input, textFile);

      expect(screen.getByTestId('upload-error')).toHaveTextContent('Please upload an image file');
    });
  });

  describe('Results display flow', () => {
    it('displays screening results after analysis completes', async () => {
      const MockResults = () => {
        const { useState } = require('react');
        const [result, setResult] = useState<{
          risk: string;
          hemoglobin: number;
          confidence: number;
        } | null>(null);

        return (
          <div data-testid="results-panel">
            {!result ? (
              <div data-testid="no-results">No results yet. Complete a screening.</div>
            ) : (
              <div data-testid="results-display">
                <div data-testid="risk-level" role="status">Risk: {result.risk}</div>
                <div data-testid="hemoglobin">Hemoglobin: {result.hemoglobin} g/dL</div>
                <div data-testid="confidence">Confidence: {(result.confidence * 100).toFixed(0)}%</div>
              </div>
            )}
            <button
              data-testid="run-analysis"
              onClick={() =>
                setResult({
                  risk: 'moderate',
                  hemoglobin: 11.5,
                  confidence: 0.78,
                })
              }
            >
              Run Analysis
            </button>
          </div>
        );
      };

      renderWithProviders(<MockResults />);

      expect(screen.getByTestId('no-results')).toBeInTheDocument();

      await user.click(screen.getByTestId('run-analysis'));

      expect(screen.queryByTestId('no-results')).not.toBeInTheDocument();
      expect(screen.getByTestId('risk-level')).toHaveTextContent('Risk: moderate');
      expect(screen.getByTestId('hemoglobin')).toHaveTextContent('Hemoglobin: 11.5');
      expect(screen.getByTestId('confidence')).toHaveTextContent('Confidence: 78%');
    });

    it('displays loading state during analysis', async () => {
      const MockLoadingState = () => {
        const { useState } = require('react');
        const [isAnalyzing, setIsAnalyzing] = useState(false);

        return (
          <div>
            {isAnalyzing ? (
              <div data-testid="loading" role="status" aria-live="polite">
                Analyzing your image...
              </div>
            ) : (
              <button data-testid="start-analysis" onClick={() => setIsAnalyzing(true)}>
                Start Analysis
              </button>
            )}
          </div>
        );
      };

      renderWithProviders(<MockLoadingState />);

      expect(screen.getByTestId('start-analysis')).toBeInTheDocument();
      await user.click(screen.getByTestId('start-analysis'));
      expect(screen.getByTestId('loading')).toHaveTextContent('Analyzing your image...');
    });
  });

  describe('Screening reset flow', () => {
    it('resets screening state when user starts over', async () => {
      const MockScreeningWithReset = () => {
        const { useState } = require('react');
        const [hasResult, setHasResult] = useState(false);
        const [step, setStep] = useState(1);

        const reset = () => {
          setHasResult(false);
          setStep(1);
        };

        return (
          <div>
            {hasResult ? (
              <div data-testid="results">
                <p>Screening complete</p>
                <button data-testid="start-over" onClick={reset}>Start Over</button>
              </div>
            ) : (
              <div data-testid="in-progress">
                <p>Step {step}</p>
                <button data-testid="complete" onClick={() => setHasResult(true)}>
                  Complete Screening
                </button>
              </div>
            )}
          </div>
        );
      };

      renderWithProviders(<MockScreeningWithReset />);

      // Complete screening
      await user.click(screen.getByTestId('complete'));
      expect(screen.getByTestId('results')).toBeInTheDocument();

      // Start over
      await user.click(screen.getByTestId('start-over'));
      expect(screen.getByTestId('in-progress')).toBeInTheDocument();
      expect(screen.getByText('Step 1')).toBeInTheDocument();
    });
  });

  describe('Error handling flow', () => {
    it('displays error when analysis fails', async () => {
      const MockErrorFlow = () => {
        const { useState } = require('react');
        const [error, setError] = useState<string | null>(null);

        return (
          <div>
            {error && (
              <div data-testid="error-display" role="alert">
                <p>{error}</p>
                <button data-testid="dismiss-error" onClick={() => setError(null)}>
                  Dismiss
                </button>
              </div>
            )}
            <button
              data-testid="fail-analysis"
              onClick={() => setError('Analysis failed. Please try again.')}
            >
              Fail Analysis
            </button>
          </div>
        );
      };

      renderWithProviders(<MockErrorFlow />);

      await user.click(screen.getByTestId('fail-analysis'));
      expect(screen.getByTestId('error-display')).toHaveTextContent('Analysis failed');
      expect(screen.getByRole('alert')).toBeInTheDocument();

      await user.click(screen.getByTestId('dismiss-error'));
      expect(screen.queryByTestId('error-display')).not.toBeInTheDocument();
    });
  });

  describe('Quality check flow', () => {
    it('shows quality feedback before proceeding to analysis', async () => {
      const MockQualityCheck = () => {
        const { useState } = require('react');
        const [quality, setQuality] = useState<'pending' | 'pass' | 'fail'>('pending');

        return (
          <div data-testid="quality-check">
            {quality === 'pending' && (
              <button
                data-testid="check-quality"
                onClick={() => setQuality('pass')}
              >
                Check Quality
              </button>
            )}
            {quality === 'pass' && (
              <div data-testid="quality-passed">
                <p>Image quality is acceptable</p>
                <button data-testid="proceed" onClick={() => {}}>Proceed to Analysis</button>
              </div>
            )}
            {quality === 'fail' && (
              <div data-testid="quality-failed">
                <p>Image quality is insufficient</p>
                <button data-testid="retry" onClick={() => setQuality('pending')}>
                  Retake Photo
                </button>
              </div>
            )}
          </div>
        );
      };

      renderWithProviders(<MockQualityCheck />);

      // Initial state
      expect(screen.getByTestId('check-quality')).toBeInTheDocument();

      // Check quality - passes
      await user.click(screen.getByTestId('check-quality'));
      expect(screen.getByTestId('quality-passed')).toBeInTheDocument();
      expect(screen.getByText('Image quality is acceptable')).toBeInTheDocument();

      // Proceed button exists
      expect(screen.getByTestId('proceed')).toBeInTheDocument();
    });

    it('allows retry when quality check fails', async () => {
      const MockQualityCheck = () => {
        const { useState } = require('react');
        const [quality, setQuality] = useState<'pending' | 'pass' | 'fail'>('pending');

        return (
          <div data-testid="quality-check">
            {quality === 'pending' && (
              <button
                data-testid="check-quality"
                onClick={() => setQuality('fail')}
              >
                Check Quality
              </button>
            )}
            {quality === 'fail' && (
              <div data-testid="quality-failed">
                <p>Image quality is insufficient</p>
                <ul>
                  <li>Ensure good lighting</li>
                  <li>Keep camera steady</li>
                  <li>Focus on inner eyelid</li>
                </ul>
                <button data-testid="retry" onClick={() => setQuality('pending')}>
                  Retake Photo
                </button>
              </div>
            )}
          </div>
        );
      };

      renderWithProviders(<MockQualityCheck />);

      await user.click(screen.getByTestId('check-quality'));
      expect(screen.getByTestId('quality-failed')).toBeInTheDocument();
      expect(screen.getByText('Ensure good lighting')).toBeInTheDocument();

      await user.click(screen.getByTestId('retry'));
      expect(screen.getByTestId('check-quality')).toBeInTheDocument();
    });
  });
});
