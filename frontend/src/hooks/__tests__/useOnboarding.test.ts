import { renderHook, act } from '@testing-library/react';
import { useOnboarding } from '../useOnboarding';

describe('useOnboarding', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('returns hasSeenOnboarding false when localStorage is empty', () => {
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.hasSeenOnboarding).toBe(false);
  });

  it('returns isReady false initially', () => {
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.isReady).toBe(false);
  });

  it('marks isReady true after timeout', async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useOnboarding());
    act(() => {
      vi.advanceTimersByTime(150);
    });
    expect(result.current.isReady).toBe(true);
    vi.useRealTimers();
  });

  it('returns hasSeenOnboarding true when localStorage has correct version', () => {
    localStorage.setItem(
      'anemialens.onboarding-complete',
      JSON.stringify({ complete: true, version: 1 })
    );
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.hasSeenOnboarding).toBe(true);
  });

  it('returns hasSeenOnboarding false when version is outdated', () => {
    localStorage.setItem(
      'anemialens.onboarding-complete',
      JSON.stringify({ complete: true, version: 0 })
    );
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.hasSeenOnboarding).toBe(false);
  });

  it('returns hasSeenOnboarding false when complete is false', () => {
    localStorage.setItem(
      'anemialens.onboarding-complete',
      JSON.stringify({ complete: false, version: 1 })
    );
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.hasSeenOnboarding).toBe(false);
  });

  it('returns hasSeenOnboarding false when localStorage is malformed', () => {
    localStorage.setItem('anemialens.onboarding-complete', 'not-json');
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.hasSeenOnboarding).toBe(false);
  });

  it('marks onboarding complete and persists to localStorage', () => {
    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.completeOnboarding();
    });

    expect(result.current.hasSeenOnboarding).toBe(true);
    const stored = JSON.parse(localStorage.getItem('anemialens.onboarding-complete')!);
    expect(stored.complete).toBe(true);
    expect(stored.version).toBe(1);
    expect(stored.completedAt).toBeDefined();
    expect(typeof stored.completedAt).toBe('number');
  });

  it('resets onboarding and removes from localStorage', () => {
    localStorage.setItem(
      'anemialens.onboarding-complete',
      JSON.stringify({ complete: true, version: 1 })
    );
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.hasSeenOnboarding).toBe(true);

    act(() => {
      result.current.resetOnboarding();
    });

    expect(result.current.hasSeenOnboarding).toBe(false);
    expect(localStorage.getItem('anemialens.onboarding-complete')).toBeNull();
  });

  it('handles localStorage write failure gracefully', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });

    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.completeOnboarding();
    });

    // Session fallback: still marks as seen even if localStorage fails
    expect(result.current.hasSeenOnboarding).toBe(true);
    setItemSpy.mockRestore();
  });

  it('handles localStorage read failure gracefully', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('AccessDenied');
    });

    const { result } = renderHook(() => useOnboarding());
    expect(result.current.hasSeenOnboarding).toBe(false);
  });

  it('handles removeItem failure gracefully', () => {
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('AccessDenied');
    });

    localStorage.setItem(
      'anemialens.onboarding-complete',
      JSON.stringify({ complete: true, version: 1 })
    );
    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.resetOnboarding();
    });

    expect(result.current.hasSeenOnboarding).toBe(false);
  });

  it('default export matches named export', async () => {
    const mod = await import('../useOnboarding');
    expect(mod.default).toBe(mod.useOnboarding);
  });
});
