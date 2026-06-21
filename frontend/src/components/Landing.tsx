import { useState, FormEvent, ChangeEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import TexturaBackground from './textura/TexturaBackground';
import Panel from './textura/Panel';
import Button from './textura/Button';
import { Input, Select, Field } from './textura/Field';
import {
  Shield,
  Globe,
  FileCheck,
  Landmark,
  Briefcase,
  ArrowRight,
  Menu,
  X,
  CheckCircle2,
  ChevronRight,
  Users,
  Sparkles,
  Lock,
} from 'lucide-react';

const navLinks = [
  { label: 'Features', href: '#features' },
  { label: 'Modules', href: '#modules' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'Trust', href: '#trust' },
];

function Header() {
  const { isAuthenticated } = useAuth();
  const [open, setOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-textura-line-subtle bg-black/60 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-textura-warm to-textura-accent flex items-center justify-center">
              <Shield className="w-5 h-5 text-textura-bg" />
            </div>
            <span className="text-lg font-semibold text-textura-text tracking-tight">OperatorOS</span>
          </Link>

          <nav className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-sm font-medium text-textura-dim hover:text-textura-text transition-colors"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <div className="hidden md:flex items-center gap-3">
            {isAuthenticated ? (
              <Button variant="gradient" onClick={() => window.location.href = '/dashboard'}>
                Dashboard <ArrowRight className="w-4 h-4" />
              </Button>
            ) : (
              <>
                <Link to="/login">
                  <Button variant="ghost">Sign In</Button>
                </Link>
                <Link to="/login">
                  <Button variant="gradient">Get Started</Button>
                </Link>
              </>
            )}
          </div>

          <button
            className="md:hidden p-2 text-textura-dim hover:text-textura-text"
            onClick={() => setOpen(!open)}
            aria-label="Toggle menu"
          >
            {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="md:hidden border-t border-textura-line-subtle bg-black/90 backdrop-blur-xl px-4 py-4 space-y-3 animate-fade-in">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setOpen(false)}
              className="block text-sm font-medium text-textura-dim hover:text-textura-text"
            >
              {link.label}
            </a>
          ))}
          <div className="pt-2 flex flex-col gap-2">
            <Link to="/login" onClick={() => setOpen(false)}>
              <Button variant="ghost" className="w-full">Sign In</Button>
            </Link>
            <Link to="/login" onClick={() => setOpen(false)}>
              <Button variant="gradient" className="w-full">Get Started</Button>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}

function Hero() {
  return (
    <section className="relative pt-32 pb-20 lg:pt-44 lg:pb-32 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-textura-line-subtle bg-textura-panel/50 text-xs font-medium text-textura-dim mb-6 animate-stagger-1">
          <Sparkles className="w-3.5 h-3.5 text-textura-warm" />
          Cross-border tax intelligence for NRIs & global Indians
        </div>

        <h1 className="font-[var(--font-gilda)] text-4xl sm:text-5xl lg:text-7xl font-normal text-textura-text leading-[1.1] tracking-tight mb-6 animate-stagger-2">
          Cross-border tax,{' '}
          <em className="not-italic gradient-text">finally clear.</em>
        </h1>

        <p className="text-lg sm:text-xl text-textura-dim max-w-2xl mx-auto mb-10 animate-stagger-3 leading-relaxed">
          For NRIs, returning Indians, and global founders. Residency, DTAA, TDS, FTC,
          customs, and a world-tax radar — in one CA-backed platform.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-stagger-4">
          <Link to="/login">
            <Button variant="gradient" size="lg" className="min-w-[180px]">
              Start Free <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
          <a href="#residency">
            <Button variant="ghost" size="lg" className="min-w-[180px]">
              Check Residency
            </Button>
          </a>
        </div>

        <p className="mt-4 text-xs text-textura-muted animate-stagger-5">
          CA-reviewed computations. FEMA/RBI aware. No tax surprises.
        </p>
      </div>
    </section>
  );
}

