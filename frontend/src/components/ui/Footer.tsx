import React from 'react';
import { Link } from 'react-router-dom';
import { Activity, Github, Twitter, Linkedin, ArrowUpRight } from 'lucide-react';
import { GlowButton } from './GlowButton';

export const Footer = () => {
  return (
    <footer className="relative mt-24 border-t border-glass-medium bg-background pt-16 pb-8 overflow-hidden">
      {/* Decorative Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-4xl h-px bg-gradient-to-r from-transparent via-accent-primary to-transparent opacity-50" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-32 bg-accent-primary/10 blur-[100px] pointer-events-none rounded-full" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12 lg:gap-8 mb-16">
          
          {/* Brand Column */}
          <div className="lg:col-span-2">
            <Link to="/" className="flex items-center gap-3 group inline-flex mb-6">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-primary to-brand-teal flex items-center justify-center text-white font-bold text-lg shadow-[0_0_15px_rgba(99,102,241,0.3)]">
                AL
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-xl leading-none tracking-tight text-text-primary">AnemiaLens</span>
              </div>
            </Link>
            <p className="text-text-secondary text-sm leading-relaxed max-w-sm mb-6">
              Next-generation neural diagnostics for non-invasive anemia screening. 
              Powered by advanced computer vision and clinical-grade AI to provide instant, accessible healthcare insights.
            </p>
            <div className="flex gap-4">
              <a href="#" className="w-10 h-10 rounded-full bg-surface border border-glass-medium flex items-center justify-center text-text-muted hover:text-accent-primary hover:border-accent-primary/50 transition-all">
                <Twitter className="w-4 h-4" />
              </a>
              <a href="#" className="w-10 h-10 rounded-full bg-surface border border-glass-medium flex items-center justify-center text-text-muted hover:text-accent-primary hover:border-accent-primary/50 transition-all">
                <Github className="w-4 h-4" />
              </a>
              <a href="#" className="w-10 h-10 rounded-full bg-surface border border-glass-medium flex items-center justify-center text-text-muted hover:text-accent-primary hover:border-accent-primary/50 transition-all">
                <Linkedin className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Links Columns */}
          <div>
            <h4 className="text-text-primary font-semibold mb-6">Platform</h4>
            <ul className="flex flex-col gap-4">
              <li><Link to="/how-it-works" className="text-text-secondary hover:text-accent-primary transition-colors text-sm">How it Works</Link></li>
              <li><Link to="/providers" className="text-text-secondary hover:text-accent-primary transition-colors text-sm">For Providers</Link></li>
              <li><Link to="/clinical" className="text-text-secondary hover:text-accent-primary transition-colors text-sm">Clinical Validation</Link></li>
              <li><Link to="/pricing" className="text-text-secondary hover:text-accent-primary transition-colors text-sm">Pricing</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-text-primary font-semibold mb-6">Company</h4>
            <ul className="flex flex-col gap-4">
              <li><Link to="/about" className="text-text-secondary hover:text-accent-primary transition-colors text-sm">About Us</Link></li>
              <li><Link to="/careers" className="text-text-secondary hover:text-accent-primary transition-colors text-sm">Careers</Link></li>
              <li><Link to="/blog" className="text-text-secondary hover:text-accent-primary transition-colors text-sm">Blog</Link></li>
              <li><Link to="/contact" className="text-text-secondary hover:text-accent-primary transition-colors text-sm">Contact</Link></li>
            </ul>
          </div>

          {/* CTA Column */}
          <div>
            <h4 className="text-text-primary font-semibold mb-6">Get Started</h4>
            <p className="text-text-secondary text-sm mb-4">
              Ready to transform your clinical workflow? Join our early access program.
            </p>
            <GlowButton size="sm" className="w-full">
              Request Access <ArrowUpRight className="w-4 h-4 ml-1" />
            </GlowButton>
          </div>

        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-glass-medium flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-text-muted text-xs">
            © {new Date().getFullYear()} AnemiaLens Technologies, Inc. All rights reserved.
          </p>
          <div className="flex items-center gap-6 text-xs text-text-muted">
            <Link to="/privacy" className="hover:text-text-primary transition-colors">Privacy Policy</Link>
            <Link to="/terms" className="hover:text-text-primary transition-colors">Terms of Service</Link>
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500"></span>
              </span>
              All systems operational
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};
