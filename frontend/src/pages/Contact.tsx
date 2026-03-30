import { motion } from 'framer-motion';
import { Mail, MapPin, Phone, MessageSquare } from 'lucide-react';

const FADE_UP = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: 'easeOut' as const } }
};

export default function Contact() {
  return (
    <main className="min-h-screen pt-32 pb-20 px-6 sm:px-12 max-w-7xl mx-auto">
      <motion.div initial="hidden" animate="visible" variants={FADE_UP} className="text-center mb-16">
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
          Get in <span className="text-brand-purple">Touch</span>
        </h1>
        <p className="text-text-secondary text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
          Whether you're a patient with a question or a healthcare provider looking to partner, our team is ready to assist you.
        </p>
      </motion.div>

      <div className="grid lg:grid-cols-5 gap-8">
        
        {/* Contact Info Sidebar */}
        <motion.div initial="hidden" animate="visible" variants={FADE_UP} transition={{ delay: 0.1 }} className="lg:col-span-2 flex flex-col gap-6">
          <div className="glass p-8 rounded-3xl border border-glass-border flex-1 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-64 h-64 bg-brand-purple/10 rounded-full blur-3xl -mr-20 -mt-20 transition-transform duration-700 group-hover:scale-150"></div>
            <h3 className="text-2xl font-bold mb-8 relative z-10">Contact Information</h3>
            
            <div className="space-y-8 relative z-10">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-surface border border-glass-border flex items-center justify-center shrink-0">
                  <Mail className="w-5 h-5 text-brand-teal" />
                </div>
                <div>
                  <h4 className="font-medium text-white mb-1">Email Us</h4>
                  <p className="text-text-secondary text-sm">support@anemialens.health</p>
                  <p className="text-text-secondary text-sm">partnerships@anemialens.health</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-surface border border-glass-border flex items-center justify-center shrink-0">
                  <Phone className="w-5 h-5 text-brand-blue" />
                </div>
                <div>
                  <h4 className="font-medium text-white mb-1">Call Us</h4>
                  <p className="text-text-secondary text-sm">+1 (800) 555-0199</p>
                  <p className="text-text-secondary text-sm">Mon-Fri, 9am - 6pm EST</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-surface border border-glass-border flex items-center justify-center shrink-0">
                  <MapPin className="w-5 h-5 text-brand-purple" />
                </div>
                <div>
                  <h4 className="font-medium text-white mb-1">Headquarters</h4>
                  <p className="text-text-secondary text-sm">100 Innovation Drive</p>
                  <p className="text-text-secondary text-sm">San Francisco, CA 94105</p>
                </div>
              </div>
            </div>
          </div>
          
          <div className="glass p-8 rounded-3xl border border-glass-border">
            <h4 className="font-bold mb-4 flex items-center gap-2"><MessageSquare className="w-5 h-5 text-brand-blue" /> Live Chat</h4>
            <p className="text-sm text-text-secondary mb-4">Need immediate assistance? Our support team is online.</p>
            <button className="w-full py-3 rounded-xl bg-surface border border-glass-border hover:bg-surfaceHover hover:border-brand-blue/30 transition-all font-medium">
              Start Chat
            </button>
          </div>
        </motion.div>

        {/* Contact Form */}
        <motion.form 
          initial="hidden" 
          animate="visible" 
          variants={FADE_UP} 
          transition={{ delay: 0.2 }} 
          className="lg:col-span-3 glass p-8 md:p-12 rounded-3xl border border-glass-border shadow-[0_0_40px_rgba(0,0,0,0.5)]"
          onSubmit={(e) => { e.preventDefault(); alert('Message sent successfully!'); }}
        >
          <h3 className="text-3xl font-bold mb-8">Send us a message</h3>
          
          <div className="grid md:grid-cols-2 gap-6 mb-6">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">First Name</label>
              <input type="text" className="w-full bg-surface border border-glass-border rounded-xl px-5 py-4 text-white focus:outline-none focus:border-brand-purple/50 focus:ring-1 focus:ring-brand-purple/50 transition-all" placeholder="Jane" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">Last Name</label>
              <input type="text" className="w-full bg-surface border border-glass-border rounded-xl px-5 py-4 text-white focus:outline-none focus:border-brand-purple/50 focus:ring-1 focus:ring-brand-purple/50 transition-all" placeholder="Doe" required />
            </div>
          </div>
          
          <div className="mb-6">
            <label className="block text-sm font-medium text-text-secondary mb-2">Email Address</label>
            <input type="email" className="w-full bg-surface border border-glass-border rounded-xl px-5 py-4 text-white focus:outline-none focus:border-brand-purple/50 focus:ring-1 focus:ring-brand-purple/50 transition-all" placeholder="jane@example.com" required />
          </div>
          
          <div className="mb-6">
            <label className="block text-sm font-medium text-text-secondary mb-2">Subject</label>
            <select className="w-full bg-surface border border-glass-border rounded-xl px-5 py-4 text-white focus:outline-none focus:border-brand-purple/50 focus:ring-1 focus:ring-brand-purple/50 transition-all appearance-none" required>
              <option value="" disabled selected>Select a topic</option>
              <option value="support">General Support</option>
              <option value="partnership">Clinical Partnership</option>
              <option value="press">Press & Media</option>
              <option value="other">Other</option>
            </select>
          </div>
          
          <div className="mb-8">
            <label className="block text-sm font-medium text-text-secondary mb-2">Message</label>
            <textarea rows={5} className="w-full bg-surface border border-glass-border rounded-xl px-5 py-4 text-white focus:outline-none focus:border-brand-purple/50 focus:ring-1 focus:ring-brand-purple/50 transition-all resize-none" placeholder="How can we help you today?" required></textarea>
          </div>
          
          <button type="submit" className="w-full py-4 rounded-xl font-bold text-white transition-all bg-brand-purple hover:bg-purple-600 hover:shadow-[0_0_20px_rgba(139,92,246,0.4)]">
            Send Message
          </button>
        </motion.form>
      </div>
    </main>
  );
}