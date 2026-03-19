import { useState } from 'react';
import { CheckCircle, Activity, Zap, Wind, Eye, Droplets, Utensils } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { SymptomInput } from '../../types';

const E = [0.22, 1, 0.36, 1] as const;

const SYMPTOM_ICONS: Record<string, React.ReactNode> = {
  fatigue:                <Activity size={18} />,
  dizziness:              <Zap size={18} />,
  pale_skin:              <Eye size={18} />,
  shortness_of_breath:    <Wind size={18} />,
  heavy_menstrual_bleeding: <Droplets size={18} />,
  poor_diet_low_iron:     <Utensils size={18} />,
};

const HINDI_LABELS: Record<string, string> = {
  fatigue:                  'थकान',
  dizziness:                'चक्कर आना',
  pale_skin:                'पीली त्वचा',
  shortness_of_breath:      'सांस की तकलीफ',
  heavy_menstrual_bleeding: 'अत्यधिक मासिक रक्तस्राव',
  poor_diet_low_iron:       'आयरन की कमी',
};

const LANG_KEY = 'anemialens.symptom-lang';

interface SymptomViewProps {
  symptoms: SymptomInput;
  toggleSymptom: (key: keyof SymptomInput) => void;
  onContinue: () => void;
  onBack: () => void;
  loading: boolean;
  symptomLabels: Record<keyof SymptomInput, string>;
}

