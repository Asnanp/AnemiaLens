import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, ChevronRight, Activity } from 'lucide-react';
import { GlowButton } from './GlowButton';
import { useAuth } from '../../hooks/useAuth';

const NAV_LINKS = [
  { label: 'How It Works', path: '/how-it-works' },
  { label: 'Providers', path: '/providers' },
  { label: 'About Us', path: '/about' },
  { label: 'FAQ', path: '/faq' },
];

export const Navbar = ({ backendUp = true }: { backendUp?: boolean }) => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  const openAuth = (mode: string) => {
    window.location.href = `/auth?mode=${mode}`;
  };

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  return (
    <>
      <motion.header
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled ? 'py-3' : 'py-5'
        }`}
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div
            className={`relative flex items-center justify-between rounded-full border transition-all duration-500 ${
              scrolled
                ? 'bg-surface/70 backdrop-blur-glass border-glass-medium shadow-lg'
                : 'bg-transparent border-transparent'
            } px-4 py-2 sm:px-6 sm:py-3`}
          >
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group relative z-10">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-primary to-brand-teal flex items-center justify-center text-white font-bold text-lg shadow-[0_0_15px_rgba(99,102,241,0.5)] group-hover:shadow-[0_0_25px_rgba(99,102,241,0.7)] transition-all">
                AL
              </div>
              <div className="hidden sm:flex flex-col">
                <span className="font-bold text-lg leading-none tracking-tight text-text-primary">AnemiaLens</span>
                <span className="text-[0.65rem] uppercase tracking-wider text-text-muted mt-0.5">Neural Diagnostics</span>
              </div>
            </Link>

            {/* Desktop Nav */}
            <nav className="hidden md:flex items-center gap-8 relative z-10">
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  className="text-sm font-medium text-text-secondary hover:text-text-primary transition-colors relative group"
                >
                  {link.label}
                  {location.pathname === link.path && (
                    <motion.div
                      layoutId="nav-indicator"
                      className="absolute -bottom-1 left-0 right-0 h-0.5 bg-accent-primary rounded-full"
                    />
                  )}
                </Link>
              ))}
            </nav>

            {/* Actions */}
            <div className="flex items-center gap-4 relative z-10">
              {backendUp && (
                <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-full bg-glass-light border border-glass-medium text-xs font-medium text-text-secondary">
                  <div className="w-2 h-2 rounded-full bg-teal-400 shadow-[0_0_8px_rgba(45,212,191,0.8)] animate-pulse" />
                  Systems Nominal
                </div>
              )}

              <div className="hidden sm:flex items-center gap-3">
                {!isAuthenticated ? (
                  <>
                    <button
                      onClick={() => openAuth('login')}
                      className="text-sm font-medium text-text-secondary hover:text-text-primary transition-colors px-3 py-2"
                    >
                      Sign In
                    </button>
                    <GlowButton size="sm" onClick={() => openAuth('register')}>
                      Get Started
                    </GlowButton>
                  </>
                ) : (
                  <GlowButton size="sm" variant="secondary" onClick={() => {
                    if (user?.role === 'admin') window.location.href = '/admin';
                    else window.location.href = '/dashboard';
                  }}>
                    Dashboard <ChevronRight className="w-4 h-4 ml-1" />
                  </GlowButton>
                )}
              </div>

              {/* Mobile Menu Toggle */}
              <button
                className="md:hidden p-2 text-text-secondary hover:text-text-primary"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
        </div>
      </motion.header>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed inset-x-0 top-[4.5rem] p-4 z-40 md:hidden"
          >
            <div className="bg-surface/95 backdrop-blur-xl border border-glass-medium rounded-2xl p-4 shadow-2xl flex flex-col gap-4">
              <nav className="flex flex-col gap-2">
                {NAV_LINKS.map((link) => (
                  <Link
                    key={link.path}
                    to={link.path}
                    className="p-3 text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-glass-light rounded-xl transition-colors"
                  >
                    {link.label}
                  </Link>
                ))}
              </nav>
              
              <div className="h-px bg-glass-medium w-full" />
              
              <div className="flex flex-col gap-3">
                {!isAuthenticated ? (
                  <>
                    <button
                      onClick={() => openAuth('login')}
                      className="w-full py-3 text-sm font-medium text-text-primary bg-glass-light border border-glass-medium rounded-xl"
                    >
                      Sign In
                    </button>
                    <GlowButton className="w-full" onClick={() => openAuth('register')}>
                      Get Started
                    </GlowButton>
                  </>
                ) : (
                  <GlowButton className="w-full" variant="secondary" onClick={() => {
                    if (user?.role === 'admin') window.location.href = '/admin';
                    else window.location.href = '/dashboard';
                  }}>
                    Go to Dashboard
                  </GlowButton>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};
