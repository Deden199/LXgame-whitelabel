import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { 
  ArrowRight, 
  Layers, 
  Palette, 
  BarChart3, 
  Smartphone,
  Settings,
  Brush,
  Rocket,
  Mail,
  ChevronRight,
  Monitor,
  Shield,
  Zap,
  Globe,
  CreditCard,
  Lock,
  Users,
  RefreshCw,
  CheckCircle,
  Server,
  Database,
  Activity,
  Building2,
  Gamepad2,
  Wallet,
  LayoutDashboard,
  FileText,
  Headphones
} from 'lucide-react';

export default function LandingPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <Zap className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="text-xl font-bold">LooxGame</span>
            </div>
            <div className="hidden md:flex items-center gap-6 text-sm">
              <a href="#features" className="text-muted-foreground hover:text-foreground transition-colors">Features</a>
              <a href="#onboarding" className="text-muted-foreground hover:text-foreground transition-colors">Onboarding</a>
              <a href="#security" className="text-muted-foreground hover:text-foreground transition-colors">Security</a>
              <a href="/integration/" className="text-muted-foreground hover:text-foreground transition-colors">API Docs</a>
            </div>
            <div className="flex items-center gap-3">
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => navigate('/login')}
              >
                Operator Login
              </Button>
              <Button 
                size="sm"
                onClick={() => document.getElementById('contact').scrollIntoView({ behavior: 'smooth' })}
              >
                Request Demo
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section - Enterprise Grade */}
      <section className="pt-32 pb-24 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background to-background" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/5 rounded-full blur-3xl" />
        
        <div className="max-w-7xl mx-auto text-center relative">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-8 border border-primary/20">
            <Shield className="w-4 h-4" />
            Enterprise-Ready White-Label iGaming Platform
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-6 leading-tight">
            Launch Your Gaming
            <br />
            <span className="text-primary">Empire in Days</span>
          </h1>
          <p className="text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto mb-10 leading-relaxed">
            Multi-tenant infrastructure with hardened wallet, idempotent payments, and complete operator control. 
            Built for scale, security, and seamless white-label deployment.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Button 
              size="lg" 
              className="h-14 px-10 text-base font-semibold"
              onClick={() => document.getElementById('contact').scrollIntoView({ behavior: 'smooth' })}
            >
              Request Demo
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
            <Button 
              variant="outline" 
              size="lg"
              className="h-14 px-10 text-base font-semibold"
              onClick={() => navigate('/login')}
            >
              Operator Login
            </Button>
          </div>
          
          {/* Trust Indicators */}
          <div className="flex flex-wrap justify-center items-center gap-8 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span>Idempotent Transactions</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span>Multi-Currency (IDR/USD/USDT)</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span>Agregator Compatible</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span>24/7 Uptime</span>
            </div>
          </div>
        </div>
      </section>

      {/* Operator Onboarding Steps - NEW SECTION */}
      <section id="onboarding" className="py-24 px-4 sm:px-6 lg:px-8 bg-card/30 border-y border-border/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 text-blue-500 text-sm font-medium mb-4">
              <Rocket className="w-4 h-4" />
              Quick Start
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">Operator Onboarding</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              From zero to live platform in four simple steps
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                step: '01',
                icon: Building2,
                title: 'Create Tenant',
                description: 'Set up your operator account with unique branding identity and configuration.',
                color: 'from-blue-500 to-blue-600'
              },
              {
                step: '02',
                icon: Globe,
                title: 'Set Domain & Branding',
                description: 'Configure custom domain, logo, colors, and SEO settings for your platform.',
                color: 'from-purple-500 to-purple-600'
              },
              {
                step: '03',
                icon: Gamepad2,
                title: 'Enable Games & Payments',
                description: 'Select games from catalog, configure bet limits, and set up payment channels.',
                color: 'from-amber-500 to-amber-600'
              },
              {
                step: '04',
                icon: Rocket,
                title: 'Launch Operator',
                description: 'Go live instantly. Players can start playing within minutes of launch.',
                color: 'from-green-500 to-green-600'
              }
            ].map((item, idx) => (
              <div key={idx} className="relative group">
                <div className="bg-card rounded-2xl border border-border/50 p-6 h-full hover:border-primary/30 transition-all duration-300 hover:shadow-lg hover:shadow-primary/5">
                  <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${item.color} flex items-center justify-center mb-5 group-hover:scale-110 transition-transform`}>
                    <item.icon className="w-7 h-7 text-white" />
                  </div>
                  <div className="text-5xl font-bold text-primary/10 mb-3">{item.step}</div>
                  <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{item.description}</p>
                </div>
                {idx < 3 && (
                  <ChevronRight className="hidden lg:block absolute top-1/2 -right-3 w-6 h-6 text-border" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Core Features Grid - NEW SECTION */}
      <section id="features" className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 text-green-500 text-sm font-medium mb-4">
              <Layers className="w-4 h-4" />
              Platform Features
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">Core Features</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Everything you need to run a professional gaming operation
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: Wallet,
                title: 'Multi-Currency Wallet',
                description: 'Support IDR, USD, USDT with automatic conversion. Atomic transactions with complete audit trail.',
                color: 'text-blue-500',
                bg: 'bg-blue-500/10'
              },
              {
                icon: LayoutDashboard,
                title: 'Operator Control Center',
                description: 'Real-time KPIs, player management, withdrawal approval, game configuration, and risk monitoring.',
                color: 'text-purple-500',
                bg: 'bg-purple-500/10'
              },
              {
                icon: CreditCard,
                title: 'Payments & Webhooks',
                description: 'Provider-agnostic payment integration with idempotent webhook handling and strict rollback.',
                color: 'text-green-500',
                bg: 'bg-green-500/10'
              },
              {
                icon: Shield,
                title: 'Responsible Gaming',
                description: 'Player-controlled deposit limits, loss limits, wager limits, and self-exclusion features.',
                color: 'text-amber-500',
                bg: 'bg-amber-500/10'
              },
              {
                icon: Server,
                title: 'Provider Adapter Layer',
                description: 'Compatible wallet callbacks. Easily integrate with any game aggregator.',
                color: 'text-red-500',
                bg: 'bg-red-500/10'
              },
              {
                icon: Globe,
                title: 'Multi-Tenant Domain System',
                description: 'Custom domains per operator with Host header resolution, SEO settings, and branding.',
                color: 'text-cyan-500',
                bg: 'bg-cyan-500/10'
              }
            ].map((feature, idx) => (
              <div 
                key={idx}
                className="p-6 rounded-2xl bg-card border border-border/50 hover:border-primary/30 transition-all duration-300 group hover:shadow-lg hover:shadow-primary/5"
              >
                <div className={`w-14 h-14 rounded-xl ${feature.bg} flex items-center justify-center mb-5 group-hover:scale-110 transition-transform`}>
                  <feature.icon className={`w-7 h-7 ${feature.color}`} />
                </div>
                <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Security & Reliability - NEW SECTION */}
      <section id="security" className="py-24 px-4 sm:px-6 lg:px-8 bg-card/30 border-y border-border/50">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-500/10 text-red-500 text-sm font-medium mb-4">
                <Lock className="w-4 h-4" />
                Enterprise Security
              </div>
              <h2 className="text-3xl sm:text-4xl font-bold mb-6">Security & Reliability</h2>
              <p className="text-lg text-muted-foreground mb-8 leading-relaxed">
                Built with enterprise-grade security from the ground up. Every transaction is protected, 
                every operation is auditable, and every failure is handled gracefully.
              </p>
              
              <div className="space-y-4">
                {[
                  {
                    icon: RefreshCw,
                    title: 'Idempotent Transactions',
                    description: 'Duplicate callbacks return same result. No double-spend possible.'
                  },
                  {
                    icon: Shield,
                    title: 'Strict Rollback Protection',
                    description: 'Only valid rollbacks processed. Reference validation enforced.'
                  },
                  {
                    icon: Database,
                    title: 'Atomic Ledger',
                    description: 'Balance + transaction log in single atomic operation.'
                  },
                  {
                    icon: Users,
                    title: 'Multi-Tenant Isolation',
                    description: 'Complete data separation between operators.'
                  }
                ].map((item, idx) => (
                  <div key={idx} className="flex gap-4 p-4 rounded-xl bg-card border border-border/50">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <item.icon className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                      <h4 className="font-semibold mb-1">{item.title}</h4>
                      <p className="text-sm text-muted-foreground">{item.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="relative">
              <div className="bg-card rounded-2xl border border-border/50 p-8 shadow-xl">
                <div className="flex items-center gap-3 mb-6">
                  <Activity className="w-6 h-6 text-green-500" />
                  <span className="font-semibold">System Health</span>
                  <span className="ml-auto px-3 py-1 rounded-full bg-green-500/10 text-green-500 text-sm font-medium">
                    All Systems Operational
                  </span>
                </div>
                
                <div className="space-y-4">
                  {[
                    { name: 'API Gateway', status: 'Operational', uptime: '99.99%' },
                    { name: 'Wallet Service', status: 'Operational', uptime: '99.99%' },
                    { name: 'Database Cluster', status: 'Operational', uptime: '99.95%' },
                    { name: 'Payment Webhooks', status: 'Operational', uptime: '99.98%' }
                  ].map((service, idx) => (
                    <div key={idx} className="flex items-center justify-between py-3 border-b border-border/50 last:border-0">
                      <div className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-sm">{service.name}</span>
                      </div>
                      <span className="text-sm text-muted-foreground">{service.uptime}</span>
                    </div>
                  ))}
                </div>
                
                <div className="mt-6 p-4 rounded-xl bg-muted/30">
                  <p className="text-xs text-muted-foreground text-center">
                    Secure Wallet • Multi-tenant • Provider-ready
                  </p>
                </div>
              </div>
              
              {/* Decorative elements */}
              <div className="absolute -top-4 -right-4 w-24 h-24 bg-primary/10 rounded-full blur-2xl" />
              <div className="absolute -bottom-4 -left-4 w-32 h-32 bg-primary/5 rounded-full blur-3xl" />
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section - NEW */}
      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary/10 via-primary/5 to-background border border-primary/20 p-8 md:p-16">
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-primary/5 rounded-full blur-2xl" />
            
            <div className="relative text-center">
              <h2 className="text-3xl sm:text-4xl font-bold mb-4">Ready to Launch Your Platform?</h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
                Join operators who trust LooxGame for their gaming infrastructure. 
                Get a personalized demo and see how we can power your operation.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Button 
                  size="lg" 
                  className="h-14 px-10 text-base font-semibold"
                  onClick={() => document.getElementById('contact').scrollIntoView({ behavior: 'smooth' })}
                >
                  <Mail className="w-5 h-5 mr-2" />
                  Request Demo
                </Button>
                <Button 
                  variant="outline" 
                  size="lg"
                  className="h-14 px-10 text-base font-semibold"
                  onClick={() => navigate('/login')}
                >
                  <Headphones className="w-5 h-5 mr-2" />
                  Contact Sales
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section id="contact" className="py-24 px-4 sm:px-6 lg:px-8 bg-card/30 border-t border-border/50">
        <div className="max-w-xl mx-auto">
          <div className="text-center mb-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium mb-4">
              <Mail className="w-4 h-4" />
              Get In Touch
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">Start Your Journey</h2>
            <p className="text-muted-foreground">
              Interested in launching your own gaming platform? Let's talk.
            </p>
          </div>
          
          {submitted ? (
            <div className="text-center p-10 rounded-2xl bg-card border border-primary/30">
              <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-10 h-10 text-primary" />
              </div>
              <h3 className="text-2xl font-semibold mb-2">Thank You!</h3>
              <p className="text-muted-foreground">
                We've received your inquiry and will get back to you within 24 hours.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input 
                  placeholder="Your Name" 
                  required 
                  className="h-14 text-base"
                />
                <Input 
                  type="email" 
                  placeholder="Email Address" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required 
                  className="h-14 text-base"
                />
              </div>
              <Input 
                placeholder="Company / Organization" 
                className="h-14 text-base"
              />
              <textarea 
                placeholder="Tell us about your requirements..."
                rows={5}
                className="w-full px-4 py-4 rounded-xl bg-background border border-border focus:border-primary focus:ring-1 focus:ring-primary outline-none resize-none text-base"
              />
              <Button type="submit" size="lg" className="w-full h-14 text-base font-semibold">
                Send Inquiry
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
              <p className="text-center text-sm text-muted-foreground">
                Or email us directly at{' '}
                <a href="mailto:partnership@looxgame.com" className="text-primary hover:underline font-medium">
                  partnership@looxgame.com
                </a>
              </p>
            </form>
          )}
        </div>
      </section>

      {/* Footer - Professional */}
      <footer className="py-12 px-4 sm:px-6 lg:px-8 border-t border-border/50">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <div className="md:col-span-2">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                  <Zap className="w-5 h-5 text-primary-foreground" />
                </div>
                <span className="text-xl font-bold">LooxGame</span>
              </div>
              <p className="text-sm text-muted-foreground max-w-md leading-relaxed">
                Enterprise-grade white-label iGaming platform. Multi-tenant infrastructure 
                with hardened wallet, idempotent payments, and complete operator control.
              </p>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Platform</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#features" className="hover:text-foreground transition-colors">Features</a></li>
                <li><a href="#security" className="hover:text-foreground transition-colors">Security</a></li>
                <li><a href="/integration/" className="hover:text-foreground transition-colors">API Documentation</a></li>
                <li><a href="#onboarding" className="hover:text-foreground transition-colors">Onboarding</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Contact</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a href="mailto:partnership@looxgame.com" className="hover:text-foreground transition-colors">
                    partnership@looxgame.com
                  </a>
                </li>
                <li>
                  <a href="mailto:support@looxgame.com" className="hover:text-foreground transition-colors">
                    support@looxgame.com
                  </a>
                </li>
              </ul>
            </div>
          </div>
          
          <div className="pt-8 border-t border-border/50 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              © {new Date().getFullYear()} LooxGame. White-Label iGaming Platform.
            </p>
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <span>Built for Operator Growth</span>
              <span>🌐 Global Ready</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
