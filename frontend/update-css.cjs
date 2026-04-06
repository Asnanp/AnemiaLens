const fs = require('fs');
const path = require('path');

const cssPath = path.join(__dirname, 'src', 'styles.css');
let css = fs.readFileSync(cssPath, 'utf8');

// Find the :root block - from "/* ── DESIGN TOKENS" to the closing "}"
const tokenStart = css.indexOf('/* ── DESIGN TOKENS');
const rootStart = css.indexOf(':root {', tokenStart);
const rootEnd = css.indexOf('}', rootStart) + 1;

const newTokens = `/* ── DESIGN TOKENS — hyper-premium medical AI ──────────────────────────────── */
:root {
  --void:            #04040A;
  --bg:              #04040A;
  --crimson:         #C8001E;
  --crimson-bright:  #E8294A;
  --crimson-glow:    rgba(200, 0, 30, 0.18);
  --crimson-subtle:  rgba(200, 0, 30, 0.06);
  --pink-glow:       #FF6B8A;
  --pink-glow-alpha: rgba(255, 107, 138, 0.15);
  --teal:            #5EEAD4;
  --teal-glow:       rgba(94, 234, 212, 0.15);
  --teal-subtle:     rgba(94, 234, 212, 0.06);
  --teal-dim:        rgba(94, 234, 212, 0.4);
  --violet:          #8B5CF6;
  --violet-light:    #A78BFA;
  --violet-glow:     rgba(139, 92, 246, 0.15);
  --violet-subtle:   rgba(139, 92, 246, 0.05);
  --accent:          #FFFFFF;
  --accent-bright:   #FFFFFF;
  --accent-glow:     rgba(255, 255, 255, 0.15);
  --accent-glow-sm:  rgba(255, 255, 255, 0.08);
  --iris-border:     rgba(255, 255, 255, 0.06);
  --glass-white:     rgba(255, 255, 255, 0.025);
  --glass-border:    rgba(255, 255, 255, 0.07);
  --glass-highlight: rgba(255, 255, 255, 0.09);
  --glass:           rgba(255, 255, 255, 0.025);
  --glass-md:        rgba(255, 255, 255, 0.045);
  --glass-hi:        rgba(255, 255, 255, 0.07);
  --glass-border-hi: rgba(255, 255, 255, 0.14);
  --glass-shine:     rgba(255, 255, 255, 0.10);
  --text-primary:    #F0F0F5;
  --text:            #E8EAF0;
  --text-secondary:  #94A3B8;
  --text-muted:      #5F6B80;
  --text-dim:        rgba(255, 255, 255, 0.32);
  --serif:           'Sora', system-ui, sans-serif;
  --sans:            'Inter', system-ui, sans-serif;
  --mono:            'DM Mono', 'Fira Mono', monospace;
  --ease:            cubic-bezier(0.22, 1, 0.36, 1);
  --ease-spring:     cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-expo:   cubic-bezier(0.19, 1, 0.22, 1);
}`;

css = css.substring(0, tokenStart) + newTokens + css.substring(rootEnd);

// Now update the cursor section - replace the cursor dot styling
const cursorDotOld = '#cursor-dot {';
const cursorDotIdx = css.indexOf(cursorDotOld);
if (cursorDotIdx !== -1) {
  // Find the end of cursor-ring block  
  const cursorRingEnd = css.indexOf('}', css.indexOf('#cursor-ring {', cursorDotIdx));
  const afterCursorRing = css.indexOf('\n', cursorRingEnd) + 1;
  
  // Find end of button hover cursor rules
  const btnHoverRingEnd = css.indexOf('}', css.indexOf("body:has(a:hover) #cursor-ring", cursorDotIdx));
  const afterBtnHover = css.indexOf('\n', btnHoverRingEnd) + 1;
  
  const newCursor = `#cursor-dot {
  position: fixed; top: 0; left: 0; width: 5px; height: 5px;
  background: var(--teal); border-radius: 50%;
  pointer-events: none; z-index: 9999;
  mix-blend-mode: screen;
  will-change: transform;
  box-shadow: 0 0 12px var(--teal-glow), 0 0 24px rgba(94,234,212,0.08);
  transition: width 0.25s var(--ease), height 0.25s var(--ease), opacity 0.25s, background 0.3s;
}
#cursor-ring {
  position: fixed; top: 0; left: 0; width: 36px; height: 36px;
  border: 1px solid rgba(94,234,212,0.25);
  border-radius: 50%;
  pointer-events: none; z-index: 9998;
  will-change: transform;
  transition: width 0.35s var(--ease-out-expo), height 0.35s var(--ease-out-expo), border-color 0.3s, opacity 0.3s;
}
body:has(button:hover) #cursor-dot,
body:has(a:hover) #cursor-dot { width: 0; height: 0; opacity: 0; }
body:has(button:hover) #cursor-ring,
body:has(a:hover) #cursor-ring { width: 52px; height: 52px; border-color: var(--crimson-bright); border-width: 1.5px; box-shadow: 0 0 20px var(--crimson-glow); }

/* Hide cursor on touch */
@media (hover: none), (pointer: coarse) {
  body { cursor: auto; }
  #cursor-dot, #cursor-ring { display: none !important; }
}`;
  
  // Find the start of cursor comment
  const cursorCommentStart = css.lastIndexOf('/*', cursorDotIdx);
  css = css.substring(0, cursorCommentStart) + '/* ── CUSTOM CURSOR — premium glow ──────────────────────────────────────── */\n' + newCursor + '\n' + css.substring(afterBtnHover);
}

