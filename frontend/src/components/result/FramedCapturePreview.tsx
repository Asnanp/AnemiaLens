import type { AnalyzeResponse } from '../../types';

interface FramedCapturePreviewProps {
  src?: string | null;
  alt: string;
  roiPreview?: AnalyzeResponse['roi_preview'] | null;
}

export function FramedCapturePreview({
  src,
  alt,
  roiPreview,
}: FramedCapturePreviewProps) {
  const box = roiPreview?.roi_box;
  const frameWidth = roiPreview?.frame_width ?? 0;
  const frameHeight = roiPreview?.frame_height ?? 0;
  const hasBox = Boolean(
    box
    && frameWidth > 0
    && frameHeight > 0
    && box.width > 0
    && box.height > 0
  );

  const overlayStyle = hasBox
    ? {
        left: `${(box!.x / frameWidth) * 100}%`,
        top: `${(box!.y / frameHeight) * 100}%`,
        width: `${(box!.width / frameWidth) * 100}%`,
        height: `${(box!.height / frameHeight) * 100}%`,
      }
    : null;

  return (
    <div style={{ borderRadius: '0.85rem', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', minHeight: 112, position: 'relative' }}>
      {src ? (
        <>
          <img
            src={src}
            alt={alt}
            style={{ width: '100%', height: 140, objectFit: 'cover', display: 'block' }}
          />
          {overlayStyle && (
            <div
              style={{
                position: 'absolute',
                border: '2px solid rgba(34,211,238,0.95)',
                boxShadow: '0 0 0 1px rgba(0,0,0,0.35), 0 0 18px rgba(34,211,238,0.45)',
                borderRadius: '0.7rem',
                background: 'rgba(34,211,238,0.08)',
                pointerEvents: 'none',
                ...overlayStyle,
              }}
            />
          )}
        </>
      ) : (
        <div style={{ minHeight: 140, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: '0.72rem' }}>
          Preview unavailable
        </div>
      )}
    </div>
  );
}
