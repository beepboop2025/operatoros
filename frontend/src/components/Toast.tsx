import { createContext, useContext, useCallback, useState, ReactNode } from 'react';
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react';

// ── Types ────────────────────────────────────────────────────────────────────

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  exiting: boolean;
}

interface ToastContextType {
  toast: (message: string, type?: ToastType) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useToast(): ToastContextType {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

// ── Styles per type ──────────────────────────────────────────────────────────

const TYPE_STYLES: Record<ToastType, { border: string; iconColor: string; Icon: typeof CheckCircle }> = {
  success: {
    border: 'border-success/25',
    iconColor: 'text-success',
    Icon: CheckCircle,
  },
  error: {
    border: 'border-danger/25',
    iconColor: 'text-danger',
    Icon: AlertCircle,
  },
  warning: {
    border: 'border-warning/25',
    iconColor: 'text-warning',
    Icon: AlertTriangle,
  },
  info: {
    border: 'border-textura-accent/25',
    iconColor: 'text-textura-accent',
    Icon: Info,
  },
};

const AUTO_DISMISS_MS = 4000;
const EXIT_ANIMATION_MS = 300;
const MAX_TOASTS = 3;

let idCounter = 0;

// ── Provider ─────────────────────────────────────────────────────────────────

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    // Start exit animation
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)));
    // Remove after animation
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, EXIT_ANIMATION_MS);
  }, []);

  const addToast = useCallback(
    (message: string, type: ToastType = 'info') => {
      const id = `toast-${Date.now()}-${++idCounter}`;
      setToasts((prev) => {
        const next = [...prev, { id, type, message, exiting: false }];
        // Trim to MAX_TOASTS (exit oldest)
        if (next.length > MAX_TOASTS) {
          const oldest = next[0];
          setTimeout(() => removeToast(oldest.id), 0);
        }
        return next.slice(-MAX_TOASTS);
      });
      // Auto-dismiss
      setTimeout(() => removeToast(id), AUTO_DISMISS_MS);
    },
    [removeToast],
  );

  const ctx: ToastContextType = {
    toast: addToast,
    success: useCallback((m: string) => addToast(m, 'success'), [addToast]),
    error: useCallback((m: string) => addToast(m, 'error'), [addToast]),
    warning: useCallback((m: string) => addToast(m, 'warning'), [addToast]),
    info: useCallback((m: string) => addToast(m, 'info'), [addToast]),
  };

  return (
    <ToastContext.Provider value={ctx}>
      {children}

      {/* Toast container — bottom right */}
      <div
        className="fixed bottom-4 right-4 z-[9999] flex flex-col-reverse gap-2 pointer-events-none"
        style={{ maxWidth: 380 }}
        aria-live="polite"
      >
        {toasts.map((t) => (
          <ToastCard key={t.id} item={t} onClose={() => removeToast(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// ── Individual toast ─────────────────────────────────────────────────────────

function ToastCard({ item, onClose }: { item: ToastItem; onClose: () => void }) {
  const style = TYPE_STYLES[item.type];
  const Icon = style.Icon;

  return (
    <div
      className={`pointer-events-auto flex items-start gap-3 rounded-2xl px-4 py-3 border bg-textura-panel/85 backdrop-blur-xl shadow-2xl shadow-black/40 ${style.border}`}
      style={{
        animation: item.exiting
          ? `toast-exit ${EXIT_ANIMATION_MS}ms cubic-bezier(0.4, 0, 1, 1) forwards`
          : `toast-enter 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards`,
      }}
      role="alert"
    >
      <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${style.iconColor}`} />

      <p className="text-sm text-textura-text flex-1">{item.message}</p>

      {/* Close button */}
      <button
        onClick={onClose}
        className="flex-shrink-0 text-textura-muted hover:text-textura-text transition-colors mt-0.5"
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