function Features() {
  const features = [
    {
      icon: Globe,
      title: 'Residency Determiner',
      desc: 'Know if you are Resident, RNOR, NRI, or Deemed Resident — with the controlling rule and taxable scope.',
    },
    {
      icon: Landmark,
      title: 'DTAA + FTC',
      desc: 'Explore treaty rates and calculate Foreign Tax Credit to avoid double taxation.',
    },
    {
      icon: FileCheck,
      title: 'Section 195 Toolkit',
      desc: 'TDS on NRI payments, Form 15CA/15CB workflow, and property-sale guidance.',
    },
    {
      icon: Briefcase,
      title: 'World Tax Radar',
      desc: 'Track global tax, trade, and FEMA developments that affect cross-border clients.',
    },
  ];

  return (
    <section id="features" className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-[var(--font-gilda)] text-textura-text mb-3">
            Built for the questions NRIs actually ask
          </h2>
          <p className="text-textura-dim max-w-xl mx-auto">
            Stop guessing across jurisdictions. OperatorOS connects Indian tax law with your life abroad.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {features.map((f, i) => (
            <Panel
              key={f.title}
              interactive
              className="p-6 animate-stagger-1"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-textura-accent/10 to-textura-warm/10 flex items-center justify-center mb-4">
                <f.icon className="w-5 h-5 text-textura-accent" />
              </div>
              <h3 className="text-lg font-semibold text-textura-text mb-2">{f.title}</h3>
              <p className="text-sm text-textura-dim leading-relaxed">{f.desc}</p>
            </Panel>
          ))}
        </div>
      </div>
    </section>
  );
}

function ResidencyHook() {
  const [daysCurrent, setDaysCurrent] = useState<string>('');
  const [daysPrior, setDaysPrior] = useState<string>('');
  const [incomeOver15L, setIncomeOver15L] = useState<string>('no');
  const [residentElsewhere, setResidentElsewhere] = useState<string>('no');
  const [showResult, setShowResult] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setShowResult(true);
  };

  const current = Number(daysCurrent) || 0;
  const prior = Number(daysPrior) || 0;
  const over15L = incomeOver15L === 'yes';
  const elsewhere = residentElsewhere === 'yes';

  let result = '';
  let note = '';
  if (current >= 182) {
    result = 'Resident in India';
    note = '182 days or more in the current FY makes you resident.';
  } else if (current >= 60 && prior >= 365) {
    result = 'Resident in India';
    note = '60 days in current FY + 365 days in prior 4 FYs satisfies the second test.';
  } else if (over15L && current >= 120) {
    result = 'Deemed Resident / Resident';
    note = 'Indian-sourced income over ₹15 lakh + 120 days or more may trigger deemed-residency rules.';
  } else if (elsewhere && over15L) {
    result = 'Deemed Resident';
    note = 'Indian citizen/POS with India-sourced income > ₹15L who is not tax-resident elsewhere may be deemed resident.';
  } else {
    result = 'Non-Resident Indian (NRI)';
    note = 'You do not meet the current FY residency tests.';
  }

  return (
    <section id="residency" className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <Panel elevated className="p-6 sm:p-10 gradient-border">
          <div className="text-center mb-8">
            <h2 className="text-2xl sm:text-3xl font-[var(--font-gilda)] text-textura-text mb-2">
              Am I a resident this year?
            </h2>
            <p className="text-textura-dim text-sm">
              Free preliminary check. CA-verified detailed report available inside.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Field label="Days in India (current FY)">
              <Input
                type="number"
                min={0}
                value={daysCurrent}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setDaysCurrent(e.target.value)}
                placeholder="e.g. 150"
              />
            </Field>
            <Field label="Days in India (prior 4 FYs total)">
              <Input
                type="number"
                min={0}
                value={daysPrior}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setDaysPrior(e.target.value)}
                placeholder="e.g. 400"
              />
            </Field>
            <Field label="India-sourced income > ₹15 lakh?">
              <Select
                value={incomeOver15L}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setIncomeOver15L(e.target.value)}
              >
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </Select>
            </Field>
            <Field label="Tax resident in another country?">
              <Select
                value={residentElsewhere}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setResidentElsewhere(e.target.value)}
              >
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </Select>
            </Field>

            <div className="sm:col-span-2 flex justify-center mt-2">
              <Button variant="gradient" type="submit" className="min-w-[200px]">
                Check Residency
              </Button>
            </div>
          </form>

          {showResult && (
            <div className="mt-8 p-5 rounded-xl border border-textura-accent/20 bg-textura-accent/5 animate-fade-in">
              <h3 className="text-lg font-semibold text-textura-accent mb-1">{result}</h3>
              <p className="text-sm text-textura-dim mb-4">{note}</p>
              <p className="text-xs text-textura-muted">
                This is a simplified preview. Final determination requires a CA review of your exact dates,
                citizenship status, and income sources.
              </p>
            </div>
          )}
        </Panel>
      </div>
    </section>
  );
}

