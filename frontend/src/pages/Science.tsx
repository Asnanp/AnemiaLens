import { motion } from 'framer-motion';
import { BrainCircuit, Microscope, Activity, ShieldCheck } from 'lucide-react';

const FADE_UP = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: 'easeOut' as const } }
};

export default function Science() {
  return (
    <main className="min-h-screen pt-32 pb-20 px-6 sm:px-12 max-w-7xl mx-auto">
      <motion.div initial="hidden" animate="visible" variants={FADE_UP} className="text-center mb-20">
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
          The <span className="text-brand-purple">Science</span> Behind<br/>AnemiaLens
        </h1>
        <p className="text-text-secondary text-lg md:text-xl max-w-3xl mx-auto leading-relaxed">
          Our proprietary machine learning models analyze conjunctival pallor with clinical precision, 
          bridging the gap between accessible technology and hematological science.
        </p>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-8 mb-20">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={FADE_UP} className="glass p-10 rounded-3xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-64 h-64 bg-brand-blue/10 rounded-full blur-3xl -mr-20 -mt-20 transition-transform duration-700 group-hover:scale-150"></div>
          <BrainCircuit className="w-12 h-12 text-brand-blue mb-6" />
          <h3 className="text-2xl font-bold mb-4">Deep Learning Architecture</h3>
          <p className="text-text-secondary leading-relaxed">
            We utilize a specialized Convolutional Neural Network (CNN) trained on thousands of diverse 
            clinical images. The model isolates the palpebral conjunctiva, accounting for varying lighting 
            conditions and skin tones to ensure robust, unbiased hemoglobin estimation.
          </p>
        </motion.div>

        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={FADE_UP} transition={{ delay: 0.2 }} className="glass p-10 rounded-3xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-64 h-64 bg-brand-purple/10 rounded-full blur-3xl -mr-20 -mt-20 transition-transform duration-700 group-hover:scale-150"></div>
          <Activity className="w-12 h-12 text-brand-purple mb-6" />
          <h3 className="text-2xl font-bold mb-4">Colorimetric Analysis</h3>
          <p className="text-text-secondary leading-relaxed">
            By extracting advanced color space features (RGB, HSV, LAB) from the targeted region, 
            our algorithm quantifies erythema (redness) at a pixel level. This quantitative analysis 
            correlates strongly with systemic hemoglobin concentration.
          </p>
        </motion.div>
      </div>

      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={FADE_UP} className="glass p-10 md:p-16 rounded-3xl flex flex-col md:flex-row items-center gap-12">
        <div className="flex-1">
          <h2 className="text-3xl font-bold mb-6">Rigorous Validation</h2>
          <p className="text-text-secondary leading-relaxed mb-6">
            AnemiaLens isn't just an app; it's a peer-reviewed approach to accessible screening. 
            Our models are continuously cross-validated against invasive Complete Blood Count (CBC) tests 
            conducted in partner clinics, ensuring a high degree of sensitivity and specificity.
          </p>
          <ul className="space-y-4">
            {[
              { icon: ShieldCheck, text: 'HIPAA Compliant Data Handling' },
              { icon: Microscope, text: 'Clinical Grade Accuracy Target' },
            ].map((item, i) => (
              <li key={i} className="flex items-center gap-3 text-text-primary">
                <item.icon className="w-5 h-5 text-brand-teal" />
                {item.text}
              </li>
            ))}
          </ul>
        </div>
        <div className="flex-1 w-full relative">
           <div className="aspect-square rounded-3xl bg-surface border border-glass-border overflow-hidden flex items-center justify-center relative">
              <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1576086213369-97a306d36557?q=80&w=1000&auto=format&fit=crop')] bg-cover bg-center opacity-30 mix-blend-luminosity"></div>
              <div className="z-10 text-center">
                 <div className="w-24 h-24 rounded-full border-4 border-brand-teal border-t-transparent animate-spin mx-auto mb-4"></div>
                 <span className="text-brand-teal font-mono tracking-widest text-sm uppercase">PROCESSING DATA</span>
              </div>
           </div>
        </div>
      </motion.div>
    </main>
  );
}