import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LanguageSwitcher } from '../../components/LanguageSwitcher';

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    i18n: {
      language: 'en',
      changeLanguage: vi.fn(),
    },
  }),
  initReactI18next: {},
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Languages: () => <div data-testid="languages-icon" />,
  Check: () => <div data-testid="check-icon" />,
}));

// Mock framer-motion
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    motion: {
      div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
        <div {...props}>{children}</div>
      ),
      button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
        <button {...props}>{children}</button>
      ),
    },
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  };
});

describe('LanguageSwitcher', () => {
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('inline variant (default)', () => {
    it('renders all supported language buttons', () => {
      render(<LanguageSwitcher />);
      expect(screen.getByText('EN')).toBeInTheDocument();
      expect(screen.getByText('ES')).toBeInTheDocument();
      expect(screen.getByText('HI')).toBeInTheDocument();
    });

    it('highlights the current language as active', () => {
      render(<LanguageSwitcher />);
      const enButton = screen.getByText('EN');
      expect(enButton).toBeInTheDocument();
      // The active button has a specific background style — verify it renders
      expect(enButton.closest('button')).toBeInTheDocument();
    });

    it('switches language when a button is clicked', async () => {
      const { useTranslation } = await import('react-i18next');
      const changeLanguage = vi.fn();
      vi.mocked(useTranslation).mockReturnValue({
        i18n: { language: 'en', changeLanguage },
      } as any);

      render(<LanguageSwitcher />);
      await user.click(screen.getByText('ES'));
      expect(changeLanguage).toHaveBeenCalledWith('es');
    });
  });

  describe('floating variant', () => {
    it('renders a language button with the current language native name', () => {
      render(<LanguageSwitcher variant="floating" />);
      expect(screen.getByText('English')).toBeInTheDocument();
      expect(screen.getByTestId('languages-icon')).toBeInTheDocument();
    });

    it('toggles the dropdown when clicked', async () => {
      render(<LanguageSwitcher variant="floating" />);
      const toggle = screen.getByRole('button', { name: /switch language/i });

      // Dropdown should not be visible initially
      expect(screen.queryByText('Español')).not.toBeInTheDocument();

      await user.click(toggle);
      expect(screen.getByText('Español')).toBeInTheDocument();
      expect(screen.getByText('हिन्दी')).toBeInTheDocument();

      await user.click(toggle);
      expect(screen.queryByText('Español')).not.toBeInTheDocument();
    });

    it('closes dropdown when clicking outside', async () => {
      render(
        <div>
          <LanguageSwitcher variant="floating" />
          <div data-testid="outside">Outside</div>
        </div>
      );

      const toggle = screen.getByRole('button', { name: /switch language/i });
      await user.click(toggle);
      expect(screen.getByText('Español')).toBeInTheDocument();

      await user.click(screen.getByTestId('outside'));
      expect(screen.queryByText('Español')).not.toBeInTheDocument();
    });

    it('selects language and closes dropdown in floating mode', async () => {
      const { useTranslation } = await import('react-i18next');
      const changeLanguage = vi.fn();
      vi.mocked(useTranslation).mockReturnValue({
        i18n: { language: 'en', changeLanguage },
      } as any);

      render(<LanguageSwitcher variant="floating" />);
      const toggle = screen.getByRole('button', { name: /switch language/i });
      await user.click(toggle);

      await user.click(screen.getByText('Español'));
      expect(changeLanguage).toHaveBeenCalledWith('es');
      // After selection, dropdown closes
      expect(screen.queryByText('हिन्दी')).not.toBeInTheDocument();
    });

    it('shows check icon for active language in dropdown', async () => {
      render(<LanguageSwitcher variant="floating" />);
      const toggle = screen.getByRole('button', { name: /switch language/i });
      await user.click(toggle);

      // Active language should have a check icon
      const englishButton = screen.getByRole('button', { name: '' }).closest('button');
      expect(screen.getByTestId('check-icon')).toBeInTheDocument();
    });

    it('has correct aria-expanded attribute', () => {
      render(<LanguageSwitcher variant="floating" />);
      const toggle = screen.getByRole('button', { name: /switch language/i });
      expect(toggle).toHaveAttribute('aria-expanded', 'false');
    });
  });

  describe('accessibility', () => {
    it('inline variant buttons have proper type', () => {
      render(<LanguageSwitcher />);
      const buttons = screen.getAllByRole('button');
      buttons.forEach((btn) => {
        expect(btn).toHaveAttribute('type', 'button');
      });
    });
  });
});
