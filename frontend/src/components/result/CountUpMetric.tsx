import { useEffect, useState } from 'react';

const E = [0.22, 1, 0.36, 1] as const;

export function useCountUp(target: number, duration = 1600, delay = 200) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let start: number | null = null;
    const t = setTimeout(() => {
      const step = (ts: number) => {
        if (!start) start = ts;
        const p = Math.min((ts - start) / duration, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        setVal(parseFloat((ease * target).toFixed(1)));
        if (p < 1) requestAnimationFrame(step);
        else setVal(target);
      };
      requestAnimationFrame(step);
    }, delay);
    return () => clearTimeout(t);
  }, [target, duration, delay]);
  return val;
}

export function CountUpMetric({ value, duration = 1600, delay = 200, postfix = '' }: { value: number, duration?: number, delay?: number, postfix?: string }) {
  const val = useCountUp(value, duration, delay);
  return <>{val}{postfix}</>;
}
