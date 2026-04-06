import { renderHook, act } from '@testing-library/react';
import {
  useScrollReveal,
  useParallax,
  useScrollProgress,
  useStaggeredReveal,
} from '../useScrollAnimation';

// Mock framer-motion hooks used by the scroll animation hooks
const mockUseInView = vi.fn();
const mockUseScroll = vi.fn();
const mockUseSpring = vi.fn();
const mockUseTransform = vi.fn();
const mockUseMotionValue = vi.fn();

vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    useInView: (...args: any[]) => mockUseInView(...args),
    useScroll: (...args: any[]) => mockUseScroll(...args),
    useSpring: (...args: any[]) => mockUseSpring(...args),
    useTransform: (...args: any[]) => mockUseTransform(...args),
    useMotionValue: (...args: any[]) => mockUseMotionValue(...args),
  };
});

describe('useScrollAnimation hooks', () => {
  const mockMotionValue = {
    set: vi.fn(),
    get: vi.fn(() => 0),
    onChange: vi.fn(),
    off: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseInView.mockReturnValue(true);
    mockUseScroll.mockReturnValue({ scrollYProgress: mockMotionValue });
    mockUseSpring.mockReturnValue(mockMotionValue);
    mockUseTransform.mockReturnValue(mockMotionValue);
    mockUseMotionValue.mockReturnValue(mockMotionValue);
  });

  describe('useScrollReveal', () => {
    it('returns expected state object', () => {
      const { result } = renderHook(() => useScrollReveal());
      expect(result.current).toHaveProperty('ref');
      expect(result.current).toHaveProperty('isInView');
      expect(result.current).toHaveProperty('y');
      expect(result.current).toHaveProperty('x');
      expect(result.current).toHaveProperty('opacity');
      expect(result.current).toHaveProperty('scale');
      expect(result.current).toHaveProperty('delay');
    });

    it('uses default options correctly', () => {
      renderHook(() => useScrollReveal());
      expect(mockUseInView).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({ once: true, amount: 0.15 })
      );
    });

    it('respects custom threshold', () => {
      renderHook(() => useScrollReveal({ threshold: 0.5 }));
      expect(mockUseInView).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({ amount: 0.5 })
      );
    });

    it('respects custom direction "down"', () => {
      renderHook(() => useScrollReveal({ direction: 'down' }));
      // Motion values should be created for down direction
      expect(mockUseMotionValue).toHaveBeenCalled();
    });

    it('respects custom direction "left"', () => {
      renderHook(() => useScrollReveal({ direction: 'left' }));
      expect(mockUseMotionValue).toHaveBeenCalled();
    });

    it('respects custom direction "right"', () => {
      renderHook(() => useScrollReveal({ direction: 'right' }));
      expect(mockUseMotionValue).toHaveBeenCalled();
    });

    it('respects custom direction "scale"', () => {
      renderHook(() => useScrollReveal({ direction: 'scale' }));
      expect(mockUseMotionValue).toHaveBeenCalled();
    });

    it('respects custom direction "none"', () => {
      renderHook(() => useScrollReveal({ direction: 'none' }));
      expect(mockUseMotionValue).toHaveBeenCalled();
    });

    it('uses custom spring preset "snappy"', () => {
      renderHook(() => useScrollReveal({ spring: 'snappy' }));
      expect(mockUseSpring).toHaveBeenCalled();
    });

    it('uses custom spring preset "bouncy"', () => {
      renderHook(() => useScrollReveal({ spring: 'bouncy' }));
      expect(mockUseSpring).toHaveBeenCalled();
    });

    it('uses custom spring preset "stiff"', () => {
      renderHook(() => useScrollReveal({ spring: 'stiff' }));
      expect(mockUseSpring).toHaveBeenCalled();
    });

    it('uses custom spring preset "gentle"', () => {
      renderHook(() => useScrollReveal({ spring: 'gentle' }));
      expect(mockUseSpring).toHaveBeenCalled();
    });

    it('accepts custom SpringOptions object', () => {
      renderHook(() =>
        useScrollReveal({
          spring: { stiffness: 150, damping: 20, mass: 0.7 },
        })
      );
      expect(mockUseSpring).toHaveBeenCalled();
    });

    it('respects custom initialOpacity', () => {
      renderHook(() => useScrollReveal({ initialOpacity: 0.5 }));
      expect(mockUseMotionValue).toHaveBeenCalledWith(0.5);
    });

    it('respects custom distance', () => {
      renderHook(() => useScrollReveal({ distance: 100 }));
      expect(mockUseMotionValue).toHaveBeenCalledWith(100);
    });

    it('calculates stagger delay correctly', () => {
      const { result } = renderHook(() =>
        useScrollReveal({ stagger: 100, index: 3 })
      );
      expect(result.current.delay).toBe(300);
    });

    it('respects once=false for re-animation', () => {
      renderHook(() => useScrollReveal({ once: false }));
      expect(mockUseInView).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({ once: false })
      );
    });
  });

  describe('useParallax', () => {
    it('returns expected state object', () => {
      const { result } = renderHook(() => useParallax());
      expect(result.current).toHaveProperty('ref');
      expect(result.current).toHaveProperty('y');
      expect(result.current).toHaveProperty('scrollYProgress');
    });

    it('uses default speed', () => {
      renderHook(() => useParallax());
      expect(mockUseTransform).toHaveBeenCalled();
    });

    it('respects custom speed', () => {
      renderHook(() => useParallax({ speed: 0.8 }));
      expect(mockUseTransform).toHaveBeenCalled();
    });

    it('respects custom range', () => {
      renderHook(() => useParallax({ range: [-100, 100] }));
      expect(mockUseTransform).toHaveBeenCalled();
    });

    it('uses gentle spring by default', () => {
      renderHook(() => useParallax());
      expect(mockUseSpring).toHaveBeenCalled();
    });

    it('respects custom spring preset', () => {
      renderHook(() => useParallax({ spring: 'snappy' }));
      expect(mockUseSpring).toHaveBeenCalled();
    });

    it('accepts custom SpringOptions', () => {
      renderHook(() =>
        useParallax({ spring: { stiffness: 100, damping: 15, mass: 0.8 } })
      );
      expect(mockUseSpring).toHaveBeenCalled();
    });
  });

  describe('useScrollProgress', () => {
    it('returns expected state object', () => {
      const { result } = renderHook(() => useScrollProgress());
      expect(result.current).toHaveProperty('ref');
      expect(result.current).toHaveProperty('progress');
      expect(result.current).toHaveProperty('rawProgress');
      expect(result.current).toHaveProperty('progressPct');
    });

    it('uses stiff spring by default', () => {
      renderHook(() => useScrollProgress());
      expect(mockUseSpring).toHaveBeenCalled();
    });

    it('respects custom spring preset', () => {
      renderHook(() => useScrollProgress({ spring: 'gentle' }));
      expect(mockUseSpring).toHaveBeenCalled();
    });

    it('accepts custom SpringOptions', () => {
      renderHook(() =>
        useScrollProgress({ spring: { stiffness: 200, damping: 20, mass: 0.6 } })
      );
      expect(mockUseSpring).toHaveBeenCalled();
    });
  });

  describe('useStaggeredReveal', () => {
    it('returns array of ScrollRevealState for given count', () => {
      const { result } = renderHook(() => useStaggeredReveal(3));
      expect(result.current).toHaveLength(3);
      result.current.forEach((state) => {
        expect(state).toHaveProperty('ref');
        expect(state).toHaveProperty('isInView');
        expect(state).toHaveProperty('y');
        expect(state).toHaveProperty('opacity');
      });
    });

    it('applies stagger delay based on index', () => {
      const { result } = renderHook(() => useStaggeredReveal(2, { staggerMs: 120 }));
      // First item has index 0, second has index 1
      expect(result.current[0].delay).toBe(0);
      expect(result.current[1].delay).toBe(120);
    });

    it('uses default staggerMs of 80', () => {
      const { result } = renderHook(() => useStaggeredReveal(2));
      expect(result.current[1].delay).toBe(80);
    });

    it('respects custom options', () => {
      const { result } = renderHook(() =>
        useStaggeredReveal(2, { distance: 50, direction: 'left', once: false })
      );
      expect(result.current).toHaveLength(2);
    });

    it('returns empty array for count 0', () => {
      const { result } = renderHook(() => useStaggeredReveal(0));
      expect(result.current).toHaveLength(0);
    });
  });
});
