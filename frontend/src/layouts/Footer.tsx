import { HeartPulse, ShieldCheck } from 'lucide-react';

export function Footer() {
  return (
    <footer className="px-6 py-20 bg-brand-dark relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent shadow-[0_0_15px_rgba(255,255,255,0.3)]" />
      
      <div className="max-w-[90rem] mx-auto grid grid-cols-1 md:grid-cols-3 gap-12">
        <div className="space-y-6">
          <div className="flex items-center gap-3 group cursor-default">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-accent to-brand-crimson flex items-center justify-center text-white font-black shadow-[0_0_20px_rgba(230,21,58,0.4)] group-hover:scale-110 transition-transform duration-500 group-hover:shadow-[0_0_30px_rgba(255,59,92,0.6)]">
              AL
            </div>
            <div>
              <div className="text-xl font-black tracking-tighter text-white leading-none">AnemiaLens</div>
              <div className="text-xs font-bold text-text-dim uppercase tracking-widest mt-1">AI Diagnostics</div>
            </div>
          </div>
          <p className="text-sm text-text-secondary leading-relaxed max-w-sm">
            Empowering global healthcare through AI-driven non-invasive anemia screening. 
            Designed for impact, accessibility, and scientific excellence.
          </p>
          <div className="flex items-center gap-4 pt-2">
            <div className="px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/5 flex items-center gap-2 shadow-inner">
              <ShieldCheck className="w-3.5 h-3.5 text-brand-accent drop-shadow-[0_0_8px_rgba(255,59,92,0.8)]" />
              <span className="text-[10px] font-black text-text-dim uppercase tracking-widest">ISO 27001</span>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/5 flex items-center gap-2 shadow-inner">
              <HeartPulse className="w-3.5 h-3.5 text-brand-accent drop-shadow-[0_0_8px_rgba(255,59,92,0.8)]" />
              <span className="text-[10px] font-black text-text-dim uppercase tracking-widest">HIPAA READY</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-8">
          <div className="space-y-6">
            <h4 className="text-xs font-bold text-white uppercase tracking-widest">Company</h4>
            <ul className="space-y-4">
              {['About Us', 'Science', 'Careers', 'Contact'].map(link => (
                <li key={link}>
                  <a href="#" className="text-sm text-text-dim hover:text-white transition-colors">{link}</a>
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-6">
            <h4 className="text-xs font-bold text-white uppercase tracking-widest">Legal</h4>
            <ul className="space-y-4">
              {['Privacy Policy', 'Terms of Service', 'Cookie Policy', 'Disclaimer'].map(link => (
                <li key={link}>
                  <a href="#" className="text-sm text-text-dim hover:text-white transition-colors">{link}</a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="space-y-6">
          <h4 className="text-xs font-bold text-white uppercase tracking-widest">Impact</h4>
          <div className="p-6 rounded-3xl glass-card bg-white/[0.01] hover:bg-white/[0.03] transition-all space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-white font-bold text-xs shadow-[0_0_10px_rgba(255,255,255,0.05)]">
                🎯
              </div>
              <span className="text-[10px] font-black text-white uppercase tracking-widest">UN SDG 3</span>
            </div>
            <p className="text-xs text-text-dim leading-relaxed italic">
              "Good Health & Well-being: Ensuring healthy lives and promoting well-being for all at all ages."
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-[90rem] mx-auto mt-20 pt-8 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-6">
        <p className="text-[10px] text-text-dim uppercase tracking-widest">
          © 2026 AnemiaLens AI. All rights reserved. 
        </p>
        <p className="text-[10px] text-text-dim uppercase tracking-widest text-center md:text-right max-w-lg leading-loose">
          AnemiaLens is a screening tool, not a diagnostic device. Results must be confirmed with clinical blood testing. 
          This application does not replace professional medical advice, diagnosis, or treatment.
        </p>
      </div>
    </footer>
  );
}
