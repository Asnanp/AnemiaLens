import { Activity, Droplets, Eye, HeartPulse, UserRound, UtensilsCrossed, Wind, Zap } from 'lucide-react';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { PatientProfileInput, SymptomInput } from '../../types';
import { MagneticButton } from '../MagneticButton';

const E = [0.22, 1, 0.36, 1] as const;

const SYMPTOM_ICONS: Record<string, React.ReactNode> = {
  fatigue: <Activity size={16} />,
  dizziness: <Zap size={16} />,
  pale_skin: <Eye size={16} />,
  shortness_of_breath: <Wind size={16} />,
  heavy_menstrual_bleeding: <Droplets size={16} />,
  poor_diet_low_iron: <UtensilsCrossed size={16} />,
};

const SEX_OPTIONS: Array<{ value: PatientProfileInput['sex']; label: string }> = [
  { value: 'female', label: 'Female' },
  { value: 'male', label: 'Male' },
  { value: 'other', label: 'Other' },
  { value: 'not_specified', label: 'Skip' },
];

const DIET_OPTIONS: Array<{ value: PatientProfileInput['diet_type']; label: string }> = [
  { value: 'omnivore', label: 'Omnivore' },
  { value: 'vegetarian', label: 'Vegetarian' },
  { value: 'vegan', label: 'Vegan' },
  { value: 'mixed', label: 'Mixed' },
  { value: 'not_specified', label: 'Skip' },
];

type IntakeViewProps = {
  symptoms: SymptomInput;
  patientProfile: PatientProfileInput;
  toggleSymptom: (key: keyof SymptomInput) => void;
  updatePatientProfile: <K extends keyof PatientProfileInput>(key: K, value: PatientProfileInput[K]) => void;
  onContinue: () => void;
  onBack: () => void;
  loading: boolean;
  symptomLabels: Record<keyof SymptomInput, string>;
};

