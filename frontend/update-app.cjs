const fs = require('fs');
const path = require('path');

const appPath = path.join(__dirname, 'src', 'App.tsx');
let app = fs.readFileSync(appPath, 'utf8');

// 1. Replace accent-bright with teal in brand title
app = app.replace(
  `color: 'var(--accent-bright)'`,
  `color: 'var(--teal)'`
);

// 2. Replace the old status chip with AIStatusIndicator
app = app.replace(
  /\{backendUp && \(\s*<span className="stat-chip nav-status-chip">\s*<span className="nav-status-dot" \/>\s*Live\s*<\/span>\s*\)\}/s,
  `<AIStatusIndicator backendUp={backendUp} />`
);

fs.writeFileSync(appPath, app, 'utf8');
console.log('App.tsx updated successfully');
