import { motion } from 'framer-motion';

export default function FAQ() {
  const faqs = [
    { q: "How accurate is the AnemiaLens screening?", a: "Our AI model is trained on thousands of clinical images and achieves high sensitivity in detecting palpebral conjunctiva pallor, a strong indicator of anemia. However, it is a screening tool, not a diagnostic one. Always consult a healthcare professional for a confirmed diagnosis." },
    { q: "Is my medical data secure?", a: "Absolutely. We employ end-to-end encryption. If you use the app as a guest, your images are processed in-memory and immediately discarded. Registered users have their data securely stored in HIPAA-compliant databases." },
    { q: "Can I use this on children?", a: "The current model is primarily calibrated for adult conjunctiva. While it can process pediatric images, the confidence intervals may vary. We recommend clinical supervision for pediatric screening." },
    { q: "How do I get the best results?", a: "Ensure you are in a well-lit room, preferably with natural daylight. Gently pull down your lower eyelid to expose the inner tissue, and ensure the camera focuses sharply on the eye." }
  ];

  return (
    <div className="pt-24 pb-16 min-h-screen">
      <div className="max-w-4xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-16"
        >
          <h1 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight">
            Frequently Asked Questions
          </h1>
          <p className="text-lg text-[var(--text-secondary)]">
            Everything you need to know about the AnemiaLens platform.
          </p>
        </motion.div>

        <div className="space-y-6">
          {faqs.map((faq, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="glass p-6 md:p-8 rounded-2xl border border-[var(--glass-border)] hover:border-[var(--glass-highlight)] transition-colors"
            >
              <h3 className="text-xl font-semibold mb-3 text-[var(--text-primary)]">{faq.q}</h3>
              <p className="text-[var(--text-muted)] leading-relaxed">{faq.a}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
