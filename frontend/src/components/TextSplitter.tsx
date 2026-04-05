import { useRef } from 'react';
import {
  motion,
  useScroll,
  useTransform,
  useReducedMotion,
  type MotionStyle,
} from 'framer-motion';

type SplitMode = 'words' | 'chars';

interface TextSplitterProps {
  children: string;
  as?: 'h1' | 'h2' | 'h3' | 'p' | 'span' | 'div';
  className?: string;
  style?: React.CSSProperties;
  mode?: SplitMode;
  /** 0–1 range within the element's scroll travel where animation runs */
  scrollStart?: number;
  scrollEnd?: number;
  /** Stagger delay factor between tokens */
  stagger?: number;
  /** Apply a blur dissolve alongside opacity */
  blur?: boolean;
  /** Y offset each token starts from */
  yOffset?: number;
}

export function TextSplitter({
  children,
  as: Tag = 'h1',
  className,
  style,
  mode = 'words',
  scrollStart = 0.0,
  scrollEnd = 0.55,
  stagger = 0.035,
  blur = true,
  yOffset = 18,
}: TextSplitterProps) {
  const ref = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start 0.92', 'start 0.55'],
  });

  const tokens =
    mode === 'chars'
      ? children.split('').map((c) => (c === ' ' ? '\u00A0' : c))
      : children.split(/(\s+)/).filter(Boolean);

  if (reduceMotion) {
    return (
      <Tag className={className} style={style}>
        {children}
      </Tag>
    );
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <Tag
        className={className}
        style={{
          ...style,
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: style?.textAlign === 'center' ? 'center' : undefined,
          gap: mode === 'chars' ? 0 : '0 0.3em',
        }}
      >
        {tokens.map((token, i) => {
          const tokenStart = scrollStart + i * stagger;
          const tokenEnd = Math.min(tokenStart + (scrollEnd - scrollStart) * 0.5, 1);

          return (
            <TokenSpan
              key={`${token}-${i}`}
              token={token}
              scrollYProgress={scrollYProgress}
              start={tokenStart}
              end={tokenEnd}
              blur={blur}
              yOffset={yOffset}
              isSpace={/^\s+$/.test(token)}
            />
          );
        })}
      </Tag>
    </div>
  );
}

function TokenSpan({
  token,
  scrollYProgress,
  start,
  end,
  blur,
  yOffset,
  isSpace,
}: {
  token: string;
  scrollYProgress: ReturnType<typeof useScroll>['scrollYProgress'];
  start: number;
  end: number;
  blur: boolean;
  yOffset: number;
  isSpace: boolean;
}) {
  const opacity = useTransform(scrollYProgress, [start, end], [0.08, 1]);
  const y = useTransform(scrollYProgress, [start, end], [yOffset, 0]);
  const blurVal = useTransform(scrollYProgress, [start, end], [8, 0]);
  const filter = useTransform(blurVal, (v) => (blur ? `blur(${v}px)` : 'none'));

  if (isSpace) {
    return <span style={{ width: '0.3em' }}>&nbsp;</span>;
  }

  const motionStyle: MotionStyle = {
    opacity,
    y,
    filter,
    display: 'inline-block',
    willChange: 'transform, opacity, filter',
  };

  return <motion.span style={motionStyle}>{token}</motion.span>;
}
