import { useState, useRef, useCallback, useEffect } from 'react';
import { Camera, X, RefreshCw, ShieldCheck, ZoomIn, ZoomOut, Maximize2, ScanLine, Grid3X3 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Skeleton } from '../ui/Skeleton';

const E = [0.22, 1, 0.36, 1] as const;

// --- Constants ---
const MAX_IMAGE_DIMENSION = 2048;
const JPEG_QUALITY = 0.85;
const MAX_FILE_SIZE_MB = 10;

// --- Types ---
interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  previewUrl: string | null;
  onClear: () => void;
  onRunQuality: () => void;
  loading: boolean;
  disabled: boolean;
}

interface FramingGuideProps {
  active: boolean;
}

interface ImagePreviewProps {
  src: string;
  onZoomChange: (zoom: number) => void;
  zoom: number;
  onPan: (x: number, y: number) => void;
  panX: number;
  panY: number;
}

interface CompressionResult {
  file: File;
  originalSize: number;
  compressedSize: number;
}

// ------------------------------------------------------------------
// EXIF Orientation Helper
// ------------------------------------------------------------------

function getExifOrientation(file: File): Promise<number> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => {
      const view = new DataView(reader.result as ArrayBuffer);
      if (view.getUint16(0, false) !== 0xFFD8) {
        resolve(-1);
        return;
      }
      const length = view.byteLength;
      let offset = 2;
      while (offset < length) {
        const marker = view.getUint16(offset, false);
        offset += 2;
        if (marker === 0xFFE1) {
          if (view.getUint32(offset + 2, false) !== 0x45786966) {
            resolve(-1);
            return;
          }
          const little = view.getUint16(offset + 8, false) === 0x4949;
          const ifdOffset = view.getUint32(offset + 12, little);
          const entryCount = view.getUint16(offset + ifdOffset, little);
          for (let i = 0; i < entryCount; i++) {
            const tagOffset = offset + ifdOffset + 2 + i * 12;
            const tag = view.getUint16(tagOffset, little);
            if (tag === 0x0112) {
              const valueOffset = view.getUint16(tagOffset + 8, little);
              resolve(valueOffset);
              return;
            }
          }
          resolve(1);
          return;
        }
        offset += view.getUint16(offset, false);
      }
      resolve(-1);
    };
    reader.readAsArrayBuffer(file.slice(0, 64 * 1024));
  });
}

function applyExifOrientation(canvas: HTMLCanvasElement, orientation: number): HTMLCanvasElement {
  if (orientation <= 1) return canvas;
  const ctx = canvas.getContext('2d');
  if (!ctx) return canvas;

  const { width, height } = canvas;
  const oriented = document.createElement('canvas');
  const oCtx = oriented.getContext('2d')!;

  if ([5, 6, 7, 8].includes(orientation)) {
    oriented.width = height;
    oriented.height = width;
  } else {
    oriented.width = width;
    oriented.height = height;
  }

  switch (orientation) {
    case 2: oCtx.transform(-1, 0, 0, 1, width, 0); break;
    case 3: oCtx.transform(-1, 0, 0, -1, width, height); break;
    case 4: oCtx.transform(1, 0, 0, -1, 0, height); break;
    case 5: oCtx.transform(0, 1, 1, 0, 0, 0); break;
    case 6: oCtx.transform(0, 1, -1, 0, height, 0); break;
    case 7: oCtx.transform(0, -1, -1, 0, height, width); break;
    case 8: oCtx.transform(0, -1, 1, 0, 0, width); break;
    default: return canvas;
  }

  oCtx.drawImage(canvas, 0, 0);
  return oriented;
}

// ------------------------------------------------------------------
// Image Compression
// ------------------------------------------------------------------

async function compressImage(file: File, maxWidth = MAX_IMAGE_DIMENSION, quality = JPEG_QUALITY): Promise<CompressionResult> {
  const originalSize = file.size;

  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      let { width, height } = img;

      if (width > maxWidth || height > maxWidth) {
        if (width > height) {
          height = Math.round((height * maxWidth) / width);
          width = maxWidth;
        } else {
          width = Math.round((width * maxWidth) / height);
          height = maxWidth;
        }
      }

      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d')!;
      ctx.drawImage(img, 0, 0, width, height);

      getExifOrientation(file).then((orientation) => {
        const finalCanvas = applyExifOrientation(canvas, orientation);

        finalCanvas.toBlob(
          (blob) => {
            if (blob) {
              const compressedFile = new File([blob], file.name, { type: 'image/jpeg' });
              resolve({
                file: compressedFile,
                originalSize,
                compressedSize: compressedFile.size,
              });
            } else {
              resolve({ file, originalSize, compressedSize: originalSize });
            }
          },
          'image/jpeg',
          quality
        );
      });
    };
    img.onerror = () => resolve({ file, originalSize, compressedSize: originalSize });
    img.src = URL.createObjectURL(file);
  });
}

