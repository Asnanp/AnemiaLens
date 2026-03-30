import { motion } from 'framer-motion';

const FADE_UP = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: 'easeOut' as const } }
};

const TEAM = [
  {
    name: "Dr. Elena Rostova",
    role: "Chief Medical Officer",
    image: "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=400&h=400&auto=format&fit=crop&q=60"
  },
  {
    name: "Marcus Chen",
    role: "Head of AI Research",
    image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&auto=format&fit=crop&q=60"
  },
  {
    name: "Sarah Jenkins",
    role: "Lead Product Designer",
    image: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=400&auto=format&fit=crop&q=60"
  }
];

export default function AboutUs() {
  return (
    <main className="min-h-screen pt-32 pb-20 px-6 sm:px-12 max-w-7xl mx-auto">
      <motion.div initial="hidden" animate="visible" variants={FADE_UP} className="text-center mb-24">
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8">
          Democratizing <span className="text-brand-blue">Diagnostics</span>
        </h1>
        <p className="text-text-secondary text-lg md:text-xl max-w-3xl mx-auto leading-relaxed">
          At AnemiaLens, we believe that access to critical health insights should be as simple as taking a photo. 
          We are merging cutting-edge artificial intelligence with clinical expertise to democratize anemia screening globally.
        </p>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-8 mb-24">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={FADE_UP} className="glass p-10 md:p-12 rounded-3xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-64 h-64 bg-red-500/10 rounded-full blur-3xl -mr-20 -mt-20 transition-transform duration-700 group-hover:scale-150"></div>
          <h2 className="text-3xl font-bold mb-6 text-white relative z-10">The Crisis</h2>
          <p className="text-text-secondary leading-relaxed text-lg relative z-10">
            Anemia affects over 1.6 billion people worldwide, yet traditional diagnostic methods require invasive blood draws, 
            clinical visits, and slow lab processing times. In many underserved regions, this creates an insurmountable barrier to care, leaving millions undiagnosed.
          </p>
        </motion.div>

        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={FADE_UP} transition={{ delay: 0.2 }} className="glass p-10 md:p-12 rounded-3xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-64 h-64 bg-brand-teal/10 rounded-full blur-3xl -mr-20 -mt-20 transition-transform duration-700 group-hover:scale-150"></div>
          <h2 className="text-3xl font-bold mb-6 text-white relative z-10">The Solution</h2>
          <p className="text-text-secondary leading-relaxed text-lg relative z-10">
            By analyzing the pallor of the conjunctiva (the inner eyelid) using advanced computer vision models, 
            AnemiaLens provides an instant, non-invasive risk assessment. Our platform is designed for both personal 
            empowerment and clinical triage at scale.
          </p>
        </motion.div>
      </div>

      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={FADE_UP} className="text-center">
        <h2 className="text-4xl font-bold mb-4">Meet the Team</h2>
        <p className="text-text-secondary mb-16 max-w-2xl mx-auto">
          A multidisciplinary group of hematologists, machine learning engineers, and designers committed to global health equity.
        </p>
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {TEAM.map((member, i) => (
            <motion.div 
              key={i} 
              whileHover={{ y: -10 }}
              className="glass p-6 rounded-3xl border border-glass-border text-center group transition-all duration-300 hover:border-brand-blue/30 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)]"
            >
              <div className="w-32 h-32 mx-auto rounded-full overflow-hidden mb-6 border-4 border-surface shadow-xl">
                <img 
                  src={member.image} 
                  alt={member.name} 
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                />
              </div>
              <h3 className="text-xl font-bold text-white mb-1">{member.name}</h3>
              <p className="text-sm font-medium text-brand-blue uppercase tracking-wider">{member.role}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </main>
  );
}