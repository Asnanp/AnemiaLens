import { motion } from 'framer-motion';

export default function ForProviders() {
  return (
    <div className="pt-24 pb-16 min-h-screen">
      <div className="max-w-5xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-16"
        >
          <h1 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight text-[var(--text-primary)]">
            For Healthcare Providers
          </h1>
          <p className="text-lg text-[var(--text-secondary)] max-w-3xl mx-auto">
            Empower your clinical practice with rapid, AI-driven triage tools. Integrate AnemiaLens into your workflow to streamline patient assessment.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-12 mb-20">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="flex flex-col justify-center"
          >
            <h2 className="text-3xl font-bold mb-6">Why Partner With Us?</h2>
            <ul className="space-y-4 text-[var(--text-muted)]">
              <li className="flex items-start">
                <span className="text-[var(--accent-bright)] mr-3">✓</span>
                <span><strong>Reduce Wait Times:</strong> Instantly triage patients before lab results return.</span>
              </li>
              <li className="flex items-start">
                <span className="text-[var(--accent-bright)] mr-3">✓</span>
                <span><strong>Cost Effective:</strong> Lower the barrier to initial screening in resource-limited settings.</span>
              </li>
              <li className="flex items-start">
                <span className="text-[var(--accent-bright)] mr-3">✓</span>
                <span><strong>API Integration:</strong> Connect directly with your existing EHR/EMR systems.</span>
              </li>
            </ul>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="glass p-8 rounded-3xl border border-[var(--glass-border)]"
          >
            <h3 className="text-xl font-bold mb-6 text-center">Request a Demo</h3>
            <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); alert('Demo requested!'); }}>
              <input type="text" className="w-full bg-[var(--glass-hi)] border border-[var(--glass-border)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-bright)]" placeholder="Clinic / Hospital Name" required />
              <input type="email" className="w-full bg-[var(--glass-hi)] border border-[var(--glass-border)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-bright)]" placeholder="Work Email" required />
              <button type="submit" className="w-full py-3 rounded-xl font-semibold text-white shadow-lg transition-transform hover:scale-[1.02] active:scale-95" style={{ background: 'linear-gradient(135deg, var(--accent-bright), var(--accent))' }}>
                Submit Request
              </button>
            </form>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
