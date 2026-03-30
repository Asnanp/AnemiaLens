import { motion } from 'framer-motion';
import { ArrowRight, Clock } from 'lucide-react';

const FADE_UP = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: 'easeOut' as const } }
};

const ARTICLES = [
  {
    title: 'The Silent Epidemic: Understanding Iron Deficiency',
    category: 'Health',
    readTime: '5 min read',
    image: 'https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=800&auto=format&fit=crop&q=60',
    date: 'Oct 12, 2024'
  },
  {
    title: 'How Convolutional Neural Networks Detect Pallor',
    category: 'Technology',
    readTime: '8 min read',
    image: 'https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=800&auto=format&fit=crop&q=60',
    date: 'Sep 28, 2024'
  },
  {
    title: 'AnemiaLens Reaches 10,000 Clinical Validations',
    category: 'Company News',
    readTime: '3 min read',
    image: 'https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=800&auto=format&fit=crop&q=60',
    date: 'Sep 15, 2024'
  },
  {
    title: 'Maternal Health and the Importance of Early Screening',
    category: 'Research',
    readTime: '6 min read',
    image: 'https://images.unsplash.com/photo-1531983412531-1f49a365ffed?w=800&auto=format&fit=crop&q=60',
    date: 'Aug 30, 2024'
  }
];

export default function Blog() {
  return (
    <main className="min-h-screen pt-32 pb-20 px-6 sm:px-12 max-w-7xl mx-auto">
      <motion.div initial="hidden" animate="visible" variants={FADE_UP} className="mb-16">
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
          Latest <span className="text-brand-blue">Insights</span>
        </h1>
        <p className="text-text-secondary text-lg md:text-xl max-w-2xl leading-relaxed">
          Read about the intersection of AI, global health, and the future of accessible diagnostics.
        </p>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-8">
        {ARTICLES.map((article, i) => (
          <motion.div 
            key={i} 
            initial="hidden" 
            whileInView="visible" 
            viewport={{ once: true }} 
            variants={FADE_UP} 
            transition={{ delay: i * 0.1 }}
            className="group cursor-pointer"
          >
            <div className="relative overflow-hidden rounded-3xl aspect-[16/9] mb-6 border border-glass-border">
              <div className="absolute inset-0 bg-surface/20 z-10 group-hover:bg-transparent transition-colors duration-500"></div>
              <img 
                src={article.image} 
                alt={article.title} 
                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
              />
              <div className="absolute top-4 left-4 z-20 bg-black/50 backdrop-blur-md px-3 py-1 rounded-full text-xs font-medium text-brand-teal border border-glass-border">
                {article.category}
              </div>
            </div>
            <div className="flex items-center gap-4 text-text-muted text-sm mb-3">
              <span>{article.date}</span>
              <span className="w-1 h-1 rounded-full bg-text-muted"></span>
              <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {article.readTime}</span>
            </div>
            <h2 className="text-2xl font-bold mb-3 group-hover:text-brand-blue transition-colors">
              {article.title}
            </h2>
            <div className="flex items-center gap-2 text-brand-blue font-medium group-hover:translate-x-2 transition-transform">
              Read Article <ArrowRight className="w-4 h-4" />
            </div>
          </motion.div>
        ))}
      </div>
    </main>
  );
}