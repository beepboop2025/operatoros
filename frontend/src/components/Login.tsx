import { useState, FormEvent } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Shield, Eye, EyeOff, Loader2, ArrowRight } from 'lucide-react';
import { AxiosError } from 'axios';

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
      <div className="flex items-center justify-center min-h-screen gradient-hero">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
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
    <div className="min-h-screen gradient-hero flex items-center justify-center p-4 relative overflow-hidden">
      {/* Decorative gradient orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-blue-600/8 rounded-full blur-3xl" />

      <div className="w-full max-w-[420px] relative z-10 animate-slide-up">
        {/* Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 gradient-brand rounded-2xl mb-5 shadow-xl shadow-blue-500/20">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">AuditMind</h1>
          <p className="text-stone-500 mt-2 text-sm">Intelligent Tax & Compliance Platform</p>
        </div>

        {/* Login card */}
        <div className="bg-white rounded-2xl shadow-2xl shadow-black/20 p-8 border border-white/10">
          <h2 className="text-xl font-semibold text-stone-800 mb-1">Welcome back</h2>
          <p className="text-sm text-stone-500 mb-6">Sign in to your account to continue</p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 animate-fade-in">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-stone-700 mb-1.5">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                autoFocus
                className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm
                  focus:bg-white focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none
                  placeholder:text-stone-400 transition-all"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-stone-700 mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  className="w-full px-4 py-2.5 bg-stone-50 border border-stone-200 rounded-xl text-sm pr-10
                    focus:bg-white focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none
                    placeholder:text-stone-400 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 gradient-brand hover:opacity-90 disabled:opacity-50
                text-white font-medium rounded-xl text-sm
                flex items-center justify-center gap-2 transition-all
                shadow-lg shadow-blue-500/25"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                <>
                  Sign In
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-stone-600 text-xs mt-6">
          OperatorOS Platform &middot; Secure &middot; Compliant
        </p>
      </div>
    </div>
  );
}
