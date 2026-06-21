import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  FormEvent,
  ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import { X, ArrowRight, Check, Loader2, Sparkles } from 'lucide-react';
import Button from './textura/Button';
import { Field, Input, Select } from './textura/Field';

/**
 * Waitlist — early-access capture for the pre-launch landing page.
 *
 * Exposes openWaitlist(source) via context so any CTA, anywhere in the tree, can
 * trigger the same modal. Submits to the public POST /api/waitlist endpoint and
 * surfaces every state explicitly (submitting / success / error) — a waitlist that
 * silently swallows failures would lose the very leads it exists to collect.
 */

interface WaitlistContextValue {
  openWaitlist: (source?: string) => void;
}

const WaitlistContext = createContext<WaitlistContextValue | null>(null);

export function useWaitlist(): WaitlistContextValue {
  const ctx = useContext(WaitlistContext);
  if (!ctx) throw new Error('useWaitlist must be used within <WaitlistProvider>');
  return ctx;
}

const PERSONAS = [
  { value: '', label: 'I am a…' },
  { value: 'nri', label: 'NRI (living abroad)' },
  { value: 'returning', label: 'Returning to India' },
  { value: 'ca_firm', label: 'CA / Tax firm' },
  { value: 'founder', label: 'Founder / Business owner' },
  { value: 'other', label: 'Something else' },
];

type Status = 'idle' | 'submitting' | 'success' | 'error';

export function WaitlistProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState('landing');
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState('');

  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [persona, setPersona] = useState('');
  const [country, setCountry] = useState('');

  const emailRef = useRef<HTMLInputElement>(null);

  const openWaitlist = useCallback((src = 'landing') => {
    setSource(src);
    setStatus('idle');
    setError('');
    setOpen(true);
  }, []);

  const close = useCallback(() => setOpen(false), []);

  // Esc to close; lock body scroll while open; focus the email field on open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const t = setTimeout(() => emailRef.current?.focus(), 80);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
      clearTimeout(t);
    };
  }, [open, close]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setError('Please enter your email.');
      setStatus('error');
      return;
    }
    setStatus('submitting');
    setError('');
    try {
      const res = await fetch('/api/waitlist/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          name: name.trim() || null,
          persona: persona || null,
          country: country.trim() || null,
          source,
        }),
      });
      if (!res.ok) {
        let detail = `Something went wrong (${res.status}).`;
        try {
          const body = await res.json();
          if (typeof body?.detail === 'string') detail = body.detail;
          else if (Array.isArray(body?.detail) && body.detail[0]?.msg) detail = body.detail[0].msg;
        } catch {
          /* keep generic message */
        }
        throw new Error(detail);
      }
      setStatus('success');
    } catch (err) {
      setStatus('error');
      setError(err instanceof Error ? err.message : 'Network error — please try again.');
    }
  };

  return (
    <WaitlistContext.Provider value={{ openWaitlist }}>
      {children}
      {open &&
        createPortal(
          <div
            className="fixed inset-0 z-[1000] flex items-center justify-center p-4 animate-backdrop"
            style={{ background: 'rgba(0,0,0,0.72)', backdropFilter: 'blur(8px)' }}
            onClick={close}
          >
            <div
              className="relative w-full max-w-md rounded-2xl gradient-border bg-textura-panel-raised/95 backdrop-blur-2xl p-7 sm:p-8 animate-scale-in shadow-[0_24px_80px_rgba(0,0,0,0.6)]"
              onClick={(e) => e.stopPropagation()}
              role="dialog"
              aria-modal="true"
              aria-label="Request early access"
            >
              <button
                onClick={close}
                className="absolute top-4 right-4 p-1.5 rounded-lg text-textura-muted hover:text-textura-text hover:bg-textura-panel transition-colors"
                aria-label="Close"
                data-cursor
              >
                <X className="w-5 h-5" />
              </button>

              {status === 'success' ? (
                <div className="text-center py-6 animate-fade-in">
                  <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-textura-warm to-textura-accent flex items-center justify-center mb-5 shadow-[0_0_40px_rgba(161,236,255,0.35)]">
                    <Check className="w-8 h-8 text-textura-bg" strokeWidth={3} />
                  </div>
                  <h3 className="text-2xl font-[var(--font-gilda)] text-textura-text mb-2">
                    You&apos;re on the list.
                  </h3>
                  <p className="text-sm text-textura-dim leading-relaxed mb-6">
                    Thanks{name ? `, ${name.split(' ')[0]}` : ''}. We&apos;ll email{' '}
                    <span className="text-textura-accent">{email}</span> the moment early access opens.
                  </p>
                  <Button variant="ghost" onClick={close} className="min-w-[140px]" data-cursor-label="Close">
                    Done
                  </Button>
                </div>
              ) : (
                <>
                  <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full border border-textura-line-subtle bg-textura-panel/60 text-[11px] font-medium text-textura-dim mb-4">
                    <Sparkles className="w-3 h-3 text-textura-warm" />
                    Early access — limited cohort
                  </div>
                  <h3 className="text-2xl font-[var(--font-gilda)] text-textura-text mb-1.5">
                    Request access
                  </h3>
                  <p className="text-sm text-textura-dim mb-6 leading-relaxed">
                    Be first to get CA-backed clarity on cross-border tax. No spam — just your invite.
                  </p>

                  <form onSubmit={submit} className="space-y-4">
                    <Field label="Email">
                      <Input
                        ref={emailRef}
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@example.com"
                        autoComplete="email"
                      />
                    </Field>
                    <div className="grid grid-cols-2 gap-3">
                      <Field label="Name">
                        <Input
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          placeholder="Optional"
                          autoComplete="name"
                        />
                      </Field>
                      <Field label="Country">
                        <Input
                          value={country}
                          onChange={(e) => setCountry(e.target.value)}
                          placeholder="e.g. USA"
                          autoComplete="country-name"
                        />
                      </Field>
                    </div>
                    <Field label="You are">
                      <Select value={persona} onChange={(e) => setPersona(e.target.value)}>
                        {PERSONAS.map((p) => (
                          <option key={p.value} value={p.value}>
                            {p.label}
                          </option>
                        ))}
                      </Select>
                    </Field>

                    {status === 'error' && (
                      <p className="text-xs text-danger bg-danger/10 border border-danger/20 rounded-lg px-3 py-2 animate-fade-in">
                        {error}
                      </p>
                    )}

                    <Button
                      type="submit"
                      variant="gradient"
                      size="lg"
                      className="w-full"
                      disabled={status === 'submitting'}
                      data-cursor-label="Join"
                    >
                      {status === 'submitting' ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" /> Joining…
                        </>
                      ) : (
                        <>
                          Join the waitlist <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </Button>
                  </form>
                </>
              )}
            </div>
          </div>,
          document.body,
        )}
    </WaitlistContext.Provider>
  );
}
