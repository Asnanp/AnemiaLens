import { renderHook, act, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { useCountUp } from '../../components/result/CountUpMetric';

// Mock requestAnimationFrame for predictable testing
const mockRequestAnimationFrame = (callback: FrameRequestCallback) => {
  return setTimeout(() => callback(performance.now()), 0);
};

describe('useCountUp', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation(mockRequestAnimationFrame);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  test('returns initial state of 0', () => {
    const { result } = renderHook(() => useCountUp(100, 1000, 500));
    expect(result.current).toBe(0);
  });

  test('returns final value after animation completes', async () => {
    const { result } = renderHook(() => useCountUp(100, 100, 0));

    // Advance past the delay (0ms)
    await act(async () => {
      vi.advanceTimersByTime(0);
      await Promise.resolve();
    });

    // Advance past the animation duration
    await act(async () => {
      vi.advanceTimersByTime(100);
      await Promise.resolve();
    });

    expect(result.current).toBe(100);
  });

  test('returns correct final value with decimal target', async () => {
    const { result } = renderHook(() => useCountUp(75.5, 100, 0));

    await act(async () => {
      vi.advanceTimersByTime(0);
      await Promise.resolve();
    });

    await act(async () => {
      vi.advanceTimersByTime(100);
      await Promise.resolve();
    });

    expect(result.current).toBe(75.5);
  });

  test('cleans up timeout on unmount', () => {
    const clearTimeoutSpy = vi.spyOn(window, 'clearTimeout');
    const { unmount } = renderHook(() => useCountUp(100, 1000, 500));

    unmount();

    expect(clearTimeoutSpy).toHaveBeenCalled();
    clearTimeoutSpy.mockRestore();
  });

  test('respects custom duration', async () => {
    const { result } = renderHook(() => useCountUp(200, 50, 0));

    await act(async () => {
      vi.advanceTimersByTime(0);
      await Promise.resolve();
    });

    await act(async () => {
      vi.advanceTimersByTime(50);
      await Promise.resolve();
    });

    expect(result.current).toBe(200);
  });

  test('respects custom delay', async () => {
    const { result } = renderHook(() => useCountUp(50, 100, 200));

    // During delay, value should be 0
    expect(result.current).toBe(0);

    // Advance past delay
    await act(async () => {
      vi.advanceTimersByTime(200);
      await Promise.resolve();
    });

    // Animation should have started
    expect(result.current).toBeGreaterThanOrEqual(0);

    // Advance past duration
    await act(async () => {
      vi.advanceTimersByTime(100);
      await Promise.resolve();
    });

    expect(result.current).toBe(50);
  });

  test('uses default duration and delay', async () => {
    const { result } = renderHook(() => useCountUp(100));

    // Defaults: duration=1600, delay=200
    await act(async () => {
      vi.advanceTimersByTime(200); // delay
      await Promise.resolve();
    });

    await act(async () => {
      vi.advanceTimersByTime(1600); // duration
      await Promise.resolve();
    });

    expect(result.current).toBe(100);
  });
});
