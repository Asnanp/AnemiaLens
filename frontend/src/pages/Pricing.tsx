import { motion } from 'framer-motion';
import { Check, X } from 'lucide-react';

const FADE_UP = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: 'easeOut' as const } }
};

export default function Pricing() {
  return (
    <main className="min-h-screen pt-32 pb-20 px-6 sm:px-12 max-w-7xl mx-auto">
      <motion.div initial="hidden" animate="visible" variants={FADE_UP} className="text-center mb-16">
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
          Simple, <span className="text-brand-teal">Transparent</span> Pricing
        </h1>
        <p className="text-text-secondary text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
          Accessible health screening for everyone. No hidden fees, no subscriptions unless you need them.
        </p>
      </motion.div>

      <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
        {/* Tier 1 */}
        <motion.div initial="hidden" animate="visible" variants={FADE_UP} transition={{ delay: 0.1 }} className="glass p-8 rounded-3xl flex flex-col">
          <h3 className="text-xl font-medium text-text-muted mb-2">Guest Screening</h3>
          <div className="text-4xl font-bold mb-6">Free</div>
          <p className="text-text-secondary mb-8 text-sm h-10">Perfect for a quick, one-time check without creating an account.</p>
          <ul className="space-y-4 mb-8 flex-1">
            <li className="flex items-center gap-3"><Check className="w-5 h-5 text-brand-teal" /> 1 AI Scan per month</li>
            <li className="flex items-center gap-3"><Check className="w-5 h-5 text-brand-teal" /> Instant Results</li>
            <li className="flex items-center gap-3 text-text-muted"><X className="w-5 h-5" /> No History Saved</li>
            <li className="flex items-center gap-3 text-text-muted"><X className="w-5 h-5" /> No PDF Export</li>
          </ul>
          <button className="w-full py-3 rounded-xl bg-surface border border-glass-border hover:bg-surfaceHover transition-colors font-medium">
            Try Now
          </button>
        </motion.div>

        {/* Tier 2 */}
        <motion.div initial="hidden" animate="visible" variants={FADE_UP} transition={{ delay: 0.2 }} className="glass p-8 rounded-3xl flex flex-col relative border-brand-blue/30 scale-105 shadow-[0_0_40px_rgba(59,130,246,0.15)] z-10">
          <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-brand-blue text-white px-4 py-1 rounded-full text-xs font-bold tracking-wider">MOST POPULAR</div>
          <h3 className="text-xl font-medium text-brand-blue mb-2">Personal Account</h3>
          <div className="text-4xl font-bold mb-6">$4.99<span className="text-lg text-text-muted font-normal">/mo</span></div>
          <p className="text-text-secondary mb-8 text-sm h-10">Track your hemoglobin trends over time with unlimited scans.</p>
          <ul className="space-y-4 mb-8 flex-1">
            <li className="flex items-center gap-3"><Check className="w-5 h-5 text-brand-teal" /> Unlimited AI Scans</li>
            <li className="flex items-center gap-3"><Check className="w-5 h-5 text-brand-teal" /> Cloud History Sync</li>
            <li className="flex items-center gap-3"><Check className="w-5 h-5 text-brand-teal" /> PDF Report Export</li>
            <li className="flex items-center gap-3"><Check className="w-5 h-5 text-brand-teal" /> Health Insights Dashboard</li>
          </ul>
          <button className="w-full py-3 rounded-xl bg-brand-blue hover:bg-blue-600 text-white transition-colors font-medium shadow-[0_0_20px_rgba(59,130,246,0.4)]">
            Get Started
          </button>
        </motion.div>

        {/* Tier 3 */}
        <motion.div initial="hidden" animate="visible" variants={FADE_UP} transition={{ delay: 0.3 }} className="glass p-8 rounded-3xl flex flex-col">
          <h3 className="text-xl font-medium text-brand-purple mb-2">Clinical / API</h3>
          <div className="text-4xl font-bold mb-6">Custom</div>
          <p className="text-text-secondary mb-8 text-sm h-10">For healthcare providers and developers integrating our model.</p>
          <ul className="space-y-4 mb-8 flex-1">
            <li className="flex items-center gap-3"><Check className="w-5 h-5 text-brand-purple" /> REST API Access</li>
            <li className="flex items-center gap-3"><Check className="w-5 h-5 text-brand-purple" /> Bulk Batch Processing</li>
            <li className="flex items-center gap-3"><Check className="w-5 h-5 text-brand-purple" /> Dedicated Support</li>
            <li className="flex items-center gap-3"><Check className="w-5 h-5 text-brand-purple" /> White-label Options</li>
          </ul>
          <button className="w-full py-3 rounded-xl bg-surface border border-glass-border hover:border-brand-purple/50 transition-colors font-medium">
            Contact Sales
          </button>
        </motion.div>
      </div>
    </main>
  );
}