// ------------------------------------------------------------------
// Framing Guide Component
// ------------------------------------------------------------------

function FramingGuide({ active }: FramingGuideProps) {
  if (!active) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 5,
      }}
      role="presentation"
      aria-hidden="true"
    >
      {/* Animated grid pattern */}
      <svg
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="grid" width="33.33%" height="33.33%" patternUnits="userSpaceOnUse">
            <path d="M 100 0 L 0 0 0 100" fill="none" stroke="rgba(200,0,30,0.25)" strokeWidth="1" strokeDasharray="4 4" />
          </pattern>
          <linearGradient id="vignette" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="60%" stopColor="rgba(0,0,0,0)" />
            <stop offset="100%" stopColor="rgba(0,0,0,0.4)" />
          </linearGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
        <rect width="100%" height="100%" fill="url(#vignette)" />
      </svg>

      {/* Center target area */}
      <motion.div
        animate={{
          borderColor: ['rgba(200,0,30,0.4)', 'rgba(200,0,30,0.7)', 'rgba(200,0,30,0.4)'],
          scale: [1, 1.02, 1],
        }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '60%',
          height: '50%',
          borderRadius: '1rem',
          border: '2px dashed rgba(200,0,30,0.5)',
          boxShadow: '0 0 20px rgba(200,0,30,0.15)',
        }}
      />

      {/* Animated scan line */}
      <motion.div
        initial={{ top: '-10%' }}
        animate={{ top: '110%' }}
        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          height: 2,
          background: 'var(--teal)',
          boxShadow: '0 0 10px rgba(94,234,212,0.8), 0 0 40px rgba(94,234,212,0.4)',
          zIndex: 5,
          pointerEvents: 'none',
          opacity: 0.85,
        }}
      />

      {/* Corner brackets */}
      {[
        { top: '15%', left: '10%' },
        { top: '15%', right: '10%' },
        { bottom: '15%', left: '10%' },
        { bottom: '15%', right: '10%' },
      ].map((pos, i) => (
        <motion.div
          key={i}
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.5, delay: i * 0.2, repeat: Infinity }}
          style={{
            position: 'absolute',
            ...pos,
            width: 20,
            height: 20,
            borderTop: (pos as any).top ? '2px solid rgba(200,0,30,0.6)' : 'none',
            borderLeft: (pos as any).left ? '2px solid rgba(200,0,30,0.6)' : 'none',
            borderBottom: (pos as any).bottom ? '2px solid rgba(200,0,30,0.6)' : 'none',
            borderRight: (pos as any).right ? '2px solid rgba(200,0,30,0.6)' : 'none',
          }}
        />
      ))}

      {/* Guidance text */}
      <div
        style={{
          position: 'absolute',
          bottom: '8%',
          left: '50%',
          transform: 'translateX(-50%)',
          padding: '0.4rem 0.8rem',
          borderRadius: '999px',
          background: 'rgba(10,10,16,0.7)',
          border: '1px solid rgba(200,0,30,0.3)',
          color: 'var(--text)',
          fontFamily: 'var(--mono)',
          fontSize: '0.6rem',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          whiteSpace: 'nowrap',
        }}
      >
        Align eyelid within frame
      </div>
    </motion.div>
  );
}

// ------------------------------------------------------------------
// Image Preview with Zoom/Pan
// ------------------------------------------------------------------

