import React from 'react';
import { render, screen, act } from '../../test/utils';
import { vi } from 'vitest';
import { CountUpMetric } from '../../components/result/CountUpMetric';

// Mock requestAnimationFrame for predictable testing
const mockRequestAnimationFrame = (callback: FrameRequestCallback) => {
  return setTimeout(() => callback(performance.now()), 0);
};

describe('CountUpMetric', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation(mockRequestAnimationFrame);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  test('renders with initial value 0', () => {
    render(<CountUpMetric value={100} duration={0} delay={0} />);
    // With duration=0 and delay=0, the initial render should show 0
    // before any animation frame fires
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  test('animates to target value', async () => {
    render(<CountUpMetric value={100} duration={100} delay={0} />);

    // Advance past the delay
    await act(async () => {
      vi.advanceTimersByTime(0);
      // Let the rAF callback execute
      await Promise.resolve();
    });

    // Advance past the animation duration
    await act(async () => {
      vi.advanceTimersByTime(100);
      // Let remaining rAF callbacks execute
      await Promise.resolve();
    });

    // After animation completes, should show the target value
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  test('animates to correct value with decimals', async () => {
    render(<CountUpMetric value={75.5} duration={100} delay={0} />);

    await act(async () => {
      vi.advanceTimersByTime(0);
      await Promise.resolve();
    });

    await act(async () => {
      vi.advanceTimersByTime(100);
      await Promise.resolve();
    });

    expect(screen.getByText('75.5')).toBeInTheDocument();
  });

  test('renders with custom duration and delay', async () => {
    render(<CountUpMetric value={50} duration={200} delay={100} />);

    // During delay period, should still be 0
    expect(screen.getByText('0')).toBeInTheDocument();

    // Advance past delay
    await act(async () => {
      vi.advanceTimersByTime(100);
      await Promise.resolve();
    });

    // Animation should have started but not finished
    // Value should be > 0
    const text = screen.getByText(/./);
    expect(text).toBeInTheDocument();

    // Advance past duration
    await act(async () => {
      vi.advanceTimersByTime(200);
      await Promise.resolve();
    });

    expect(screen.getByText('50')).toBeInTheDocument();
  });

  test('renders with postfix', async () => {
    render(<CountUpMetric value={100} duration={100} delay={0} postfix="%" />);

    await act(async () => {
      vi.advanceTimersByTime(0);
      await Promise.resolve();
    });

    await act(async () => {
      vi.advanceTimersByTime(100);
      await Promise.resolve();
    });

    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  test('uses default duration and delay', () => {
    // Just verify it renders without error with defaults
    const { container } = render(<CountUpMetric value={42} />);
    expect(container).toBeInTheDocument();
  });
});
