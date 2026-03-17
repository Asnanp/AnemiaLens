import { useEffect, useState } from 'react';
import { Download, Info, Share2, AlertCircle, RefreshCw } from 'lucide-react';
import { motion } from 'framer-motion';
import type { AnalyzeResponse } from '../../types';

const E = [0.22, 1, 0.36, 1] as const;

function useCountUp(target: number, duration = 1600, delay = 200) {
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

function RiskArc({ value, color }: { value: number; color: string }) {
  const r = 52, circ = 2 * Math.PI * r;
  return (
    <div style={{ position:'relative', width:124, height:124, flexShrink:0 }}>
      <svg width="124" height="124" style={{ transform:'rotate(-90deg)' }}>
        <circle cx="62" cy="62" r={r} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="6" />
        <motion.circle cx="62" cy="62" r={r} fill="none"
          stroke={color} strokeWidth="6" strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - (value/100)*circ }}
          transition={{ duration:1.6, delay:0.5, ease:E }}
          style={{ filter:`drop-shadow(0 0 10px ${color})` }}
        />
      </svg>
      <div style={{ position:'absolute', inset:0, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center' }}>
        <span style={{ fontFamily:'var(--mono)', fontWeight:700, fontSize:'1.4rem', color, lineHeight:1 }}>{value}%</span>
        <span style={{ fontSize:'0.6rem', fontFamily:'var(--mono)', color:'var(--text-dim)', letterSpacing:'0.12em', textTransform:'uppercase', marginTop:4 }}>Risk Score</span>
      </div>
    </div>
  );
}

interface ResultViewProps {
  analysis: AnalyzeResponse;
  onReset: () => void;
  onDownload: () => void;
}

export function ResultView({ analysis, onReset, onDownload }: ResultViewProps) {
  const isHigh     = analysis.triage.band === 'high_concern';
  const isModerate = analysis.triage.band === 'moderate_risk';
  const bandColor  = isHigh ? '#EF4444' : isModerate ? '#F59E0B' : '#10B981';
  const bandBg     = isHigh ? 'rgba(239,68,68,0.07)' : isModerate ? 'rgba(245,158,11,0.07)' : 'rgba(16,185,129,0.07)';
  const bandBorder = isHigh ? 'rgba(239,68,68,0.3)'  : isModerate ? 'rgba(245,158,11,0.3)'  : 'rgba(16,185,129,0.3)';
  const bandGlow   = isHigh ? 'rgba(239,68,68,0.2)'  : isModerate ? 'rgba(245,158,11,0.15)' : 'rgba(16,185,129,0.15)';

  const hbRaw  = analysis.prediction?.predicted_hemoglobin ?? 0;
  const risk   = Math.round((analysis.triage.score ?? analysis.prediction?.anemia_risk ?? 0) * 100);
  const conf   = Math.round((analysis.prediction?.confidence ?? 0) * 100);
  const hbAnim = useCountUp(hbRaw, 1600, 200);

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:'1.5rem' }}>

      {/* ── HERO CARD — full-width Hb display ── */}
      <motion.div className="glass result-hero-card"
        initial={{ opacity:0, y:24 }} animate={{ opacity:1, y:0 }}
        transition={{ duration:0.6, ease:E }}
        style={{ padding:'clamp(1.25rem, 4vw, 3rem)', borderLeft:`4px solid ${bandColor}`, background:bandBg,
          boxShadow:`inset 0 1px 0 rgba(255,255,255,0.12), -8px 0 80px ${bandGlow}, 0 60px 120px rgba(0,0,0,0.6)`,
          position:'relative', overflow:'hidden' }}
      >
        {/* Ambient glow */}
        <motion.div animate={{ scale:[1,1.2,1], opacity:[0.12,0.2,0.12] }}
          transition={{ duration:6, repeat:Infinity, ease:'easeInOut' }}
          style={{ position:'absolute', top:-120, right:-120, width:500, height:500, borderRadius:'50%', background:bandColor, filter:'blur(160px)', pointerEvents:'none' }}
        />
        <div style={{ position:'relative', zIndex:1 }}>
          {/* Top row: badge + label */}
          <div style={{ display:'flex', alignItems:'center', gap:'1rem', marginBottom:'2rem', flexWrap:'wrap' }}>
            <span style={{ padding:'0.35rem 1rem', borderRadius:'99px', fontSize:'0.55rem',
              fontFamily:'var(--mono)', fontWeight:700, letterSpacing:'0.15em', textTransform:'uppercase',
              background:bandBg, border:`1px solid ${bandBorder}`, color:bandColor }}>
              {analysis.triage.label}
            </span>
            {analysis.guidance.source === 'mistral' && (
              <span style={{ padding:'0.35rem 0.9rem', borderRadius:'99px', fontSize:'0.55rem',
                fontFamily:'var(--mono)', fontWeight:600, letterSpacing:'0.12em', textTransform:'uppercase',
                background:'rgba(0,194,255,0.07)', border:'1px solid rgba(0,194,255,0.25)', color:'rgba(0,194,255,0.9)' }}>
                Mistral AI
              </span>
            )}
          </div>

          {/* Main metrics row */}
          <div className="result-metrics-row" style={{ display:'flex', alignItems:'center', gap:'3rem', flexWrap:'wrap', marginBottom:'2rem' }}>
            {/* Giant Hb number */}
            <div>
              <div style={{ fontFamily:'var(--serif)', fontSize:'clamp(3.5rem,10vw,8rem)', fontWeight:300,
                lineHeight:1, letterSpacing:'-0.04em', color:bandColor,
                textShadow:`0 0 80px ${bandColor}40` }}>
                {hbAnim.toFixed(1)}
              </div>
              <div style={{ fontFamily:'var(--mono)', fontSize:'0.65rem', color:'var(--text-dim)',
                letterSpacing:'0.2em', textTransform:'uppercase', marginTop:'0.5rem' }}>
                g/dL Hemoglobin
              </div>
            </div>

            {/* Divider — hidden on mobile */}
            <div className="result-divider" style={{ width:1, height:100, background:'rgba(255,255,255,0.08)', flexShrink:0 }} />

            {/* Risk arc */}
            <RiskArc value={risk} color={bandColor} />

            {/* Divider — hidden on mobile */}
            <div className="result-divider" style={{ width:1, height:100, background:'rgba(255,255,255,0.08)', flexShrink:0 }} />

            {/* Confidence + Reliability */}
            <div style={{ display:'flex', flexDirection:'row', gap:'2rem', flexWrap:'wrap' }}>
              {[
                { label:'Confidence', val:`${conf}%` },
                { label:'Reliability', val: analysis.prediction?.reliability_flag ?? 'N/A' },
              ].map(s => (
                <div key={s.label}>
                  <div style={{ fontFamily:'var(--mono)', fontSize:'0.58rem', color:'var(--text-dim)',
                    textTransform:'uppercase', letterSpacing:'0.15em', marginBottom:'0.25rem' }}>{s.label}</div>
                  <div style={{ fontFamily:'var(--mono)', fontWeight:700, fontSize:'1.1rem', color:'var(--text)' }}>{s.val}</div>
                </div>
              ))}
            </div>

            {/* Triage label — hidden on mobile (already shown in badge above) */}
            <div className="result-triage-label" style={{ marginLeft:'auto' }}>
              <h2 style={{ fontFamily:'var(--serif)', fontSize:'clamp(1.8rem,3vw,2.8rem)', fontWeight:700,
                lineHeight:1.05, letterSpacing:'-0.03em', color:'var(--text)', maxWidth:280 }}>
                {analysis.triage.label}
              </h2>
            </div>
          </div>

          {/* Summary */}
          <p style={{ fontSize:'0.92rem', color:'var(--text-muted)', lineHeight:1.75, maxWidth:700, marginBottom:'1.75rem' }}>
            {analysis.triage.summary}
          </p>

          {/* Disclaimer bar */}
          <div style={{ display:'flex', gap:'0.75rem', alignItems:'flex-start', padding:'1rem 1.25rem',
            borderRadius:'0.875rem', background:'rgba(255,255,255,0.02)', border:'1px solid rgba(255,255,255,0.06)' }}>
            <Info size={14} style={{ color:'var(--accent-bright)', flexShrink:0, marginTop:2 }} />
            <p style={{ fontSize:'0.7rem', color:'var(--text-dim)', lineHeight:1.6 }}>{analysis.triage.disclaimer}</p>
          </div>
        </div>
      </motion.div>

      {/* ── MISTRAL AI GUIDANCE — full-width ── */}
      {analysis.guidance.source === 'mistral' && (
        <motion.div
          initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }}
          transition={{ delay:0.1, duration:0.5, ease:E }}
          style={{ borderRadius:'1.25rem', overflow:'hidden',
            border:'1px solid rgba(0,194,255,0.25)',
            boxShadow:'0 0 80px rgba(0,194,255,0.08), 0 2px 40px rgba(0,0,0,0.4)' }}>

          {/* Top bar */}
          <div style={{ padding:'0.875rem 1.5rem', display:'flex', alignItems:'center', gap:'0.75rem',
            background:'rgba(0,194,255,0.1)', borderBottom:'1px solid rgba(0,194,255,0.15)' }}>
            <div style={{ width:8, height:8, borderRadius:'50%', background:'rgba(0,194,255,1)',
              boxShadow:'0 0 8px rgba(0,194,255,0.8)', animation:'pulse 2s infinite' }} />
            <span style={{ fontFamily:'var(--mono)', fontSize:'0.58rem', fontWeight:700,
              letterSpacing:'0.18em', textTransform:'uppercase', color:'rgba(0,194,255,0.9)' }}>
              Mistral AI · {analysis.guidance.model_used ?? 'mistral-small-latest'}
            </span>
            <span style={{ marginLeft:'auto', fontFamily:'var(--mono)', fontSize:'0.5rem',
              color:'rgba(0,194,255,0.5)', letterSpacing:'0.1em' }}>
              AI-GENERATED CLINICAL GUIDANCE
            </span>
          </div>

          {/* Body */}
          <div style={{ padding:'clamp(1rem, 4vw, 2rem) clamp(1rem, 4vw, 2.5rem)', background:'rgba(0,10,30,0.6)' }}>

            {/* Main explanation — big and clear */}
            <div style={{ marginBottom:'1.75rem', padding:'1.25rem 1.5rem', borderRadius:'0.875rem',
              background:'rgba(0,194,255,0.05)', border:'1px solid rgba(0,194,255,0.12)',
              borderLeft:'3px solid rgba(0,194,255,0.6)' }}>
              <div style={{ fontFamily:'var(--mono)', fontSize:'0.48rem', letterSpacing:'0.15em',
                textTransform:'uppercase', color:'rgba(0,194,255,0.5)', marginBottom:'0.6rem' }}>
                Assessment
              </div>
              <p style={{ fontSize:'1rem', color:'var(--text)', lineHeight:1.8, fontWeight:400 }}>
                {analysis.guidance.explanation}
              </p>
            </div>

            <div className="guidance-2col" style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'1rem', marginBottom:'1.5rem' }}>
              {/* Urgency */}
              <div style={{ padding:'1rem 1.25rem', borderRadius:'0.875rem',
                background:'rgba(239,68,68,0.06)', border:'1px solid rgba(239,68,68,0.2)',
                borderLeft:'3px solid rgba(239,68,68,0.6)' }}>
                <div style={{ fontFamily:'var(--mono)', fontSize:'0.48rem', letterSpacing:'0.15em',
                  textTransform:'uppercase', color:'rgba(239,68,68,0.8)', marginBottom:'0.5rem' }}>
                  ⚠ Urgency
                </div>
                <p style={{ fontSize:'0.85rem', color:'var(--text)', lineHeight:1.65 }}>
                  {analysis.guidance.urgency_guidance}
                </p>
              </div>

              {/* Food advice */}
              <div style={{ padding:'1rem 1.25rem', borderRadius:'0.875rem',
                background:'rgba(0,229,150,0.06)', border:'1px solid rgba(0,229,150,0.2)',
                borderLeft:'3px solid rgba(0,229,150,0.6)' }}>
                <div style={{ fontFamily:'var(--mono)', fontSize:'0.48rem', letterSpacing:'0.15em',
                  textTransform:'uppercase', color:'rgba(0,229,150,0.8)', marginBottom:'0.5rem' }}>
                  ✦ Dietary Advice
                </div>
                <p style={{ fontSize:'0.85rem', color:'var(--text)', lineHeight:1.65 }}>
                  {analysis.guidance.food_advice || 'Maintain a balanced, iron-rich diet.'}
                </p>
              </div>
            </div>

            {/* Next steps */}
            <div>
              <div style={{ fontFamily:'var(--mono)', fontSize:'0.48rem', letterSpacing:'0.15em',
                textTransform:'uppercase', color:'rgba(0,194,255,0.6)', marginBottom:'0.75rem' }}>
                Recommended Next Steps
              </div>
              <div style={{ display:'flex', flexDirection:'column', gap:'0.5rem' }}>
                {analysis.guidance.next_steps.map((step, i) => (
                  <motion.div key={i}
                    initial={{ opacity:0, x:-8 }} animate={{ opacity:1, x:0 }}
                    transition={{ delay:0.3 + i*0.08, duration:0.4, ease:E }}
                    style={{ display:'flex', gap:'1rem', alignItems:'center',
                      padding:'0.75rem 1rem', borderRadius:'0.625rem',
                      background:'rgba(255,255,255,0.03)', border:'1px solid rgba(255,255,255,0.06)' }}>
                    <span style={{ fontFamily:'var(--mono)', fontSize:'0.7rem', color:'rgba(0,194,255,0.7)',
                      fontWeight:700, flexShrink:0, minWidth:24 }}>{i+1}.</span>
                    <span style={{ fontSize:'0.85rem', color:'var(--text)', lineHeight:1.5 }}>{step}</span>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* ── BOTTOM ROW: 3 cards ── */}
      <div className="result-bottom-grid" style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:'1.5rem' }}>

        {/* Clinical Guidance */}
        <motion.div className="glass" initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }}
          transition={{ delay:0.15, duration:0.5, ease:E }}
          style={{ padding:'clamp(1.25rem, 3vw, 2rem)', display:'flex', flexDirection:'column', gap:'1rem',
            ...(analysis.guidance.source === 'mistral' ? { borderTop:'2px solid rgba(0,194,255,0.3)' } : {}) }}>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', gap:'0.75rem' }}>
            <div className="section-eyebrow">Clinical Guidance</div>
            {analysis.guidance.source === 'mistral' ? (
              <span style={{ display:'flex', alignItems:'center', gap:'0.4rem', padding:'0.25rem 0.7rem',
                borderRadius:'99px', fontSize:'0.5rem', fontFamily:'var(--mono)', fontWeight:700,
                letterSpacing:'0.12em', textTransform:'uppercase', whiteSpace:'nowrap',
                background:'rgba(0,194,255,0.08)', border:'1px solid rgba(0,194,255,0.25)', color:'rgba(0,194,255,0.9)' }}>
                <svg width="8" height="8" viewBox="0 0 8 8"><circle cx="4" cy="4" r="4" fill="rgba(0,194,255,0.9)"/></svg>
                Mistral AI
              </span>
            ) : (
              <span style={{ padding:'0.25rem 0.7rem', borderRadius:'99px', fontSize:'0.5rem',
                fontFamily:'var(--mono)', fontWeight:600, letterSpacing:'0.1em', textTransform:'uppercase',
                background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.08)', color:'var(--text-dim)' }}>
                Rule-based
              </span>
            )}
          </div>
          <p style={{ fontSize:'0.8rem', color:'var(--text-muted)', lineHeight:1.65, padding:'0.875rem',
            borderRadius:'0.75rem',
            background: analysis.guidance.source === 'mistral' ? 'rgba(0,194,255,0.04)' : 'rgba(255,255,255,0.03)',
            border: analysis.guidance.source === 'mistral' ? '1px solid rgba(0,194,255,0.12)' : '1px solid rgba(255,255,255,0.07)' }}>
            {analysis.guidance.explanation}
          </p>
          <div style={{ display:'flex', gap:'0.75rem', alignItems:'flex-start' }}>
            <div style={{ width:30, height:30, borderRadius:'0.625rem', flexShrink:0,
              background:'rgba(200,0,30,0.12)', border:'1px solid rgba(200,0,30,0.2)',
              display:'flex', alignItems:'center', justifyContent:'center', color:'var(--accent-bright)' }}>
              <AlertCircle size={13} />
            </div>
            <p style={{ fontSize:'0.73rem', color:'var(--text-muted)', lineHeight:1.55, paddingTop:'0.3rem' }}>
              {analysis.guidance.urgency_guidance}
            </p>
          </div>
          <ul style={{ display:'flex', flexDirection:'column', gap:'0.5rem' }}>
            {analysis.guidance.next_steps.slice(0,4).map((step, i) => (
              <li key={i} style={{ display:'flex', gap:'0.6rem', alignItems:'flex-start' }}>
                <div style={{ width:15, height:15, borderRadius:'50%', border:'1px solid rgba(255,255,255,0.1)',
                  display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, marginTop:2 }}>
                  <div style={{ width:5, height:5, borderRadius:'50%', background:'var(--accent-bright)' }} />
                </div>
                <span style={{ fontSize:'0.73rem', color:'var(--text-muted)', lineHeight:1.5 }}>{step}</span>
              </li>
            ))}
          </ul>
          {analysis.guidance.food_advice && (
            <div style={{ fontSize:'0.7rem', color:'var(--text-dim)', lineHeight:1.6, padding:'0.75rem',
              borderRadius:'0.625rem', background:'rgba(0,229,150,0.04)', border:'1px solid rgba(0,229,150,0.12)',
              display:'flex', gap:'0.6rem', alignItems:'flex-start' }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgba(0,229,150,0.7)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink:0, marginTop:1 }}>
                <path d="M2 22c1.25-1.25 2.5-2.5 3.75-3.75"/>
                <path d="M22 2s-7 0-11 4c-2.5 2.5-3 6-3 6s3.5-.5 6-3c4-4 4-11 4-11z"/>
              </svg>
              {analysis.guidance.food_advice}
            </div>
          )}
        </motion.div>

        {/* Biomarker Analysis */}
        <motion.div className="glass" initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }}
          transition={{ delay:0.22, duration:0.5, ease:E }}
          style={{ padding:'clamp(1.25rem, 3vw, 2rem)', display:'flex', flexDirection:'column', gap:'1.25rem' }}>
          <div className="section-eyebrow">Biomarker Analysis</div>
          {[
            { label:'Conjunctival Pallor', val: analysis.prediction?.anemia_risk ?? 0 },
            { label:'Vascular Density',    val: 1 - (analysis.prediction?.anemia_risk ?? 0) },
            { label:'Chromatic Stability', val: analysis.prediction?.confidence ?? 0 },
          ].map((m, i) => (
            <div key={m.label} className="biomarker-row">
              <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'0.5rem' }}>
                <span style={{ fontSize:'0.72rem', color:'var(--text-muted)', fontFamily:'var(--mono)' }}>{m.label}</span>
                <span style={{ fontSize:'0.75rem', fontWeight:700, fontFamily:'var(--mono)', color:bandColor }}>{Math.round(m.val*100)}%</span>
              </div>
              <div className="progress-track">
                <motion.div initial={{ width:0 }} animate={{ width:`${m.val*100}%` }}
                  transition={{ duration:1.4, delay:0.4+i*0.12, ease:E }}
                  style={{ height:'100%', borderRadius:'99px',
                    background:`linear-gradient(90deg, var(--crimson), ${bandColor})`,
                    boxShadow:`0 0 8px ${bandColor}60` }}
                />
              </div>
            </div>
          ))}
          <motion.button className="btn btn-glass" whileHover={{ scale:1.02 }} whileTap={{ scale:0.97 }}
            style={{ marginTop:'auto', width:'100%', padding:'0.7rem', fontSize:'0.65rem', borderRadius:'0.875rem', cursor:'pointer' }}
            onClick={onDownload}>
            <Download size={13} /> Export Report
          </motion.button>
        </motion.div>

        {/* Handoff + Actions */}
        <motion.div className="glass" initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }}
          transition={{ delay:0.3, duration:0.5, ease:E }}
          style={{ padding:'clamp(1.25rem, 3vw, 2rem)', display:'flex', flexDirection:'column', gap:'1.25rem',
            borderLeft:'3px solid rgba(200,0,30,0.4)',
            boxShadow:'inset 0 1px 0 rgba(255,255,255,0.1), -4px 0 30px rgba(200,0,30,0.08)' }}>
          <div className="section-eyebrow">Handoff Summary</div>
          <div style={{ padding:'1.25rem', borderRadius:'0.875rem', background:'rgba(0,0,0,0.4)',
            border:'1px solid rgba(255,255,255,0.05)', fontFamily:'var(--mono)', fontSize:'0.63rem',
            color:'var(--text-muted)', lineHeight:1.9, flex:1, maxHeight:180, overflowY:'auto' }}>
            {analysis.handoff_summary.share_text}
          </div>
          <motion.button className="btn btn-primary" whileHover={{ scale:1.02 }} whileTap={{ scale:0.97 }}
            style={{ width:'100%', padding:'0.75rem', fontSize:'0.68rem', cursor:'pointer' }}
            onClick={() => navigator.share?.({ text: analysis.handoff_summary.share_text })}>
            <Share2 size={13} /> Share with Provider
          </motion.button>
          <div style={{ padding:'1rem', borderRadius:'0.875rem', background:'rgba(255,255,255,0.02)',
            border:'1px solid rgba(255,255,255,0.05)' }}>
            <p style={{ fontSize:'0.62rem', color:'var(--text-dim)', lineHeight:1.65, fontStyle:'italic', marginBottom:'1rem' }}>
              Not a diagnostic device. Confirm results with clinical blood testing.
            </p>
            <motion.button className="btn btn-glass" whileHover={{ scale:1.02 }} whileTap={{ scale:0.97 }}
              style={{ width:'100%', padding:'0.65rem', fontSize:'0.62rem', borderRadius:'0.75rem', cursor:'pointer' }}
              onClick={onReset}>
              <RefreshCw size={12} /> New Screening
            </motion.button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
