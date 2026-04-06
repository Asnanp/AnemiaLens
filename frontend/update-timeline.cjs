const fs = require('fs');
const path = require('path');

const file = path.join(__dirname, 'src/App.tsx');
let content = fs.readFileSync(file, 'utf8');

const target = `<div className="screening-progress" style={{ marginBottom: 'clamp(2rem, 5vw, 4rem)' }}>
          {STEPS_META.map((s, i) => (
            <div key={s.label} style={{ display: 'contents' }}>
              <div
                className={\`screening-step-node \${step === i ? 'active' : ''} \${step > i ? 'done' : ''}\`}
                onClick={() => canStep(i) && setStep(i)}
                style={{ opacity: canStep(i) ? 1 : 0.45, cursor: canStep(i) ? 'pointer' : 'default' }}>
                <div className={\`screening-step-circle \${step === i ? 'active' : ''} \${step > i ? 'done' : ''}\`}>
                  {step > i
                    ? <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
                    : <span style={{ fontFamily: 'var(--mono)', fontSize: '0.65rem' }}>{String(i + 1).padStart(2, '0')}</span>}
                </div>
                <span className="screening-step-label">{s.label}</span>
              </div>
              {i < STEPS_META.length - 1 && <div className={\`screening-step-line \${step > i ? 'done' : ''}\`} />}
            </div>
          ))}
        </div>`;

const replacement = `<div className="screening-progress" style={{ marginBottom: 'clamp(2.5rem, 6vw, 4.5rem)' }}>
          {STEPS_META.map((s, i) => {
            const isActive = step === i;
            const isDone = step > i;
            const canClick = canStep(i);
            
            return (
              <div key={s.label} style={{ display: 'contents' }}>
                <motion.div
                  className={\`screening-step-node \${isActive ? 'active' : ''} \${isDone ? 'done' : ''}\`}
                  onClick={() => canClick && setStep(i)}
                  whileHover={canClick && !isActive ? { y: -2 } : {}}
                  style={{ opacity: canClick ? 1 : 0.45, cursor: canClick ? 'pointer' : 'default', position: 'relative' }}
                >
                  {isActive && (
                    <motion.div
                      layoutId="activeStepGlow"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1, scale: [1, 1.2, 1] }}
                      transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                      style={{
                        position: 'absolute', inset: -10, borderRadius: '50%',
                        background: 'radial-gradient(circle, var(--teal) 0%, transparent 60%)',
                        filter: 'blur(8px)', zIndex: -1, opacity: 0.4
                      }}
                    />
                  )}
                  
                  <motion.div 
                    layout
                    className={\`screening-step-circle \${isActive ? 'active' : ''} \${isDone ? 'done' : ''}\`}
                    animate={{ 
                      scale: isActive ? 1.15 : 1,
                      backgroundColor: isActive ? 'var(--void)' : isDone ? 'var(--teal)' : 'transparent',
                      borderColor: isActive ? 'var(--teal)' : isDone ? 'var(--teal)' : 'rgba(255,255,255,0.1)'
                    }}
                    transition={{ duration: 0.3 }}
                  >
                    {isDone
                      ? <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--void)" strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
                      : <span style={{ fontFamily: 'var(--mono)', fontSize: '0.65rem', color: isActive ? 'var(--teal)' : 'var(--text-muted)' }}>{String(i + 1).padStart(2, '0')}</span>}
                  </motion.div>
                  <span className="screening-step-label" style={{ color: isActive ? '#fff' : 'var(--text-muted)' }}>{s.label}</span>
                </motion.div>
                
                {i < STEPS_META.length - 1 && (
                  <div className="screening-step-line" style={{ background: 'rgba(255,255,255,0.06)', position: 'relative', overflow: 'hidden' }}>
                    <motion.div 
                      style={{ position: 'absolute', top: 0, left: 0, bottom: 0, background: 'var(--teal)' }}
                      initial={{ width: 0 }}
                      animate={{ width: isDone ? '100%' : '0%' }}
                      transition={{ duration: 0.5, ease: E }}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>`;

// Using regex to match with any newline sequence
const regex = new RegExp(target.replace(/[.*+?^$\{key\}()|[\\]\\\\]/g, '\\\\$&').replace(/\\n/g, '\\r?\\n\\s*'), 's');
if (regex.test(content)) {
  content = content.replace(regex, replacement);
  fs.writeFileSync(file, content, 'utf8');
  console.log('App.tsx timeline updated');
} else {
  console.error('Target not found in App.tsx');
}