function ImagePreview({ src, zoom, onZoomChange, onPan, panX, panY }: ImagePreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });

  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoom <= 1) return;
    setIsDragging(true);
    setStartPos({ x: e.clientX - panX, y: e.clientY - panY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    onPan(e.clientX - startPos.x, e.clientY - startPos.y);
  };

  const handleMouseUp = () => setIsDragging(false);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    const newZoom = Math.max(1, Math.min(5, zoom + delta));
    onZoomChange(newZoom);
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        cursor: zoom > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default',
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
      role="img"
      aria-label="Image preview - use mouse wheel to zoom, drag to pan"
    >
      <motion.img
        src={src}
        alt="Preview"
        animate={{
          scale: zoom,
          x: panX,
          y: panY,
        }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transformOrigin: 'center center',
          userSelect: 'none',
        }}
        draggable={false}
      />

      {/* Zoom controls */}
      {zoom > 1 && (
        <div
          style={{
            position: 'absolute',
            bottom: '0.5rem',
            right: '0.5rem',
            display: 'flex',
            gap: '0.35rem',
            zIndex: 10,
          }}
        >
          <button
            className="btn btn-glass"
            style={{
              padding: '0.35rem',
              borderRadius: '0.4rem',
              minWidth: '1.75rem',
              minHeight: '1.75rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            onClick={(e) => {
              e.stopPropagation();
              onZoomChange(Math.min(5, zoom + 0.25));
            }}
            aria-label="Zoom in"
          >
            <ZoomIn size={12} />
          </button>
          <button
            className="btn btn-glass"
            style={{
              padding: '0.35rem',
              borderRadius: '0.4rem',
              minWidth: '1.75rem',
              minHeight: '1.75rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            onClick={(e) => {
              e.stopPropagation();
              onZoomChange(Math.max(1, zoom - 0.25));
            }}
            aria-label="Zoom out"
          >
            <ZoomOut size={12} />
          </button>
          <button
            className="btn btn-glass"
            style={{
              padding: '0.35rem',
              borderRadius: '0.4rem',
              minWidth: '1.75rem',
              minHeight: '1.75rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            onClick={(e) => {
              e.stopPropagation();
              onZoomChange(1);
              onPan(0, 0);
            }}
            aria-label="Reset zoom and pan"
          >
            <Maximize2 size={12} />
          </button>
        </div>
      )}

      {/* Zoom level indicator */}
      {zoom > 1 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{
            position: 'absolute',
            top: '0.5rem',
            right: '0.5rem',
            padding: '0.2rem 0.45rem',
            borderRadius: '999px',
            background: 'rgba(10,10,16,0.6)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: 'var(--text)',
            fontFamily: 'var(--mono)',
            fontSize: '0.5rem',
            letterSpacing: '0.08em',
            zIndex: 10,
          }}
        >
          {Math.round(zoom * 100)}%
        </motion.div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------
// Skeleton Image Placeholder
// ------------------------------------------------------------------

