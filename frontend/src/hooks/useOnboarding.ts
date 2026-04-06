import { useState, useEffect, useCallback } from 'react';

const ONBOARDING_KEY = 'anemialens.onboarding-complete';
const ONBOARDING_VERSION = 1;

/**
 * Manages onboarding state for new users.
 * - Checks localStorage to see if onboarding has been completed
 * - Provides a function to mark onboarding as complete
 * - Supports versioning so onboarding can be re-shown after major updates
 */
export function useOnboarding() {
  const [hasSeenOnboarding, setHasSeenOnboarding] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    try {
      const stored = window.localStorage.getItem(ONBOARDING_KEY);
      if (!stored) return false;
      const parsed = JSON.parse(stored);
      // Re-show onboarding if the version has changed
      return parsed.version === ONBOARDING_VERSION && parsed.complete === true;
    } catch {
      return false;
    }
  });

  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    // Small delay to avoid flash — lets the app shell mount first
    const timer = setTimeout(() => setIsReady(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const completeOnboarding = useCallback(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(
        ONBOARDING_KEY,
        JSON.stringify({ complete: true, version: ONBOARDING_VERSION, completedAt: Date.now() })
      );
      setHasSeenOnboarding(true);
    } catch {
      // localStorage unavailable — still mark as seen for this session
      setHasSeenOnboarding(true);
    }
  }, []);

  const resetOnboarding = useCallback(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.removeItem(ONBOARDING_KEY);
      setHasSeenOnboarding(false);
    } catch {
      setHasSeenOnboarding(false);
    }
  }, []);

  return {
    hasSeenOnboarding,
    isReady,
    completeOnboarding,
    resetOnboarding,
  };
}

export default useOnboarding;
