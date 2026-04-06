import React from 'react';
import { render, screen } from '../../test/utils';
import { Skeleton, SkeletonText, SkeletonCard, SkeletonMetric } from '../../components/ui/Skeleton';
import { vi } from 'vitest';

// Mock framer-motion for Skeleton tests
vi.mock('framer-motion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('framer-motion')>();
  return {
    ...actual,
    motion: {
      div: (props: React.HTMLAttributes<HTMLDivElement>) => React.createElement('div', props, props.children),
    },
  };
});

describe('Skeleton', () => {
  const variants = ['text', 'circular', 'rectangular', 'image'] as const;

  variants.forEach((variant) => {
    test(`renders ${variant} variant correctly`, () => {
      const { container } = render(<Skeleton variant={variant} />);
      const skeleton = container.firstChild as HTMLElement;
      expect(skeleton).toBeInTheDocument();
      expect(skeleton.tagName).toBe('DIV');
    });
  });

  test('circular variant has 50% border radius', () => {
    const { container } = render(<Skeleton variant="circular" />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveStyle({ borderRadius: '50%' });
  });

  test('image variant has custom border radius', () => {
    const { container } = render(<Skeleton variant="image" />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveStyle({ borderRadius: '0.75rem' });
  });

  test('text variant has default border radius', () => {
    const { container } = render(<Skeleton variant="text" />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveStyle({ borderRadius: '0.5rem' });
  });

  test('rectangular variant has default border radius', () => {
    const { container } = render(<Skeleton variant="rectangular" />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveStyle({ borderRadius: '0.5rem' });
  });

  test('renders with custom width', () => {
    const { container } = render(<Skeleton width="200px" />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveStyle({ width: '200px' });
  });

  test('renders with custom height', () => {
    const { container } = render(<Skeleton height="50px" />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveStyle({ height: '50px' });
  });

  test('renders with custom border radius override', () => {
    const { container } = render(<Skeleton variant="text" borderRadius="10px" />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveStyle({ borderRadius: '10px' });
  });

  test('renders with custom className', () => {
    const { container } = render(<Skeleton className="my-skeleton" />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveClass('my-skeleton');
  });

  test('renders with inline style override', () => {
    const { container } = render(<Skeleton style={{ opacity: 0.5 }} />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveStyle({ opacity: '0.5' });
  });

  test('renders with numeric width and height', () => {
    const { container } = render(<Skeleton width={100} height={100} />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton).toHaveStyle({ width: '100px' });
    expect(skeleton).toHaveStyle({ height: '100px' });
  });
});

describe('SkeletonText', () => {
  test('renders with default 3 lines', () => {
    const { container } = render(<SkeletonText />);
    const lines = container.querySelectorAll('[style*="border-radius"]');
    expect(lines).toHaveLength(3);
  });

  test('renders with custom number of lines', () => {
    const { container } = render(<SkeletonText lines={5} />);
    const lines = container.querySelectorAll('[style*="border-radius"]');
    expect(lines).toHaveLength(5);
  });

  test('last line is shorter than others', () => {
    const { container } = render(<SkeletonText lines={3} />);
    const lines = container.querySelectorAll('[style*="border-radius"]');
    const lastLine = lines[lines.length - 1] as HTMLElement;
    expect(lastLine).toHaveStyle({ width: '60%' });
  });

  test('applies custom className', () => {
    const { container } = render(<SkeletonText className="custom-text-skeleton" />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveClass('custom-text-skeleton');
  });
});

describe('SkeletonCard', () => {
  test('renders card with title and text lines', () => {
    const { container } = render(<SkeletonCard />);
    expect(container).toBeInTheDocument();
    // Should have multiple skeleton elements
    const skeletons = container.querySelectorAll('[style*="border-radius"]');
    expect(skeletons.length).toBeGreaterThan(1);
  });

  test('applies custom className', () => {
    const { container } = render(<SkeletonCard className="custom-card" />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveClass('custom-card');
  });
});

describe('SkeletonMetric', () => {
  test('renders metric skeleton with circular and text', () => {
    const { container } = render(<SkeletonMetric />);
    expect(container).toBeInTheDocument();
    const skeletons = container.querySelectorAll('[style*="border-radius"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  test('applies custom className', () => {
    const { container } = render(<SkeletonMetric className="custom-metric" />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper).toHaveClass('custom-metric');
  });
});