function humanizeList(items: string[]) {
  if (items.length === 0) return 'no reported symptoms';
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(', ')}, and ${items[items.length - 1]}`;
}

export function IntakeView({
  symptoms,
  patientProfile,
  toggleSymptom,
  updatePatientProfile,
  onContinue,
  onBack,
  loading,
  symptomLabels,
}: IntakeViewProps) {
  const [showOptionalContext, setShowOptionalContext] = useState(false);
  const activeSymptoms = (Object.keys(symptomLabels) as Array<keyof SymptomInput>)
    .filter((key) => symptoms[key] === true)
    .map((key) => symptomLabels[key]);

  const optionalProfileSummary = [
    patientProfile.age ? `${patientProfile.age}y` : null,
    patientProfile.sex !== 'not_specified' ? patientProfile.sex : null,
    patientProfile.diet_type !== 'not_specified' ? patientProfile.diet_type : null,
  ]
    .filter(Boolean)
    .join(' / ');

  const caseSummary = activeSymptoms.length > 0
    ? `Reported symptoms include ${humanizeList(activeSymptoms)}. This symptom context will be fused with the conjunctiva image before triage.`
    : 'No symptoms are selected. The screening will lean more heavily on the eye-image signal unless you add symptoms.';

  return (
    <div className="intake-layout" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
      <motion.div
        className="glass"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: E }}
        style={{ padding: '1.75rem', display: 'grid', gap: '1.25rem', alignSelf: 'start' }}
      >
        <div>
          <div className="section-eyebrow" style={{ marginBottom: '0.7rem' }}>Phase 03</div>
          <h3 style={{ fontFamily: 'var(--serif)', fontSize: '2rem', lineHeight: 1.05, letterSpacing: '-0.03em' }}>
            Symptoms First
          </h3>
          <p style={{ marginTop: '0.65rem', color: 'var(--text-muted)', fontSize: '0.84rem', lineHeight: 1.65 }}>
            Start with only the symptom context that actually matters for triage. Extra profile details are optional and stay out of the way.
          </p>
        </div>

        <div style={{ padding: '1rem 1.1rem', borderRadius: '1rem', background: 'rgba(0,194,255,0.05)', border: '1px solid rgba(0,194,255,0.14)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.55rem' }}>
            <UserRound size={15} style={{ color: 'rgba(0,194,255,0.85)' }} />
            <span style={{ fontFamily: 'var(--mono)', fontSize: '0.58rem', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.85)' }}>
              Case summary
            </span>
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.7 }}>
            {caseSummary}
          </div>
        </div>

        <div style={{ display: 'grid', gap: '1rem' }}>
          <div style={{ padding: '1rem 1.05rem', borderRadius: '1rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', display: 'grid', gap: '0.8rem' }}>
            <MagneticButton
              className="btn-glass"
              onClick={() => setShowOptionalContext((current) => !current)}
              style={{
                justifyContent: 'space-between',
                padding: '0.75rem 0.95rem',
                fontSize: '0.64rem',
                borderRadius: '0.9rem',
                border: '1px solid rgba(255,255,255,0.08)',
                background: 'rgba(255,255,255,0.03)',
                width: '100%',
              }}
            >
              Optional context
              <span style={{ color: 'var(--text-dim)' }}>
                {showOptionalContext ? 'Hide' : 'Add details'}
              </span>
            </MagneticButton>
            <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)', lineHeight: 1.65 }}>
              Age, sex, and diet are optional. The screening still works without them.
              {optionalProfileSummary ? ` Current optional context: ${optionalProfileSummary}.` : ''}
            </div>

            <AnimatePresence>
              {showOptionalContext && (
                <motion.div 
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.3, ease: E }}
                  style={{ overflow: 'hidden' }}
                >
                  <div className="intake-optional-grid" style={{ display: 'grid', gap: '1rem', paddingTop: '0.5rem' }}>
                    <div>
                      <div style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '0.55rem' }}>
                        Age
                      </div>
                      <input
                    type="number"
                    min={1}
                    max={120}
                    placeholder="Optional"
                    value={patientProfile.age ?? ''}
                    onChange={(event) => {
                      const value = event.target.value.trim();
                      updatePatientProfile('age', value ? Number(value) : null);
                    }}
                    style={{
                      width: '100%',
                      padding: '0.9rem 1rem',
                      borderRadius: '0.95rem',
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      color: 'var(--text)',
                      outline: 'none',
                      fontSize: '0.92rem',
                    }}
                  />
                </div>

                <div>
                  <div style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '0.55rem' }}>
                    Sex
                  </div>
                  <div className="intake-choice-row" style={{ display: 'flex', gap: '0.55rem', flexWrap: 'wrap' }}>
                    {SEX_OPTIONS.map((option) => {
                      const active = patientProfile.sex === option.value;
                      return (
                        <button
                          key={option.value}
                          type="button"
                          className="btn btn-glass"
                          onClick={() => updatePatientProfile('sex', option.value)}
                          style={{
                            padding: '0.6rem 0.95rem',
                            fontSize: '0.64rem',
                            borderRadius: '0.85rem',
                            border: active ? '1px solid rgba(0,194,255,0.32)' : '1px solid rgba(255,255,255,0.08)',
                            background: active ? 'rgba(0,194,255,0.08)' : 'rgba(255,255,255,0.03)',
                            color: active ? 'rgba(0,194,255,0.95)' : 'var(--text-muted)',
                          }}
                        >
                          {option.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '0.55rem' }}>
                    Diet type
                  </div>
                  <div className="intake-choice-row" style={{ display: 'flex', gap: '0.55rem', flexWrap: 'wrap' }}>
                    {DIET_OPTIONS.map((option) => {
                      const active = patientProfile.diet_type === option.value;
                      return (
                        <button
                          key={option.value}
                          type="button"
                          className="btn btn-glass"
                          onClick={() => updatePatientProfile('diet_type', option.value)}
                          style={{
                            padding: '0.6rem 0.95rem',
                            fontSize: '0.64rem',
                            borderRadius: '0.85rem',
                            border: active ? '1px solid rgba(0,229,150,0.28)' : '1px solid rgba(255,255,255,0.08)',
                            background: active ? 'rgba(0,229,150,0.08)' : 'rgba(255,255,255,0.03)',
                            color: active ? 'rgba(0,229,150,0.92)' : 'var(--text-muted)',
                          }}
                        >
                          {option.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        <div style={{ padding: '0.95rem 1rem', borderRadius: '0.9rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: '0.58rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '0.45rem' }}>
            Workflow impact
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>
            Symptoms are the main triage input here. Optional profile context is only used if you choose to add it.
          </div>
        </div>
      </motion.div>

      <motion.div
        className="glass"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.08, ease: E }}
        style={{ padding: '1.75rem', display: 'grid', gap: '1rem' }}
      >
        <div>
          <div className="section-eyebrow" style={{ marginBottom: '0.7rem' }}>Symptoms</div>
          <h4 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.45rem' }}>
            Reported symptom checklist
          </h4>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', lineHeight: 1.65 }}>
            Select only what is actually present. This is the main clinical context the triage layer should weigh after the image model runs.
          </p>
        </div>

        <motion.div 
          className="intake-symptom-grid" 
          style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.8rem' }}
          variants={{
            hidden: {},
            show: {
              transition: { staggerChildren: 0.04 }
            }
          }}
          initial="hidden"
          animate="show"
        >
          {(Object.keys(symptomLabels) as Array<keyof SymptomInput>).map((key) => {
            const active = symptoms[key] === true;
            const icon = SYMPTOM_ICONS[key as string] ?? <HeartPulse size={16} />;
            return (
              <motion.button
                key={key}
                type="button"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                variants={{
                  hidden: { opacity: 0, y: 15 },
                  show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
                }}
                onClick={() => toggleSymptom(key)}
                style={{
                  textAlign: 'left',
                  padding: '1rem',
                  borderRadius: '1rem',
                  border: active ? '1px solid rgba(200,0,30,0.3)' : '1px solid rgba(255,255,255,0.08)',
                  background: active ? 'rgba(200,0,30,0.08)' : 'rgba(255,255,255,0.025)',
                  cursor: 'pointer',
                  display: 'grid',
                  gap: '0.65rem',
                  transition: 'border-color 0.22s ease, background 0.22s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
                  <motion.div 
                    initial={false}
                    animate={{ scale: active ? [1, 1.15, 1] : 1 }}
                    transition={{ duration: 0.4 }}
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: '0.85rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: active ? 'rgba(200,0,30,0.16)' : 'rgba(255,255,255,0.05)',
                      color: active ? 'var(--accent-bright)' : 'var(--text-dim)',
                    }}
                  >
                    {icon}
                  </motion.div>
                  <div style={{
                    width: 18,
                    height: 18,
                    borderRadius: '50%',
                    border: active ? '1px solid rgba(200,0,30,0.35)' : '1px solid rgba(255,255,255,0.12)',
                    background: active ? 'rgba(200,0,30,0.22)' : 'transparent',
                    boxShadow: active ? '0 0 14px rgba(200,0,30,0.18)' : 'none',
                  }} />
                </div>
                <div style={{ fontSize: '0.82rem', fontWeight: 600, lineHeight: 1.4 }}>
                  {symptomLabels[key]}
                </div>
                <div style={{ fontSize: '0.58rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: active ? 'var(--accent-bright)' : 'var(--text-dim)' }}>
                  {active ? 'Included in triage' : 'Tap to include'}
                </div>
              </motion.button>
            );
          })}
        </motion.div>

        <div className="intake-actions" style={{ paddingTop: '0.35rem', display: 'flex', gap: '0.75rem', justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <MagneticButton className="btn-glass" style={{ padding: '0.75rem 1.35rem', fontSize: '0.7rem' }} onClick={onBack}>
            Back
          </MagneticButton>
          <MagneticButton className="btn-primary" style={{ padding: '0.75rem 1.5rem', fontSize: '0.7rem' }} onClick={onContinue} disabled={loading}>
            {loading ? 'Analyzing...' : 'Run Clinical Workflow'}
          </MagneticButton>
        </div>
      </motion.div>
    </div>
  );
}
