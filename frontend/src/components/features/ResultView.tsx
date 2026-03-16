import { useEffect, useState } from 'react';
import { Download, Info, Share2, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import type { AnalyzeResponse } from '../../types';

const E = [0.22, 1, 0.36, 1] as const;

// Animated number counter hook
function useCountUp(target: number, duration = 1400, delay = 300) {
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

// Radial arc for risk %
function RiskArc({ value, color }: { value: number; color: string }) {
  const r = 44, circ = 2 * Math.PI * r;
  const dash = (value / 100) * circ;
  return (
    <div style={{ position:'relative', width:108, height:108 }}>
      <svg width="108" height="108" style={{ transform:'rotate(-90deg)' }}>
        <circle cx="54" cy="54" r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="5" />
        <motion.circle
          cx="54" cy="54" r={r} fill="none"
          stroke={color} strokeWidth="5" strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - dash }}
          transition={{ duration: 1.4, delay: 0.4, ease: E }}
          style={{ filter:`drop-shadow(0 0 8px ${color})` }}
        />
      </svg>
      <div style={{ position:'absolute', inset:0, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center' }}>
        <span style={{ fontFamily:'var(--mono)', fontWeight:700, fontSize:'1.15rem', color, lineHeight:1 }}>{value}%</span>
        <span style={{ fontSize:'0.48rem', fontFamily:'var(--mono)', color:'var(--text-dim)', letterSpacing:'0.1em', textTransform:'uppercase', marginTop:3 }}>Risk</span>
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
  const bandBg     = isHigh ? 'rgba(239,68,68,0.08)' : isModerate ? 'rgba(245,158,11,0.08)' : 'rgba(16,185,129,0.08)';
  const bandBorder = isHigh ? 'rgba(239,68,68,0.25)' : isModerate ? 'rgba(245,158,11,0.25)' : 'rgba(16,185,129,0.25)';
  const bandGlow   = isHigh ? 'rgba(239,68,68,0.18)' : isModerate ? 'rgba(245,158,11,0.14)' : 'rgba(16,185,129,0.14)';

  const hbRaw  = analysis.prediction?.predicted_hemoglobin ?? 0;
  const risk   = Math.round((analysis.prediction?.anemia_risk ?? 0) * 100);
  const conf   = Math.round((analysis.prediction?.confidence ?? 0) * 100);
  const hbAnim = useCountUp(hbRaw, 1400, 300);

  const statCards = [
    { label:'Hb Estimate',  val:`${hbAnim.toFixed(1)} g/dL` },
    { label:'Anemia Risk',  val:`${risk}%` },
    { label:'Confidence',   val:`${conf}%` },
    { label:'Reliability',  val: analysis.prediction?.reliability_flag ?? 'N/A' },
  ];

  return (
    <div className="result-grid" style={{ display:'grid', gridTemplateColumns:'1fr 320px', gap:'2rem', alignItems:'start' }}>

      {/* ── Left column ── */}
      <div style={{ display:'flex', flexDirection:'column', gap:'1.5rem' }}>

        {/* Main result card */}
        <motion.div className="glass"
          initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }}
          transition={{ duration:0.5, ease:E }}
          style={{
            padding:'2.5rem',
            borderLeft:`3px solid ${bandColor}`,
            background: bandBg,
            boxShadow:`inset 0 1px 0 rgba(255,255,255,0.12), -6px 0 60px ${bandGlow}, 0 48px 100px rgba(0,0,0,0.6)`,
            position:'relative', overflow:'hidden',
          }}
        >
          {/* Ambient glow blob — larger + stronger */}
          <motion.div
            animate={{ scale:[1,1.15,1], opacity:[0.14,0.22,0.14] }}
            transition={{ duration:5, repeat:Infinity, ease:'easeInOut' }}
            style={{ position:'absolute', top:-100, right:-100, width:400, height:400, borderRadius:'50%', background:bandColor, filter:'blur(140px)', pointerEvents:'none' }}
          />

          <div style={{ position:'relative', zIndex:1 }}>
            {/* Triage badge + Hb animated value + Risk arc */}
            <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', marginBottom:'1.75rem', flexWrap:'wrap', gap:'1rem' }}>
              <div style={{ flex:1 }}>
                <span style={{
                  display:'inline-block', padding:'0.3rem 0.9rem', borderRadius:'99px',
                  fontSize:'0.55rem', fontFamily:'var(--mono)', fontWeight:600, letterSpacing:'0.15em', textTransform:'uppercase',
                  background: bandBg, border:`1px solid ${bandBorder}`, color: bandColor, marginBottom:'0.75rem',
                }}>{analysis.triage.label}</span>
                <h2 style={{ fontFamily:'var(--serif)', fontSize:'clamp(1.6rem,3vw,2.4rem)', fontWeight:700, lineHeight:1.05, letterSpacing:'-0.03em' }}>
                  {analysis.triage.label}
                </h2>
              </div>
              {/* Hb counter */}
              <div style={{ textAlign:'right' }}>
                <div style={{ fontFamily:'var(--serif)', fontSize:'clamp(3.5rem,7vw,5.5rem)', fontWeight:700, lineHeight:1, color:bandColor, letterSpacing:'-0.04em' }}>
                  {hbAnim.toFixed(1)}
                </div>
                <div style={{ fontFamily:'var(--mono)', fontSize:'0.65rem', color:'var(--text-dim)', letterSpacing:'0.15em', textTransform:'uppercase' }}>g/dL Hemoglobin</div>
              </div>
              {/* Risk arc */}
              <RiskArc value={risk} color={bandColor} />
            </div>

            <p style={{ fontSize:'0.9rem', color:'var(--text-muted)', lineHeight:1.7, marginBottom:'2rem', maxWidth:560 }}>
              {analysis.triage.summary}
            </p>

            {/* Stat grid — hover lift + glow */}
            <div className="stat-grid" style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:'0.75rem', marginBottom:'1.75rem' }}>
              {statCards.map((s, i) => (
                <motion.div key={s.label}
                  initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }}
                  transition={{ delay:0.1 + i*0.07, duration:0.4, ease:E }}
                  whileHover={{ y:-4, boxShadow:`0 0 24px ${bandColor}33, 0 12px 32px rgba(0,0,0,0.4)` }}
                  style={{
                    padding:'1rem', borderRadius:'1rem', cursor:'default',
                    background:'rgba(255,255,255,0.03)', border:'1px solid rgba(255,255,255,0.08)',
                    transition:'border-color 0.3s',
                  }}
                >
                  <div style={{ fontSize:'0.55rem', fontFamily:'var(--mono)', color:'var(--text-dim)', letterSpacing:'0.12em', textTransform:'uppercase', marginBottom:'0.4rem' }}>{s.label}</div>
                  <div style={{ fontWeight:700, fontSize:'0.95rem' }}>{s.val}</div>
                </motion.div>
              ))}
            </div>

            {/* Disclaimer */}
            <div style={{ display:'flex', gap:'0.75rem', alignItems:'flex-start', padding:'1rem 1.25rem', borderRadius:'0.875rem', background:'rgba(255,255,255,0.02)', border:'1px solid rgba(255,255,255,0.06)' }}>
              <Info size={14} style={{ color:'var(--accent-bright)', flexShrink:0, marginTop:2 }} />
              <p style={{ fontSize:'0.7rem', color:'var(--text-dim)', lineHeight:1.6 }}>{analysis.triage.disclaimer}</p>
            </div>
          </div>
        </motion.div>

        {/* Bottom two cards */}
        <div className="result-bottom-grid" style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'1.5rem' }}>

          {/* Clinical Guidance */}
          <motion.div className="glass"
            initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }}
            transition={{ delay:0.15, duration:0.5, ease:E }}
            style={{ padding:'2rem' }}
          >
            <div className="section-eyebrow" style={{ marginBottom:'1.25rem' }}>Clinical Guidance</div>
            <div style={{ display:'flex', gap:'0.875rem', alignItems:'flex-start', marginBottom:'1.5rem' }}>
              <div style={{ width:36, height:36, borderRadius:'0.75rem', flexShrink:0, background:'rgba(200,0,30,0.12)', border:'1px solid rgba(200,0,30,0.2)', display:'flex', alignItems:'center', justifyContent:'center', color:'var(--accent-bright)' }}>
                <AlertCircle size={16} />
              </div>
              <div>
                <div style={{ fontWeight:600, fontSize:'0.85rem', marginBottom:'0.25rem' }}>
                  {analysis.insight_pack.follow_up_timeline[0]?.window ?? 'Next Steps'}
                </div>
                <p style={{ fontSize:'0.75rem', color:'var(--text-muted)', lineHeight:1.55 }}>
                  {analysis.insight_pack.follow_up_timeline[0]?.action ?? analysis.guidance.urgency_guidance}
                </p>
              </div>
            </div>
            <ul style={{ display:'flex', flexDirection:'column', gap:'0.625rem' }}>
              {analysis.guidance.next_steps.slice(0, 4).map((step, i) => (
                <li key={i} style={{ display:'flex', gap:'0.625rem', alignItems:'flex-start' }}>
                  <div style={{ width:16, height:16, borderRadius:'50%', border:'1px solid rgba(255,255,255,0.12)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, marginTop:2 }}>
                    <div style={{ width:5, height:5, borderRadius:'50%', background:'var(--accent-bright)' }} />
                  </div>
                  <span style={{ fontSize:'0.75rem', color:'var(--text-muted)', lineHeight:1.5 }}>{step}</span>
                </li>
              ))}
            </ul>
          </motion.div>

          {/* Biomarker Analysis */}
          <motion.div className="glass"
            initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }}
            transition={{ delay:0.22, duration:0.5, ease:E }}
            style={{ padding:'2rem', display:'flex', flexDirection:'column', gap:'0' }}
          >
            <div className="section-eyebrow" style={{ marginBottom:'1.25rem' }}>Biomarker Analysis</div>
            <div style={{ display:'flex', flexDirection:'column', gap:'1.25rem', flex:1 }}>
              {[
                { label:'Conjunctival Pallor', val: analysis.prediction?.anemia_risk ?? 0 },
                { label:'Vascular Density',    val: 1 - (analysis.prediction?.anemia_risk ?? 0) },
                { label:'Chromatic Stability', val: analysis.prediction?.confidence ?? 0 },
              ].map((m, i) => (
                <div key={m.label}>
                  <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'0.4rem' }}>
                    <span style={{ fontSize:'0.72rem', color:'var(--text-muted)', fontFamily:'var(--mono)' }}>{m.label}</span>
                    <span style={{ fontSize:'0.75rem', fontWeight:700, fontFamily:'var(--mono)' }}>{Math.round(m.val*100)}%</span>
                  </div>
                  <div className="progress-track">
                    <motion.div
                      initial={{ width:0 }} animate={{ width:`${m.val*100}%` }}
                      transition={{ duration:1.2, delay:0.3 + i*0.1, ease:E }}
                      style={{ height:'100%', borderRadius:'99px', background:`linear-gradient(90deg, var(--crimson), var(--accent-bright))`, boxShadow:'0 0 8px var(--crimson-glow)' }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <motion.button className="btn btn-glass"
              whileHover={{ scale:1.02 }} whileTap={{ scale:0.97 }}
              style={{ marginTop:'1.5rem', width:'100%', padding:'0.7rem', fontSize:'0.65rem', borderRadius:'0.875rem', cursor:'none' }}
              onClick={onDownload}
            >
              <Download size={13} /> Export Clinical Report
            </motion.button>
          </motion.div>
        </div>
      </div>

      {/* ── Right sidebar ── */}
      <div style={{ display:'flex', flexDirection:'column', gap:'1.5rem' }}>

        {/* Handoff summary */}
        <motion.div className="glass"
          initial={{ opacity:0, x:20 }} animate={{ opacity:1, x:0 }}
          transition={{ delay:0.1, duration:0.5, ease:E }}
          style={{ padding:'2rem', borderLeft:'3px solid rgba(200,0,30,0.5)', boxShadow:'inset 0 1px 0 rgba(255,255,255,0.12), -4px 0 30px rgba(200,0,30,0.1), 0 40px 80px rgba(0,0,0,0.5)' }}
        >
          <div className="section-eyebrow" style={{ marginBottom:'1.25rem' }}>Handoff Summary</div>
          <div style={{
            padding:'1.25rem', borderRadius:'0.875rem',
            background:'rgba(0,0,0,0.4)', border:'1px solid rgba(255,255,255,0.05)',
            fontFamily:'var(--mono)', fontSize:'0.65rem', color:'var(--text-muted)',
            lineHeight:1.9, marginBottom:'1.25rem',
            maxHeight:200, overflowY:'auto',
          }}>
            {analysis.handoff_summary.share_text}
          </div>
          <motion.button
            className="btn btn-primary"
            whileHover={{ scale:1.02 }} whileTap={{ scale:0.97 }}
            style={{ width:'100%', padding:'0.75rem', fontSize:'0.68rem', cursor:'none' }}
            onClick={() => navigator.share?.({ text: analysis.handoff_summary.share_text })}
          >
            <Share2 size={13} /> Share with Provider
          </motion.button>
        </motion.div>

        {/* Disclaimer */}
        <motion.div className="glass"
          initial={{ opacity:0, x:20 }} animate={{ opacity:1, x:0 }}
          transition={{ delay:0.2, duration:0.5, ease:E }}
          style={{ padding:'2rem' }}
        >
          <div className="label-tag" style={{ marginBottom:'1rem' }}>Medical Disclaimer</div>
          <p style={{ fontSize:'0.65rem', color:'var(--text-dim)', lineHeight:1.7, fontStyle:'italic', marginBottom:'1.5rem' }}>
            This tool does not provide medical advice. It is intended for informational purposes only and is not a substitute for professional medical advice, diagnosis, or treatment.
          </p>
          <motion.button
            className="btn btn-glass"
            whileHover={{ scale:1.02 }} whileTap={{ scale:0.97 }}
            style={{ width:'100%', padding:'0.7rem', fontSize:'0.65rem', borderRadius:'0.875rem', cursor:'none' }}
            onClick={onReset}
          >
            Start New Screening
          </motion.button>
        </motion.div>
      </div>
    </div>
  );
}
