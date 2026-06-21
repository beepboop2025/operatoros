import { useState, FormEvent } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Shield, Eye, EyeOff, ArrowRight } from 'lucide-react';
import { AxiosError } from 'axios';
import { Panel, Button, Field, Input } from './textura';

export default function Login() {
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-textura-bg">
        <div className="w-8 h-8 border-4 border-textura-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    if (!email.trim() || !password.trim()) {
      setError('Please enter both email and password.');
      return;
    }
    setIsLoading(true);
    try {
      await login(email.trim(), password);
      navigate('/', { replace: true });
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail?: string; message?: string }>;
      const msg = axiosErr.response?.data?.detail || axiosErr.response?.data?.message || 'Invalid credentials. Please try again.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-textura-bg flex items-center justify-center p-4 relative overflow-hidden">
      {/* Decorative gradient orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-textura-accent/8 rounded-full blur-[120px]" />
      <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-textura-accent/6 rounded-full blur-[120px]" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-textura-accent/3 rounded-full blur-[200px]" />

      <div className="w-full max-w-[420px] relative z-10 animate-slide-up">
        {/* Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 gradient-brand rounded-2xl mb-5 shadow-2xl shadow-textura-accent/30 glow-blue">
            <Shield className="w-8 h-8 text-textura-text" />
          </div>
          <h1 className="text-3xl font-bold text-textura-text tracking-tight">AuditMind</h1>
          <p className="text-textura-muted mt-2 text-sm">Intelligent Tax & Compliance Platform</p>
        </div>

        {/* Login card */}
        <Panel className="p-8 shadow-2xl shadow-black/40 border-textura-line">
          <h2 className="text-xl font-semibold text-textura-text mb-1">Welcome back</h2>
          <p className="text-sm text-textura-dim mb-6">Sign in to your account to continue</p>

          {error && (
            <div className="mb-4 p-3 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Field label="Email Address" htmlFor="email">
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                autoFocus
              />
            </Field>

            <Field label="Password" htmlFor="password">
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-textura-muted hover:text-textura-dim transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </Field>

            <Button
              type="submit"
              variant="gradient"
              size="md"
              loading={isLoading}
              icon={!isLoading ? <ArrowRight className="w-4 h-4" /> : undefined}
              className="w-full"
            >
              Sign In
            </Button>
          </form>
        </Panel>

        <p className="text-center text-textura-muted text-xs mt-6">
          OperatorOS Platform &middot; Secure &middot; Compliant
        </p>
      </div>
    </div>
  );
}
