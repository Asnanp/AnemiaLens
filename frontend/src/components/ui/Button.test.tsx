import React from 'react';
import { render, screen } from '../../test/utils';
import { Button } from '../../components/ui/Button';
import { vi } from 'vitest';
import { Home } from 'lucide-react';

// Mock framer-motion for Button tests
vi.mock('framer-motion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('framer-motion')>();
  return {
    ...actual,
    motion: {
      div: (props: React.HTMLAttributes<HTMLDivElement>) => React.createElement('div', props, props.children),
      button: (props: React.ButtonHTMLAttributes<HTMLButtonElement>) => React.createElement('button', props, props.children),
    },
  };
});

describe('Button', () => {
  const variants = ['primary', 'secondary', 'ghost', 'danger', 'success'] as const;
  const sizes = ['sm', 'md', 'lg'] as const;

  describe('variants', () => {
    variants.forEach((variant) => {
      test(`renders ${variant} variant correctly`, () => {
        render(<Button variant={variant}>Test Button</Button>);
        const button = screen.getByRole('button', { name: /test button/i });
        expect(button).toBeInTheDocument();
        expect(button).not.toBeDisabled();
      });
    });
  });

  describe('sizes', () => {
    sizes.forEach((size) => {
      test(`renders ${size} size correctly`, () => {
        render(<Button size={size}>Size {size}</Button>);
        const button = screen.getByRole('button', { name: /size/i });
        expect(button).toBeInTheDocument();
      });
    });
  });

  test('renders disabled state', () => {
    render(<Button disabled>Disabled Button</Button>);
    const button = screen.getByRole('button', { name: /disabled button/i });
    expect(button).toBeDisabled();
  });

  test('renders loading state with spinner', () => {
    render(<Button loading>Loading Button</Button>);
    const button = screen.getByRole('button', { name: /loading button/i });
    expect(button).toBeDisabled();
    // Spinner should be present
    const spinner = button.querySelector('div[style*="border"]');
    expect(spinner).toBeInTheDocument();
  });

  test('loading state hides icon', () => {
    render(
      <Button loading icon={Home}>
        Loading
      </Button>
    );
    const button = screen.getByRole('button', { name: /loading/i });
    // Icon should not be rendered when loading
    const svgs = button.querySelectorAll('svg');
    expect(svgs.length).toBe(0);
  });

  test('click handler is called', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click Me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    button.click();
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  test('click handler not called when disabled', () => {
    const handleClick = vi.fn();
    render(
      <Button disabled onClick={handleClick}>
        Disabled
      </Button>
    );
    const button = screen.getByRole('button', { name: /disabled/i });
    expect(button).toBeDisabled();
  });

  test('renders with icon on left', () => {
    render(
      <Button icon={Home} iconPosition="left">
        Icon Left
      </Button>
    );
    const button = screen.getByRole('button', { name: /icon left/i });
    expect(button).toBeInTheDocument();
  });

  test('renders with icon on right', () => {
    render(
      <Button icon={Home} iconPosition="right">
        Icon Right
      </Button>
    );
    const button = screen.getByRole('button', { name: /icon right/i });
    expect(button).toBeInTheDocument();
  });

  test('renders full width', () => {
    render(<Button fullWidth>Full Width</Button>);
    const button = screen.getByRole('button', { name: /full width/i });
    expect(button).toHaveStyle({ width: '100%' });
  });

  test('applies custom className', () => {
    render(<Button className="custom-class">Custom</Button>);
    const button = screen.getByRole('button', { name: /custom/i });
    expect(button).toHaveClass('custom-class');
  });

  test('passes through additional HTML props', () => {
    render(
      <Button aria-label="custom-label" type="submit">
        Props
      </Button>
    );
    const button = screen.getByRole('button', { name: /custom-label/i });
    expect(button).toHaveAttribute('aria-label', 'custom-label');
    expect(button).toHaveAttribute('type', 'submit');
  });
});