// Update the section eyebrow to use teal color
css = css.replace(/\.section-eyebrow\s*\{[^}]*animation:\s*eyebrow-glitch[^}]*\}/s, (match) => {
  return match
    .replace(/color:\s*var\(--accent-bright\)/, 'color: var(--teal)')
    .replace(/animation:\s*eyebrow-glitch\s*14s\s*infinite/, 'animation: eyebrow-breathe 8s ease-in-out infinite');
});

// Replace glitch keyframes with breathe
css = css.replace(/@keyframes eyebrow-glitch\s*\{[^}]*\{[^}]*\}[^}]*\{[^}]*\}[^}]*\{[^}]*\}[^}]*\}/s, 
`@keyframes eyebrow-breathe {
  0%,100% { opacity: 0.85; }
  50%     { opacity: 1; }
}`);

// Update the glass top-edge shimmer to include teal
css = css.replace(
  /\.glass::before\s*\{[^}]*background:\s*linear-gradient\(90deg,\s*transparent\s*0%,\s*var\(--glass-highlight\)\s*40%,\s*rgba\(255,255,255,0\.10?\)\s*60%,\s*transparent\s*100%\)/s,
  `.glass::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent 0%, rgba(94,234,212,0.12) 30%, var(--glass-highlight) 50%, rgba(200,0,30,0.12) 70%, transparent 100%)`
);

// Add new animation keyframes before the eye scanner section
const eyeScannerIdx = css.indexOf('/* ── EYE SCANNER');
if (eyeScannerIdx !== -1) {
  const newKeyframes = `
/* ── BREATHING & AI ANIMATIONS ─────────────────────────────────────────────── */
@keyframes ai-heartbeat {
  0%, 100% { transform: scale(1); opacity: 0.3; }
  25%      { transform: scale(1.02); opacity: 0.5; }
  50%      { transform: scale(1); opacity: 0.35; }
  75%      { transform: scale(1.015); opacity: 0.45; }
}
@keyframes breathing-ui {
  0%, 100% { opacity: 0.7; transform: scale(1); }
  50%      { opacity: 1; transform: scale(1.008); }
}
@keyframes scan-line-sweep {
  0%   { top: 0%; opacity: 0; }
  5%   { opacity: 0.8; }
  95%  { opacity: 0.8; }
  100% { top: 100%; opacity: 0; }
}
@keyframes liquid-drift {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25%      { transform: translate(20px, -15px) scale(1.04); }
  50%      { transform: translate(-10px, 10px) scale(0.98); }
  75%      { transform: translate(15px, 5px) scale(1.02); }
}
@keyframes status-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(94,234,212,0.4); }
  50%      { box-shadow: 0 0 0 6px rgba(94,234,212,0); }
}
@keyframes teal-glow-pulse {
  0%, 100% { box-shadow: 0 0 20px rgba(94,234,212,0.15), 0 0 40px rgba(94,234,212,0.05); }
  50%      { box-shadow: 0 0 30px rgba(94,234,212,0.25), 0 0 60px rgba(94,234,212,0.10); }
}

/* ── TEAL ACCENT GLASS VARIANT ─────────────────────────────────────────────── */
.glass-teal {
  border-color: rgba(94,234,212,0.2);
  box-shadow:
    inset 0 1px 0 rgba(94,234,212,0.12),
    0 0 30px var(--teal-subtle),
    0 24px 56px rgba(0,0,0,0.4);
}
.glass-teal::before {
  background: linear-gradient(90deg,
    transparent 0%, rgba(94,234,212,0.35) 30%,
    rgba(94,234,212,0.18) 50%, rgba(94,234,212,0.35) 70%, transparent 100%);
}

/* ── TEAL BUTTON VARIANT ───────────────────────────────────────────────────── */
.btn-teal {
  background: linear-gradient(135deg, rgba(94,234,212,0.15) 0%, rgba(94,234,212,0.05) 100%);
  color: var(--teal);
  border: 1px solid rgba(94,234,212,0.25);
  box-shadow: inset 0 1px 0 rgba(94,234,212,0.15), 0 8px 24px rgba(0,0,0,0.3);
}
.btn-teal:hover {
  background: rgba(94,234,212,0.12);
  border-color: rgba(94,234,212,0.4);
  box-shadow: inset 0 1px 0 rgba(94,234,212,0.2), 0 16px 40px rgba(0,0,0,0.4), 0 0 30px var(--teal-subtle);
  transform: translateY(-2px);
}

`;
  css = css.substring(0, eyeScannerIdx) + newKeyframes + css.substring(eyeScannerIdx);
}

// Update .text-gold to use teal
css = css.replace(/\.text-gold\s*\{[^}]*color:[^;]*;/g, '.text-gold { color: var(--teal);');

// Update scroll progress gradient reference
css = css.replace(
  /linear-gradient\(90deg,\s*var\(--crimson\),\s*var\(--accent-bright\),\s*#FF6B8A\)/g,
  'linear-gradient(90deg, var(--crimson), var(--pink-glow), var(--teal))'
);

fs.writeFileSync(cssPath, css, 'utf8');
console.log('CSS updated successfully. New length:', css.length);