export function SymptomView({ symptoms, toggleSymptom, onContinue, onBack, loading, symptomLabels }: SymptomViewProps) {
  const [lang, setLang] = useState<'en' | 'hi'>(() => {
    try { return (localStorage.getItem(LANG_KEY) as 'en' | 'hi') || 'en'; } catch { return 'en'; }
  });

  const switchLang = (l: 'en' | 'hi') => {
    setLang(l);
    try { localStorage.setItem(LANG_KEY, l); } catch { /* ignore */ }
  };

  const getLabel = (key: string) => lang === 'hi' ? (HINDI_LABELS[key] ?? symptomLabels[key as keyof typeof symptomLabels]) : symptomLabels[key as keyof typeof symptomLabels];

  const keys = Object.keys(symptomLabels) as Array<keyof SymptomInput>;
  const selectedCount = keys.filter(k => symptoms[k] === true).length;
  const riskLevel = selectedCount === 0 ? 'None' : selectedCount <= 2 ? 'Low' : selectedCount <= 4 ? 'Moderate' : 'High';
  const riskColor = selectedCount === 0 ? 'var(--text-dim)' : selectedCount <= 2 ? '#10B981' : selectedCount <= 4 ? '#F59E0B' : '#EF4444';

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:'2rem' }}>

      {/* Header */}
      <motion.div initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }} transition={{ duration:0.5, ease:E }}
        style={{ display:'flex', alignItems:'flex-end', justifyContent:'space-between', flexWrap:'wrap', gap:'1rem' }}
      >
        <div>
          <div className="section-eyebrow" style={{ marginBottom:'0.6rem' }}>Phase 03</div>
          <h3 style={{ fontFamily:'var(--serif)', fontSize:'clamp(1.8rem,3vw,2.6rem)', fontWeight:700, lineHeight:1.05, letterSpacing:'-0.03em' }}>
            {lang === 'hi' ? 'लक्षण प्रोफ़ाइल' : 'Symptom Profile'}
          </h3>
          <p style={{ fontSize:'0.82rem', color:'var(--text-muted)', marginTop:'0.5rem', maxWidth:420, lineHeight:1.65 }}>
            {lang === 'hi'
              ? 'वर्तमान में अनुभव किए जा रहे लक्षण चुनें। यह छवि बायोमार्कर के साथ मिलकर ट्राइएज सटीकता में सुधार करता है।'
              : 'Select any symptoms you\'re currently experiencing. This fuses with the image biomarkers to improve triage accuracy.'}
          </p>
        </div>

        <div style={{ display:'flex', flexDirection:'column', gap:'0.625rem', alignItems:'flex-end' }}>
          {/* Language toggle */}
          <div style={{ display:'flex', borderRadius:'0.625rem', overflow:'hidden', border:'1px solid rgba(255,255,255,0.1)' }}>
            {(['en', 'hi'] as const).map(l => (
              <button key={l} onClick={() => switchLang(l)}
                style={{
                  padding:'0.35rem 0.875rem', fontSize:'0.62rem', fontFamily:'var(--mono)',
                  fontWeight:600, letterSpacing:'0.08em', textTransform:'uppercase', cursor:'pointer',
                  background: lang === l ? 'rgba(200,0,30,0.2)' : 'rgba(255,255,255,0.03)',
                  color: lang === l ? 'var(--accent-bright)' : 'var(--text-dim)',
                  border:'none', transition:'all 0.2s',
                }}>
                {l === 'en' ? 'EN' : 'हिंदी'}
              </button>
            ))}
          </div>

          {/* Live risk indicator */}
          <motion.div className="glass"
            style={{ padding:'1rem 1.5rem', display:'flex', alignItems:'center', gap:'1rem', minWidth:160 }}
            animate={{ borderColor: selectedCount > 0 ? riskColor + '44' : 'rgba(255,255,255,0.11)' }}
          >
            <div style={{ position:'relative' }}>
              <div style={{ width:10, height:10, borderRadius:'50%', background:riskColor, boxShadow:`0 0 10px ${riskColor}` }} />
              {selectedCount > 0 && (
                <motion.div
                  animate={{ scale:[1,2,1], opacity:[0.6,0,0.6] }}
                  transition={{ duration:2, repeat:Infinity }}
                  style={{ position:'absolute', inset:0, borderRadius:'50%', background:riskColor }}
                />
              )}
            </div>
            <div>
              <div style={{ fontSize:'0.55rem', fontFamily:'var(--mono)', color:'var(--text-dim)', letterSpacing:'0.12em', textTransform:'uppercase' }}>
                {lang === 'hi' ? 'लक्षण जोखिम' : 'Symptom Risk'}
              </div>
              <div style={{ fontFamily:'var(--mono)', fontWeight:700, fontSize:'0.85rem', color:riskColor }}>{riskLevel}</div>
            </div>
          </motion.div>
        </div>
      </motion.div>

      {/* Symptom grid */}
      <div className="symptom-grid" style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(160px, 1fr))', gap:'0.875rem' }}>
        {keys.map((key, i) => {
          const active = symptoms[key] === true;
          const icon = SYMPTOM_ICONS[key as string] ?? <Activity size={18} />;
          return (
            <motion.button key={key} type="button"
              onClick={() => toggleSymptom(key)}
              initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }}
              transition={{ delay:i*0.055, duration:0.4, ease:E }}
              whileHover={{ y:-4 }}
              whileTap={{ scale:0.97 }}
              style={{
                position:'relative', textAlign:'left', padding:'1.4rem',
                borderRadius:'1.25rem', cursor:'pointer',
                background: active
                  ? 'linear-gradient(135deg, rgba(200,0,30,0.2) 0%, rgba(200,0,30,0.07) 100%)'
                  : 'rgba(255,255,255,0.03)',
                border: active ? '1px solid rgba(200,0,30,0.4)' : '1px solid rgba(255,255,255,0.08)',
                boxShadow: active
                  ? 'inset 0 1px 0 rgba(255,120,120,0.2), 0 0 28px rgba(200,0,30,0.18), 0 16px 40px rgba(0,0,0,0.4)'
                  : 'inset 0 1px 0 rgba(255,255,255,0.06), 0 8px 24px rgba(0,0,0,0.25)',
                transition:'background 0.3s, border-color 0.3s, box-shadow 0.3s',
              }}
            >
              <div style={{
                width:38, height:38, borderRadius:'0.875rem', marginBottom:'0.875rem',
                display:'flex', alignItems:'center', justifyContent:'center',
                background: active ? 'rgba(255,255,255,0.18)' : 'rgba(255,255,255,0.05)',
                color: active ? '#fff' : 'var(--text-muted)',
                transition:'all 0.3s',
                boxShadow: active ? '0 0 16px rgba(200,0,30,0.3)' : 'none',
              }}>{icon}</div>

              <div style={{ fontWeight:600, fontSize:'0.82rem', color: active ? 'var(--text)' : 'var(--text-secondary)', lineHeight:1.3, marginBottom:'0.3rem' }}>
                {getLabel(key as string)}
              </div>
              <div style={{ fontSize:'0.52rem', fontFamily:'var(--mono)', letterSpacing:'0.12em', textTransform:'uppercase', color: active ? 'rgba(255,255,255,0.45)' : 'var(--text-dim)' }}>
                {active ? (lang === 'hi' ? '● चुना गया' : '● Selected') : (lang === 'hi' ? '○ यदि मौजूद हो' : '○ Tap if present')}
              </div>

              <AnimatePresence>
                {active && (
                  <motion.div
                    initial={{ scale:0, opacity:0 }} animate={{ scale:1, opacity:1 }} exit={{ scale:0, opacity:0 }}
                    transition={{ type:'spring', stiffness:400, damping:20 }}
                    style={{ position:'absolute', top:'0.75rem', right:'0.75rem' }}
                  >
                    <CheckCircle size={15} style={{ color:'rgba(255,255,255,0.55)' }} />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.button>
          );
        })}
      </div>

      {/* Footer */}
      <motion.div className="glass"
        initial={{ opacity:0, y:12 }} animate={{ opacity:1, y:0 }}
        transition={{ delay:0.35, duration:0.5, ease:E }}
        style={{ padding:'1.25rem 1.75rem', display:'flex', alignItems:'center', justifyContent:'space-between', gap:'1rem', flexWrap:'wrap' }}
      >
        <div style={{ display:'flex', alignItems:'center', gap:'1rem' }}>
          <motion.div
            animate={{ background: selectedCount > 0 ? 'linear-gradient(135deg, rgba(200,0,30,0.25), rgba(200,0,30,0.08))' : 'rgba(255,255,255,0.04)' }}
            style={{ width:46, height:46, borderRadius:'0.875rem', border:'1px solid rgba(200,0,30,0.25)', display:'flex', alignItems:'center', justifyContent:'center', fontFamily:'var(--mono)', fontWeight:700, fontSize:'1.1rem', color:'var(--accent-bright)' }}
          >
            <AnimatePresence mode="wait">
              <motion.span key={selectedCount} initial={{ y:-8, opacity:0 }} animate={{ y:0, opacity:1 }} exit={{ y:8, opacity:0 }} transition={{ duration:0.2 }}>
                {selectedCount}
              </motion.span>
            </AnimatePresence>
          </motion.div>
          <div>
            <div style={{ fontWeight:600, fontSize:'0.85rem' }}>
              {lang === 'hi' ? `${selectedCount} लक्षण चुने गए` : 'Symptoms Selected'}
            </div>
            <div style={{ fontSize:'0.65rem', color:'var(--text-dim)' }}>
              {lang === 'hi' ? 'छवि बायोमार्कर के साथ मिलाया गया' : 'Fused with image biomarkers for triage'}
            </div>
          </div>
        </div>
        <div style={{ display:'flex', gap:'0.75rem' }}>
          <button className="btn btn-glass" style={{ padding:'0.65rem 1.5rem', fontSize:'0.7rem' }} onClick={onBack}>
            {lang === 'hi' ? 'वापस' : 'Back'}
          </button>
          <button className="btn btn-primary" style={{ padding:'0.65rem 1.75rem', fontSize:'0.7rem' }} onClick={onContinue} disabled={loading}>
            {loading
              ? <><span style={{ display:'inline-block', width:11, height:11, border:'2px solid rgba(255,255,255,0.3)', borderTopColor:'#fff', borderRadius:'50%', animation:'spin 0.8s linear infinite', marginRight:6 }} />Analyzing...</>
              : (lang === 'hi' ? 'निदान चलाएं' : 'Run Diagnostics')
            }
          </button>
        </div>
      </motion.div>
    </div>
  );
}
