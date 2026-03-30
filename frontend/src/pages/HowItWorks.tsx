import { motion } from 'framer-motion';

export default function HowItWorks() {
  const steps = [
    { title: "Capture", desc: "Take a clear, well-lit photo of your inner lower eyelid (palpebral conjunctiva) using your smartphone." },
    { title: "Analyze", desc: "Our computer vision model securely analyzes the image, looking for signs of pallor associated with lower hemoglobin levels." },
    { title: "Results", desc: "Receive an instant risk assessment. High-risk results should be followed up with a clinical blood test." }
  ];

  return (
    <div className="pt-24 pb-16 min-h-screen">
      <div className="max-w-5xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-16"
        >
          <h1 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight">
            How It Works
          </h1>
          <p className="text-lg text-[var(--text-secondary)] max-w-2xl mx-auto">
            The science behind non-invasive anemia screening, simplified for everyday use.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8 mb-20">
          {steps.map((step, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.2 }}
              className="glass p-8 rounded-3xl border border-[var(--glass-border)] text-center relative overflow-hidden"
            >
              <div className="text-[var(--accent-bright)] text-6xl font-bold opacity-20 absolute -top-4 -right-4">
                0{i + 1}
              </div>
              <h3 className="text-2xl font-bold mb-4 relative z-10">{step.title}</h3>
              <p className="text-[var(--text-muted)] relative z-10">{step.desc}</p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass p-10 rounded-3xl border border-[var(--glass-border)]"
        >
          <h2 className="text-3xl font-bold mb-6 text-[var(--accent-bright)]">The Science</h2>
          <p className="text-[var(--text-muted)] leading-relaxed mb-4">
            Anemia is characterized by a decrease in total red blood cells or hemoglobin. One of the most reliable visual clinical indicators is conjunctival pallor—the paleness of the inner lining of the lower eyelid.
          </p>
          <p className="text-[var(--text-muted)] leading-relaxed">
            Our proprietary deep learning models are trained on thousands of expertly annotated clinical images. By extracting specific color and structural features from the image you provide, the model can estimate the likelihood of hemoglobin dropping below standard thresholds.
          </p>
        </motion.div>
      </div>
    </div>
  );
}
