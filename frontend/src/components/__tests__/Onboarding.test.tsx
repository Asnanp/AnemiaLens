import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Onboarding } from '../Onboarding';

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
    },
    AnimatePresence: ({ children, mode }: { children: React.ReactNode; mode?: string }) => children,
    createElement: (tag: string, props: any, ...children: any[]) => {
      // Simple createElement mock for motion components
      return { type: tag, props, children };
    },
  };
});

// Mock SharedUI
vi.mock('../screening/SharedUI', () => ({
  E: [0.22, 1, 0.36, 1],
}));

describe('Onboarding', () => {
  const user = userEvent.setup({ delay: null });
  const mockComplete = vi.fn();
  const mockSkip = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with correct ARIA attributes', () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    const dialog = screen.getByRole('dialog', { name: /welcome to anemialens/i });
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('tabIndex', '0');
  });

  it('renders the first step content by default', () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    expect(screen.getByText(/Screen for anemia risk/i)).toBeInTheDocument();
    expect(screen.getByText(/What it does/i)).toBeInTheDocument();
  });

  it('renders Skip button', () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    expect(screen.getByRole('button', { name: /skip onboarding/i })).toBeInTheDocument();
  });

  it('renders Close button', () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    expect(screen.getByRole('button', { name: /close onboarding/i })).toBeInTheDocument();
  });

  it('renders Next button on first step', () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument();
  });

  it('renders progress dots', () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    const tablist = screen.getByRole('tablist', { name: /onboarding progress/i });
    expect(tablist).toBeInTheDocument();
  });

  it('navigates to next step when Next is clicked', async () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    // First step title
    expect(screen.getByText(/Screen for anemia risk/i)).toBeInTheDocument();

    const nextButton = screen.getByRole('button', { name: /next/i });
    await user.click(nextButton);

    // Second step title should appear
    expect(screen.getByText(/Four guided steps/i)).toBeInTheDocument();
    expect(screen.getByText(/How it works/i)).toBeInTheDocument();
  });

  it('shows Start Screening button on last step', async () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);

    // Navigate through all steps
    const nextButton = screen.getByRole('button', { name: /next/i });
    await user.click(nextButton); // Step 2
    const nextButton2 = screen.getByRole('button', { name: /next/i });
    await user.click(nextButton2); // Step 3 (last)

    expect(screen.getByRole('button', { name: /start screening/i })).toBeInTheDocument();
  });

  it('calls onComplete when Start Screening is clicked', async () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);

    // Navigate to last step
    const nextButton = screen.getByRole('button', { name: /next/i });
    await user.click(nextButton); // Step 2
    const nextButton2 = screen.getByRole('button', { name: /next/i });
    await user.click(nextButton2); // Step 3 (last)

    const startButton = screen.getByRole('button', { name: /start screening/i });
    await user.click(startButton);

    expect(mockComplete).toHaveBeenCalled();
  });

  it('calls onSkip when Skip is clicked', async () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    const skipButton = screen.getByRole('button', { name: /skip onboarding/i });
    await user.click(skipButton);
    expect(mockSkip).toHaveBeenCalled();
  });

  it('calls onComplete when Close button is clicked', async () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    const closeButton = screen.getByRole('button', { name: /close onboarding/i });
    await user.click(closeButton);
    expect(mockComplete).toHaveBeenCalled();
  });

  it('navigates back when back button is clicked', async () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);

    // Go to step 2
    const nextButton = screen.getByRole('button', { name: /next/i });
    await user.click(nextButton);
    expect(screen.getByText(/Four guided steps/i)).toBeInTheDocument();

    // Back button should now be visible
    const backButton = screen.getByRole('button', { name: /previous step/i });
    await user.click(backButton);

    // Should be back on step 1
    expect(screen.getByText(/Screen for anemia risk/i)).toBeInTheDocument();
  });

  it('handles keyboard navigation: ArrowRight', async () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    const dialog = screen.getByRole('dialog', { name: /welcome to anemialens/i });

    dialog.focus();
    await user.keyboard('{ArrowRight}');

    expect(screen.getByText(/Four guided steps/i)).toBeInTheDocument();
  });

  it('handles keyboard navigation: ArrowLeft', async () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    const dialog = screen.getByRole('dialog', { name: /welcome to anemialens/i });

    // First go to step 2
    dialog.focus();
    await user.keyboard('{ArrowRight}');
    expect(screen.getByText(/Four guided steps/i)).toBeInTheDocument();

    // Then go back
    await user.keyboard('{ArrowLeft}');
    expect(screen.getByText(/Screen for anemia risk/i)).toBeInTheDocument();
  });

  it('handles keyboard navigation: Enter triggers next', async () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    const dialog = screen.getByRole('dialog', { name: /welcome to anemialens/i });

    dialog.focus();
    await user.keyboard('{Enter}');
    expect(screen.getByText(/Four guided steps/i)).toBeInTheDocument();
  });

  it('handles keyboard navigation: Space triggers next', async () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    const dialog = screen.getByRole('dialog', { name: /welcome to anemialens/i });

    dialog.focus();
    await user.keyboard(' ');
    expect(screen.getByText(/Four guided steps/i)).toBeInTheDocument();
  });

  it('renders features list for each step', () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    const features = screen.getAllByRole('list');
    expect(features.length).toBeGreaterThan(0);
  });

  it('renders all three step titles as user navigates', async () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);

    // Step 1
    expect(screen.getByText(/What it does/i)).toBeInTheDocument();

    // Navigate to step 2
    await user.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByText(/How it works/i)).toBeInTheDocument();

    // Navigate to step 3
    await user.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByText(/Privacy & Safety/i)).toBeInTheDocument();
  });

  it('renders step icons', () => {
    render(<Onboarding onComplete={mockComplete} onSkip={mockSkip} />);
    // The icons are rendered via lucide-react components
    // We can check that the step content renders at least
    expect(screen.getByText(/Instant risk assessment/i)).toBeInTheDocument();
  });

  it('default export matches named export', async () => {
    const mod = await import('../Onboarding');
    expect(mod.default).toBe(mod.Onboarding);
  });
});