function DTAAHook() {
  const countries = ['United States', 'UAE', 'United Kingdom', 'Canada', 'Australia', 'Singapore'];
  const [country, setCountry] = useState('');

  return (
    <section className="py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <Panel className="p-6 sm:p-10">
          <div className="text-center mb-8">
            <h2 className="text-2xl sm:text-3xl font-[var(--font-gilda)] text-textura-text mb-2">
              Am I being double-taxed?
            </h2>
            <p className="text-textura-dim text-sm">
              Preview treaty coverage for top NRI corridors.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 items-end max-w-xl mx-auto">
            <Field label="Treaty partner country" className="flex-1 w-full">
              <Select
                value={country}
                onChange={(e: ChangeEvent<HTMLSelectElement>) => setCountry(e.target.value)}
              >
                <option value="">Select a country</option>
                {countries.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </Select>
            </Field>
            <Link to="/login">
              <Button variant="gradient" className="w-full sm:w-auto">
                View Treaty
              </Button>
            </Link>
          </div>

          {country && (
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 animate-fade-in">
              {['Dividends', 'Interest', 'Royalties / FTS', 'Capital Gains'].map((topic) => (
                <div
                  key={topic}
                  className="p-4 rounded-xl border border-textura-line-subtle bg-textura-panel-raised/40"
                >
                  <p className="text-sm font-medium text-textura-text">{topic}</p>
                  <p className="text-xs text-textura-muted mt-1">
                    Article rate and TRC/Form 10F requirements available after sign-up.
                  </p>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </section>
  );
}

function Modules() {
  const modules = [
    'Residential Status Determiner',
    'DTAA Explorer',
    'Section 195 / Repatriation Toolkit',
    'Foreign Tax Credit (FTC)',
    'Customs & Tariffs',
    'Cross-border GST',
  ];

  return (
    <section id="modules" className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-[var(--font-gilda)] text-textura-text mb-3">
            Every cross-border tax module in one place
          </h2>
          <p className="text-textura-dim max-w-xl mx-auto">
            Pure-logic engines + CA-verified data + a reskinned dashboard experience.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {modules.map((m, i) => (
            <div
              key={m}
              className="flex items-center gap-3 p-4 rounded-xl border border-textura-line-subtle bg-textura-panel/50 hover:border-textura-accent/25 transition-colors"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <CheckCircle2 className="w-5 h-5 text-textura-accent shrink-0" />
              <span className="text-sm font-medium text-textura-text">{m}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Pricing() {
  const plans = [
    {
      name: 'Starter',
      price: 'Free',
      desc: 'For individuals exploring their status.',
      features: ['Residency determiner', 'DTAA topic preview', 'World Tax Radar feed (limited)'],
      cta: 'Sign Up Free',
      popular: false,
    },
    {
      name: 'Professional',
      price: '₹4,999',
      period: '/mo',
      desc: 'For CA firms and global Indians with active filings.',
      features: ['All calculators', 'Full DTAA explorer', 'FTC & Section 195 toolkit', 'Document & notice management'],
      cta: 'Start Free Trial',
      popular: true,
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      desc: 'For multi-jurisdiction teams and bulk compliance.',
      features: ['Team workload', 'White-glove onboarding', 'API access', 'Dedicated CA support'],
      cta: 'Contact Sales',
      popular: false,
    },
  ];

  return (
    <section id="pricing" className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-[var(--font-gilda)] text-textura-text mb-3">
            Simple, transparent pricing
          </h2>
          <p className="text-textura-dim max-w-xl mx-auto">
            Start free. Upgrade when you need CA-backed depth.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <Panel
              key={plan.name}
              elevated={plan.popular}
              className={`p-6 flex flex-col ${plan.popular ? 'border-textura-accent/30 shadow-[0_0_40px_rgba(161,236,255,0.08)]' : ''}`}
            >
              {plan.popular && (
                <span className="self-start px-2.5 py-0.5 rounded-full bg-textura-accent/10 text-textura-accent text-xs font-medium mb-4">
                  Most Popular
                </span>
              )}
              <h3 className="text-lg font-semibold text-textura-text">{plan.name}</h3>
              <div className="flex items-baseline gap-1 mt-2 mb-3">
                <span className="text-3xl font-bold text-textura-text">{plan.price}</span>
                {plan.period && <span className="text-textura-muted text-sm">{plan.period}</span>}
              </div>
              <p className="text-sm text-textura-dim mb-6">{plan.desc}</p>
              <ul className="space-y-3 mb-8 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-textura-dim">
                    <CheckCircle2 className="w-4 h-4 text-textura-accent shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link to="/login">
                <Button variant={plan.popular ? 'gradient' : 'ghost'} className="w-full">
                  {plan.cta}
                </Button>
              </Link>
            </Panel>
          ))}
        </div>
      </div>
    </section>
  );
}

function Trust() {
  const points = [
    { icon: Shield, title: 'CA-reviewed', desc: 'Every computation surfaces a CA-review affordance.' },
    { icon: Lock, title: 'Secure & Compliant', desc: 'Built for Indian tax practice with audit-ready logs.' },
    { icon: Users, title: 'India + International', desc: 'Covers Indian income-tax, FEMA/RBI, DTAA, and customs.' },
  ];

  return (
    <section id="trust" className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl sm:text-4xl font-[var(--font-gilda)] text-textura-text mb-3">
            Trusted by cross-border tax practitioners
          </h2>
          <p className="text-textura-dim max-w-xl mx-auto">
            We do not invent tax law. We make it computable, reviewable, and actionable.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {points.map((p) => (
            <Panel key={p.title} className="p-6 text-center">
              <div className="w-12 h-12 mx-auto rounded-full bg-textura-panel-raised border border-textura-line-subtle flex items-center justify-center mb-4">
                <p.icon className="w-5 h-5 text-textura-warm" />
              </div>
              <h3 className="text-lg font-semibold text-textura-text mb-2">{p.title}</h3>
              <p className="text-sm text-textura-dim">{p.desc}</p>
            </Panel>
          ))}
        </div>
      </div>
    </section>
  );
}

function CTA() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <Panel elevated className="p-10 sm:p-16 text-center gradient-border">
          <h2 className="text-3xl sm:text-4xl font-[var(--font-gilda)] text-textura-text mb-4">
            Stop guessing. Start computing.
          </h2>
          <p className="text-textura-dim max-w-lg mx-auto mb-8">
            Join NRIs, returning Indians, and global founders who use OperatorOS to stay clear on cross-border tax.
          </p>
          <Link to="/login">
            <Button variant="gradient" size="lg">
              Get Started Free <ChevronRight className="w-4 h-4" />
            </Button>
          </Link>
        </Panel>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-textura-line-subtle py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-textura-accent" />
          <span className="text-sm font-medium text-textura-text">OperatorOS</span>
        </div>
        <p className="text-xs text-textura-muted text-center md:text-right">
          OperatorOS Platform &middot; CA-backed &middot; FEMA/RBI aware &middot; Not a substitute for professional tax advice.
        </p>
      </div>
    </footer>
  );
}

export default function Landing() {
  return (
    <TexturaBackground>
      <Header />
      <main>
        <Hero />
        <Features />
        <ResidencyHook />
        <DTAAHook />
        <Modules />
        <Pricing />
        <Trust />
        <CTA />
      </main>
      <Footer />
    </TexturaBackground>
  );
}
