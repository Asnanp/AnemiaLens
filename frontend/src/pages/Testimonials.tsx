import { motion } from 'framer-motion';
import { Star, Quote } from 'lucide-react';

const FADE_UP = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: 'easeOut' as const } }
};

const TESTIMONIALS = [
  {
    name: "Dr. Sarah Chen",
    role: "Chief Hematologist, Metro General",
    content: "The accuracy we're seeing with AnemiaLens is unprecedented for a non-invasive tool. It has completely transformed our triage process in the ER.",
    rating: 5,
    avatar: "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=150&auto=format&fit=crop&q=60"
  },
  {
    name: "Michael Rodriguez",
    role: "Patient",
    content: "As someone managing chronic anemia, having the ability to check my levels between doctor visits gives me incredible peace of mind. The UI is so simple to use.",
    rating: 5,
    avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&auto=format&fit=crop&q=60"
  },
  {
    name: "Dr. Emily Taylor",
    role: "Global Health Initiative",
    content: "In rural clinics where CBC machines are unavailable or too expensive to maintain, AnemiaLens is literally saving lives by providing instant, reliable screenings.",
    rating: 5,
    avatar: "https://images.unsplash.com/photo-1614608682850-e0d6ed316d47?w=150&auto=format&fit=crop&q=60"
  },
  {
    name: "James Wilson",
    role: "Tech Reviewer",
    content: "The seamless integration of complex machine learning models into a beautiful, buttery-smooth web interface is a masterclass in modern software engineering.",
    rating: 5,
    avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=60"
  }
];

export default function Testimonials() {
  return (
    <main className="min-h-screen pt-32 pb-20 px-6 sm:px-12 max-w-7xl mx-auto">
      <motion.div initial="hidden" animate="visible" variants={FADE_UP} className="text-center mb-20">
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
          Trusted by <span className="text-brand-purple">Professionals</span>
        </h1>
        <p className="text-text-secondary text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
          See what doctors, patients, and health organizations are saying about our technology.
        </p>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-8">
        {TESTIMONIALS.map((testimonial, i) => (
          <motion.div 
            key={i}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={FADE_UP}
            transition={{ delay: i * 0.1 }}
            className="glass p-8 md:p-10 rounded-3xl relative"
          >
            <Quote className="absolute top-8 right-8 w-12 h-12 text-glass-border-hi opacity-50" />
            <div className="flex gap-1 mb-6">
              {[...Array(testimonial.rating)].map((_, j) => (
                <Star key={j} className="w-5 h-5 fill-brand-teal text-brand-teal" />
              ))}
            </div>
            <p className="text-lg md:text-xl leading-relaxed mb-8 relative z-10">
              "{testimonial.content}"
            </p>
            <div className="flex items-center gap-4">
              <img 
                src={testimonial.avatar} 
                alt={testimonial.name} 
                className="w-14 h-14 rounded-full border-2 border-brand-purple/30 object-cover"
              />
              <div>
                <div className="font-bold">{testimonial.name}</div>
                <div className="text-sm text-text-muted">{testimonial.role}</div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </main>
  );
}