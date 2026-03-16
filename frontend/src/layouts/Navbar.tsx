import { ShieldCheck } from 'lucide-react';
import { Button } from '../components/ui/Button';

export function Navbar({ backendUp }: { backendUp: boolean }) {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 px-6 py-4">
      <div className="max-w-[90rem] mx-auto glass-card !rounded-full px-6 py-3 flex items-center justify-between border-white/5 bg-white/[0.01] backdrop-blur-2xl shadow-[0_10px_40px_rgba(0,0,0,0.5)]">
        <div className="flex items-center gap-3 group cursor-pointer">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-accent to-brand-crimson flex items-center justify-center text-white font-black shadow-[0_0_20px_rgba(230,21,58,0.4)] group-hover:shadow-[0_0_30px_rgba(255,59,92,0.6)] group-hover:scale-105 transition-all duration-300">
            AL
          </div>
          <div>
            <div className="text-sm font-black tracking-tighter text-white leading-none group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-white group-hover:to-brand-accent transition-all duration-300">AnemiaLens</div>
            <div className="text-[10px] font-bold text-text-dim uppercase tracking-widest mt-1">AI Diagnostics</div>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-10">
          <a href="#" className="text-xs font-bold text-text-dim uppercase tracking-widest hover:text-white hover:drop-shadow-[0_0_8px_rgba(255,255,255,0.5)] transition-all duration-300">Screening</a>
          <a href="#" className="text-xs font-bold text-text-dim uppercase tracking-widest hover:text-white hover:drop-shadow-[0_0_8px_rgba(255,255,255,0.5)] transition-all duration-300">History</a>
          <a href="#" className="text-xs font-bold text-text-dim uppercase tracking-widest hover:text-white hover:drop-shadow-[0_0_8px_rgba(255,255,255,0.5)] transition-all duration-300">Science</a>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/10 shadow-[inset_0_0_10px_rgba(255,255,255,0.02)] backdrop-blur-md">
            <div className={`w-2 h-2 rounded-full ${backendUp ? 'bg-green-500 shadow-[0_0_12px_rgba(34,197,94,0.8)]' : 'bg-red-500 shadow-[0_0_12px_rgba(239,68,68,0.8)]'} animate-pulse`} />
            <span className="text-[10px] font-black text-white uppercase tracking-[0.2em] opacity-90">
              {backendUp ? 'SYSTEM LIVE' : 'SYSTEM OFFLINE'}
            </span>
          </div>
          <button className="btn-premium btn-premium-secondary !px-6 !py-3 hidden sm:flex">
            Get Started
          </button>
        </div>
      </div>
    </nav>
  );
}
