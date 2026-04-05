import { useState, useRef } from 'react';
import { Camera, X, RefreshCw, ShieldCheck } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const E = [0.22, 1, 0.36, 1] as const;

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  previewUrl: string | null;
  onClear: () => void;
  onRunQuality: () => void;
  loading: boolean;
  disabled: boolean;
}

export function UploadZone({ onFileSelect, previewUrl, onClear, onRunQuality, loading, disabled }: UploadZoneProps) {
  const [drag, setDrag] = useState(false);
  const [hover, setHover] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const onDrag = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    setDrag(e.type === 'dragenter' || e.type === 'dragover');
  };
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setDrag(false);
    if (e.dataTransfer.files?.[0]) onFileSelect(e.dataTransfer.files[0]);
  };

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:'1rem' }}>
      <input ref={inputRef} type="file" accept="image/*" style={{ display:'none' }}
        onChange={e => e.target.files?.[0] && onFileSelect(e.target.files[0])} />

      {/* Drop zone */}
      <motion.div
        onDragEnter={onDrag} onDragLeave={onDrag} onDragOver={onDrag} onDrop={onDrop}
        onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
        onClick={() => !previewUrl && inputRef.current?.click()}
        animate={{
          borderColor: drag ? 'rgba(200,0,30,0.6)' : hover && !previewUrl ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.11)',
          background: drag ? 'rgba(200,0,30,0.06)' : 'rgba(255,255,255,0.03)',
        }}
        transition={{ duration: 0.25 }}
        style={{
          position:'relative', aspectRatio:'4/3',
          display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center',
          borderRadius:'1.5rem', border:'1px dashed rgba(255,255,255,0.11)',
          backdropFilter:'blur(20px)', overflow:'hidden',
          cursor: previewUrl ? 'default' : 'pointer',
          boxShadow: drag ? '0 0 40px rgba(200,0,30,0.2), inset 0 1px 0 rgba(255,255,255,0.1)' : 'inset 0 1px 0 rgba(255,255,255,0.06)',
        }}
      >
        <AnimatePresence mode="wait">
          {previewUrl ? (
            <motion.div key="preview"
              initial={{ opacity:0, scale:1.05 }} animate={{ opacity:1, scale:1 }} exit={{ opacity:0 }}
              transition={{ duration:0.4, ease:E }}
              style={{ position:'absolute', inset:0 }}
            >
              <img src={previewUrl} alt="Preview"
                style={{ width:'100%', height:'100%', objectFit:'cover',
                  filter: hover ? 'brightness(0.5)' : 'brightness(1)',
                  transition:'filter 0.4s ease', display:'block' }} />
              {/* Hover overlay */}
              <motion.div
                animate={{ opacity: hover ? 1 : 0.96 }}
                transition={{ duration:0.3 }}
                style={{ position:'absolute', inset:0, display:'flex', flexDirection:'column', justifyContent:'space-between', padding:'1rem', backdropFilter:'blur(4px)' }}
              >
                <div style={{ alignSelf:'flex-end', padding:'0.35rem 0.65rem', borderRadius:'999px', background:'rgba(10,10,16,0.48)', border:'1px solid rgba(255,255,255,0.08)', color:'var(--text)', fontFamily:'var(--mono)', fontSize:'0.54rem', letterSpacing:'0.12em', textTransform:'uppercase' }}>
                  Capture ready
                </div>
                <div style={{ display:'flex', gap:'0.65rem', justifyContent:'center', flexWrap:'wrap' }}>
                  <button className="btn btn-glass" style={{ padding:'0.6rem 1.4rem', fontSize:'0.65rem', borderRadius:'99px' }}
                    onClick={e => { e.stopPropagation(); inputRef.current?.click(); }}>
                    <RefreshCw size={12} /> Replace
                  </button>
                  <button style={{ padding:'0.5rem 1.2rem', borderRadius:'99px', fontSize:'0.62rem', fontFamily:'var(--mono)', fontWeight:600, letterSpacing:'0.08em', textTransform:'uppercase', background:'rgba(239,68,68,0.15)', border:'1px solid rgba(239,68,68,0.3)', color:'#FCA5A5', cursor:'pointer', transition:'all 0.2s' }}
                    onClick={e => { e.stopPropagation(); onClear(); }}>
                    <X size={11} style={{ display:'inline', marginRight:4 }} /> Remove
                  </button>
                </div>
              </motion.div>
            </motion.div>
          ) : (
            <motion.div key="empty"
              initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }}
              transition={{ duration:0.3 }}
              style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:'1.25rem', padding:'2rem', textAlign:'center' }}
            >
              {/* Camera icon with glow */}
              <motion.div
                animate={{ boxShadow: drag
                  ? '0 0 40px rgba(200,0,30,0.5), inset 0 0 0 1px rgba(200,0,30,0.4)'
                  : hover
                    ? '0 0 24px rgba(200,0,30,0.3), inset 0 0 0 1px rgba(200,0,30,0.25)'
                    : '0 0 16px rgba(200,0,30,0.15), inset 0 0 0 1px rgba(200,0,30,0.12)'
                }}
                transition={{ duration:0.3 }}
                className="upload-camera-icon"
                style={{ width:72, height:72, borderRadius:'1.25rem', background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.1)', display:'flex', alignItems:'center', justifyContent:'center' }}
              >
                <Camera size={28} style={{ color: drag ? 'var(--accent-bright)' : 'var(--text-muted)', transition:'color 0.3s' }} />
              </motion.div>

              <div>
                <div style={{ fontFamily:'var(--serif)', fontSize:'1.15rem', fontWeight:600, marginBottom:'0.4rem', letterSpacing:'-0.01em' }}>
                  {drag ? 'Drop to upload' : 'Capture or Upload'}
                </div>
                <p style={{ fontSize:'0.72rem', color:'var(--text-muted)', lineHeight:1.6, maxWidth:220 }}>
                  Inner lower eyelid, bright daylight, no flash
                </p>
              </div>

              <button className="btn btn-glass" style={{ padding:'0.55rem 1.5rem', fontSize:'0.65rem', borderRadius:'99px' }}
                onClick={e => { e.stopPropagation(); inputRef.current?.click(); }}>
                Select Image
              </button>

              {/* Corner HUD marks */}
              {[{top:12,left:12,bt:'2px solid',bl:'2px solid'},{top:12,right:12,bt:'2px solid',br:'2px solid'},{bottom:12,left:12,bb:'2px solid',bl:'2px solid'},{bottom:12,right:12,bb:'2px solid',br:'2px solid'}].map((c,i) => (
                <div key={i} style={{ position:'absolute', width:14, height:14, top:c.top, left:c.left, right:c.right, bottom:c.bottom, borderTop:c.bt, borderLeft:c.bl, borderBottom:c.bb, borderRight:c.br, borderColor:'rgba(200,0,30,0.3)', opacity: drag ? 1 : 0.5, transition:'opacity 0.3s' }} />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Action buttons */}
      <div style={{ display:'flex', gap:'0.75rem' }}>
        <button
          className="btn btn-primary"
          style={{ flex:1, padding:'0.8rem', fontSize:'0.72rem' }}
          onClick={onRunQuality}
          disabled={disabled || loading}
        >
          {loading
            ? <><span style={{ display:'inline-block', width:12, height:12, border:'2px solid rgba(255,255,255,0.3)', borderTopColor:'#fff', borderRadius:'50%', animation:'spin 0.8s linear infinite', marginRight:8 }} />Analyzing...</>
            : <><ShieldCheck size={14} /> Validate Quality</>
          }
        </button>
        <button
          className="btn btn-glass"
          style={{ padding:'0.8rem 1.25rem', fontSize:'0.72rem' }}
          onClick={onClear}
          disabled={!previewUrl}
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