function SkeletonImagePlaceholder() {
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '1rem',
        padding: '2rem',
        background: 'rgba(10,10,16,0.6)',
        backdropFilter: 'blur(8px)',
        zIndex: 12,
      }}
      role="status"
      aria-busy="true"
      aria-label="Image processing in progress"
    >
      <Skeleton
        variant="image"
        width="70%"
        height="65%"
        borderRadius="1rem"
        style={{
          background: 'linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.03) 75%)',
        }}
      />
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          style={{
            width: 16,
            height: 16,
            border: '2px solid rgba(255,255,255,0.15)',
            borderTopColor: 'var(--accent-bright)',
            borderRadius: '50%',
          }}
        />
        <span
          style={{
            fontFamily: 'var(--mono)',
            fontSize: '0.6rem',
            color: 'var(--text-muted)',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          Processing image...
        </span>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Haptic Feedback Simulation
// ------------------------------------------------------------------

function useHapticFeedback() {
  const triggerHaptic = useCallback((intensity: 'light' | 'medium' | 'heavy' = 'light') => {
    // Use Vibration API if available (mobile)
    if (navigator.vibrate) {
      const durations = { light: 10, medium: 20, heavy: 50 };
      navigator.vibrate(durations[intensity]);
    }
  }, []);

  return triggerHaptic;
}

// ------------------------------------------------------------------
// Main Component
// ------------------------------------------------------------------

export function UploadZone({ onFileSelect, previewUrl, onClear, onRunQuality, loading, disabled }: UploadZoneProps) {
  const [drag, setDrag] = useState(false);
  const [hover, setHover] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [showFramingGuide, setShowFramingGuide] = useState(false);
  const [imageZoom, setImageZoom] = useState(1);
  const [imagePan, setImagePan] = useState({ x: 0, y: 0 });
  const [pulseActive, setPulseActive] = useState(false);
  const [cameraMode, setCameraMode] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  const triggerHaptic = useHapticFeedback();

  // Reset zoom/pan when preview changes
  useEffect(() => {
    setImageZoom(1);
    setImagePan({ x: 0, y: 0 });
  }, [previewUrl]);

  // Pulse animation for haptic feedback
  const triggerPulse = useCallback(() => {
    setPulseActive(true);
    triggerHaptic('medium');
    setTimeout(() => setPulseActive(false), 300);
  }, [triggerHaptic]);

  // Process file with compression
  const processFile = useCallback(async (file: File) => {
    // Validate file type
    if (!file.type.startsWith('image/')) {
      return;
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      return;
    }

    // Show progress
    setUploadProgress(0);
    triggerPulse();

    // Simulate progress during compression
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev === null || prev >= 90) return prev;
        return prev + 10;
      });
    }, 50);

    try {
      // Compress image
      const result = await compressImage(file);

      clearInterval(progressInterval);
      setUploadProgress(100);

      // Brief delay to show completion
      await new Promise((resolve) => setTimeout(resolve, 200));

      setUploadProgress(null);
      setCameraMode(false);
      onFileSelect(result.file);
      triggerPulse();
    } catch {
      clearInterval(progressInterval);
      setUploadProgress(null);
      // Fallback to original file
      onFileSelect(file);
    }
  }, [onFileSelect, triggerPulse]);

  // Drag handlers
  const onDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDrag(e.type === 'dragenter' || e.type === 'dragover');
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDrag(false);
      if (e.dataTransfer.files?.[0]) {
        processFile(e.dataTransfer.files[0]);
      }
    },
    [processFile]
  );

  // File input handler
  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files?.[0]) {
        processFile(e.target.files[0]);
        // Reset input to allow same file re-selection
        e.target.value = '';
      }
    },
    [processFile]
  );

  // Keyboard handler for accessibility
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (!previewUrl) {
          inputRef.current?.click();
        }
      }
    },
    [previewUrl]
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Hidden file inputs */}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={handleFileInput}
        aria-label="Upload image file"
      />
      {/* Camera input with capture attribute for mobile */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: 'none' }}
        onChange={handleFileInput}
        aria-label="Capture photo with camera"
      />

      {/* Drop zone */}
      <motion.div
        ref={dropZoneRef}
        onDragEnter={onDrag}
        onDragLeave={onDrag}
        onDragOver={onDrag}
        onDrop={onDrop}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onClick={() => !previewUrl && !cameraMode && inputRef.current?.click()}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
        aria-label={previewUrl ? 'Image preview area - click Replace to change' : 'Upload zone - click or drag and drop an image'}
        aria-live="polite"
        aria-describedby="upload-instructions"
        className="glass-premium bg-noise hover-lift"
        animate={{
          borderColor: drag
            ? 'rgba(200,0,30,0.8)'
            : hover && !previewUrl
            ? 'rgba(255,255,255,0.3)'
            : 'rgba(255,255,255,0.15)',
          background: drag
            ? 'rgba(200,0,30,0.1)'
            : 'rgba(255,255,255,0.03)',
          scale: pulseActive ? 1.01 : 1,
        }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        style={{
          position: 'relative',
          aspectRatio: '4/3',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
          cursor: previewUrl ? 'default' : 'pointer',
          boxShadow: drag
            ? '0 0 60px rgba(200,0,30,0.3), inset 0 2px 0 rgba(255,255,255,0.2)'
            : 'inset 0 1px 0 rgba(255,255,255,0.1)',
          outline: 'none',
        }}
      >
        {/* Pulse ring effect */}
        <AnimatePresence>
          {pulseActive && (
            <motion.div
              initial={{ scale: 0.95, opacity: 1 }}
              animate={{ scale: 1.05, opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              style={{
                position: 'absolute',
                inset: 0,
                borderRadius: '1.5rem',
                border: '2px solid rgba(200,0,30,0.5)',
                pointerEvents: 'none',
                zIndex: 20,
              }}
            />
          )}
        </AnimatePresence>

        {/* Upload progress bar */}
        <AnimatePresence>
          {uploadProgress !== null && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              role="progressbar"
              aria-valuenow={uploadProgress}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Image upload progress"
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                zIndex: 15,
                padding: '0.5rem 1rem',
                background: 'rgba(10,10,16,0.8)',
                backdropFilter: 'blur(10px)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '0.35rem',
                }}
              >
                <span
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: '0.6rem',
                    color: 'var(--text)',
                    letterSpacing: '0.05em',
                  }}
                >
                  Processing...
                </span>
                <span
                  style={{
                    fontFamily: 'var(--mono)',
                    fontSize: '0.6rem',
                    color: 'var(--accent-bright)',
                  }}
                >
                  {uploadProgress}%
                </span>
              </div>
              <div
                style={{
                  height: '3px',
                  borderRadius: '2px',
                  background: 'rgba(255,255,255,0.1)',
                  overflow: 'hidden',
                }}
              >
                <motion.div
                  initial={{ width: '0%' }}
                  animate={{ width: `${uploadProgress}%` }}
                  transition={{ duration: 0.2 }}
                  style={{
                    height: '100%',
                    borderRadius: '2px',
                    background: 'linear-gradient(90deg, var(--accent), var(--accent-bright))',
                  }}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence mode="wait">
          {previewUrl ? (
            <motion.div
              key="preview"
              initial={{ opacity: 0, scale: 1.05 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4, ease: E }}
              style={{ position: 'absolute', inset: 0 }}
            >
              {/* Enhanced preview with zoom/pan */}
              <ImagePreview
                src={previewUrl}
                zoom={imageZoom}
                onZoomChange={setImageZoom}
                panX={imagePan.x}
                panY={imagePan.y}
                onPan={(x, y) => setImagePan({ x, y })}
              />

              {/* Inline skeleton placeholder during loading - replaces full-screen overlay */}
              <AnimatePresence>
                {loading && <SkeletonImagePlaceholder />}
              </AnimatePresence>

              {/* Hover overlay */}
              <motion.div
                animate={{ opacity: hover ? (loading ? 0.3 : 1) : 0.96 }}
                transition={{ duration: 0.3 }}
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  padding: '1rem',
                  backdropFilter: 'blur(4px)',
                  background: hover ? 'rgba(10,10,16,0.5)' : 'rgba(10,10,16,0.3)',
                  pointerEvents: hover && !loading ? 'auto' : 'none',
                  zIndex: 8,
                }}
              >
                <div
                  style={{
                    alignSelf: 'flex-end',
                    padding: '0.35rem 0.65rem',
                    borderRadius: '999px',
                    background: 'rgba(10,10,16,0.48)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    color: 'var(--text)',
                    fontFamily: 'var(--mono)',
                    fontSize: '0.54rem',
                    letterSpacing: '0.12em',
                    textTransform: 'uppercase',
                  }}
                >
                  Capture ready
                </div>
                <div
                  style={{
                    display: 'flex',
                    gap: '0.65rem',
                    justifyContent: 'center',
                    flexWrap: 'wrap',
                    pointerEvents: 'auto',
                  }}
                >
                  <button
                    className="btn btn-glass"
                    style={{
                      padding: '0.6rem 1.4rem',
                      fontSize: '0.65rem',
                      borderRadius: '99px',
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      inputRef.current?.click();
                    }}
                    aria-label="Replace image with a new one"
                  >
                    <RefreshCw size={12} /> Replace
                  </button>
                  <button
                    style={{
                      padding: '0.5rem 1.2rem',
                      borderRadius: '99px',
                      fontSize: '0.62rem',
                      fontFamily: 'var(--mono)',
                      fontWeight: 600,
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                      background: 'rgba(239,68,68,0.15)',
                      border: '1px solid rgba(239,68,68,0.3)',
                      color: '#FCA5A5',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onClear();
                    }}
                    aria-label="Remove current image"
                  >
                    <X size={11} style={{ display: 'inline', marginRight: 4 }} /> Remove
                  </button>
                </div>
              </motion.div>
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '1.25rem',
                padding: '2rem',
                textAlign: 'center',
                width: '100%',
              }}
            >
              {/* Framing guide overlay */}
              <FramingGuide active={showFramingGuide} />

              {/* Camera icon with glow */}
              <motion.div
                animate={{
                  boxShadow: drag
                    ? '0 0 40px rgba(200,0,30,0.5), inset 0 0 0 1px rgba(200,0,30,0.4)'
                    : hover
                    ? '0 0 24px rgba(200,0,30,0.3), inset 0 0 0 1px rgba(200,0,30,0.25)'
                    : '0 0 16px rgba(200,0,30,0.15), inset 0 0 0 1px rgba(200,0,30,0.12)',
                }}
                transition={{ duration: 0.3 }}
                className="upload-camera-icon"
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: '1.25rem',
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Camera
                  size={28}
                  style={{
                    color: drag ? 'var(--accent-bright)' : 'var(--text-muted)',
                    transition: 'color 0.3s',
                  }}
                />
              </motion.div>

              <div id="upload-instructions">
                <div
                  style={{
                    fontFamily: 'var(--serif)',
                    fontSize: '1.15rem',
                    fontWeight: 600,
                    marginBottom: '0.4rem',
                    letterSpacing: '-0.01em',
                  }}
                >
                  {drag ? 'Drop to upload' : cameraMode ? 'Capture Photo' : 'Capture or Upload'}
                </div>
                <p
                  style={{
                    fontSize: '0.72rem',
                    color: 'var(--text-muted)',
                    lineHeight: 1.6,
                    maxWidth: 220,
                  }}
                >
                  Inner lower eyelid, bright daylight, no flash
                </p>
              </div>

              {/* Action buttons - file and camera */}
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                <button
                  className="btn btn-glass"
                  style={{
                    padding: '0.55rem 1.5rem',
                    fontSize: '0.65rem',
                    borderRadius: '99px',
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setCameraMode(false);
                    inputRef.current?.click();
                  }}
                  aria-label="Select image from device"
                >
                  Select Image
                </button>
                <button
                  className="btn btn-glass"
                  style={{
                    padding: '0.55rem 1.2rem',
                    fontSize: '0.65rem',
                    borderRadius: '99px',
                    display: cameraMode ? 'none' : 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setCameraMode(true);
                    setShowFramingGuide(true);
                    cameraInputRef.current?.click();
                  }}
                  aria-label="Open camera to capture photo"
                >
                  <Camera size={12} /> Camera
                </button>
                <button
                  className="btn btn-glass"
                  style={{
                    padding: '0.55rem 1.2rem',
                    fontSize: '0.65rem',
                    borderRadius: '99px',
                    display: cameraMode && showFramingGuide ? 'flex' : 'none',
                    alignItems: 'center',
                    gap: '0.4rem',
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowFramingGuide(false);
                    cameraInputRef.current?.click();
                  }}
                  aria-label="Open camera with framing guide"
                >
                  <Grid3X3 size={12} /> With Guide
                </button>
              </div>

              {/* Corner HUD marks */}
              {[
                { top: 12, left: 12, bt: '2px solid', bl: '2px solid' },
                { top: 12, right: 12, bt: '2px solid', br: '2px solid' },
                { bottom: 12, left: 12, bb: '2px solid', bl: '2px solid' },
                { bottom: 12, right: 12, bb: '2px solid', br: '2px solid' },
              ].map((c, i) => (
                <div
                  key={i}
                  style={{
                    position: 'absolute',
                    width: 14,
                    height: 14,
                    top: c.top,
                    left: c.left,
                    right: c.right,
                    bottom: c.bottom,
                    borderTop: c.bt,
                    borderLeft: c.bl,
                    borderBottom: c.bb,
                    borderRight: c.br,
                    borderColor: 'rgba(200,0,30,0.3)',
                    opacity: drag ? 1 : 0.5,
                    transition: 'opacity 0.3s',
                  }}
                />
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Enhanced drag overlay */}
        <AnimatePresence>
          {drag && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'rgba(200,0,30,0.08)',
                backdropFilter: 'blur(8px)',
                zIndex: 25,
                pointerEvents: 'none',
              }}
            >
              <motion.div
                animate={{
                  scale: [1, 1.1, 1],
                  rotate: [0, 5, -5, 0],
                }}
                transition={{ duration: 1, repeat: Infinity }}
                style={{
                  width: 100,
                  height: 100,
                  borderRadius: '50%',
                  border: '2px dashed rgba(200,0,30,0.5)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Camera size={36} color="var(--accent-bright)" />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button
          className="btn-premium-primary"
          style={{ flex: 1, padding: '0.8rem', fontSize: '0.72rem' }}
          onClick={onRunQuality}
          disabled={disabled || loading}
          aria-label={loading ? 'Analysis in progress' : 'Run image quality validation'}
          aria-busy={loading}
        >
          {loading ? (
            <>
              <div className="loader-cinematic" style={{ transform: 'scale(0.3)', display: 'inline-block', marginRight: '0.5rem', verticalAlign: 'middle' }}></div>
              Analyzing...
            </>
          ) : (
            <>
              <ShieldCheck size={14} style={{ marginRight: '0.4rem', verticalAlign: 'middle', display: 'inline-block' }} /> Validate Quality
            </>
          )}
        </button>
        <button
          className="btn-premium-glass"
          style={{ padding: '0.8rem 1.25rem', fontSize: '0.72rem' }}
          onClick={onClear}
          disabled={!previewUrl}
          aria-label="Clear current image"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
