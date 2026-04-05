import type Lenis from 'lenis';

let lenisInstance: Lenis | null = null;

const NAV_OFFSET = 112;

export function registerLenis(instance: Lenis | null) {
  lenisInstance = instance;
}

export function scrollToY(top: number) {
  if (typeof window === 'undefined') return;
  const target = Math.max(0, top - NAV_OFFSET);

  if (lenisInstance) {
    lenisInstance.scrollTo(target, { duration: 1.1 });
    return;
  }

  window.scrollTo({ top: target, behavior: 'smooth' });
}

export function scrollToId(id: string) {
  if (typeof document === 'undefined') return;
  const target = document.getElementById(id);
  if (!target) return;

  const top = target.getBoundingClientRect().top + window.scrollY;
  scrollToY(top);
}
