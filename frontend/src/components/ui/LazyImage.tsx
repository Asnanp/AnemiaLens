/**
 * LazyImage — intersection-observer-based lazy loading for images.
 *
 * Features:
 * - Only loads when the image enters the viewport
 * - Configurable rootMargin for preloading
 * - Placeholder while loading
 * - Fade-in transition when loaded
 * - srcset and sizes support
 */

import { useRef, useState, useEffect } from 'react';
import { useInView } from 'react-intersection-observer';

interface LazyImageProps {
  src: string;
  alt: string;
  srcSet?: string;
  sizes?: string;
  className?: string;
  placeholderColor?: string;
  rootMargin?: string;
  threshold?: number;
  style?: React.CSSProperties;
  onLoad?: () => void;
  onError?: () => void;
}

export function LazyImage({
  src,
  alt,
  srcSet,
  sizes,
  className,
  placeholderColor = 'rgba(255,255,255,0.04)',
  rootMargin = '200px',
  threshold = 0,
  style,
  onLoad,
  onError,
}: LazyImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const imgRef = useRef<HTMLImageElement | null>(null);

  const { ref, inView } = useInView({
    rootMargin,
    threshold,
    triggerOnce: true,
  });

  // Set up the combined ref
  useEffect(() => {
    if (typeof ref === 'function') {
      ref(imgRef.current);
    } else if (ref) {
      (ref as React.MutableRefObject<HTMLImageElement | null>).current = imgRef.current;
    }
  }, [ref, imgRef.current]);

  const handleLoad = () => {
    setIsLoaded(true);
    onLoad?.();
  };

  const handleError = () => {
    setHasError(true);
    onError?.();
  };

  const shouldLoad = inView && !hasError;

  return (
    <div
      ref={ref}
      className={className}
      style={{
        position: 'relative',
        overflow: 'hidden',
        backgroundColor: placeholderColor,
        ...style,
      }}
    >
      {/* Placeholder */}
      {!isLoaded && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: placeholderColor,
            animation: 'pulse 1.5s ease-in-out infinite',
          }}
        />
      )}

      {/* Actual image */}
      {shouldLoad && (
        <img
          ref={imgRef}
          src={src}
          srcSet={srcSet}
          sizes={sizes}
          alt={alt}
          loading="lazy"
          decoding="async"
          onLoad={handleLoad}
          onError={handleError}
          style={{
            display: 'block',
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            opacity: isLoaded ? 1 : 0,
            transition: 'opacity 0.3s ease',
          }}
        />
      )}
    </div>
  );
}
