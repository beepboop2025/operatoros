import { createContext, useContext, useCallback, useState, useEffect, ReactNode } from 'react';

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

const TYPE_STYLES: Record<ToastType, { bg: string; border: string; icon: string; iconPath: string }> = {
  success: {
    bg: 'rgba(16, 185, 129, 0.1)',
    border: 'rgba(16, 185, 129, 0.25)',
    icon: '#10b981',
    iconPath: 'M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  },
  error: {
    bg: 'rgba(239, 68, 68, 0.1)',
    border: 'rgba(239, 68, 68, 0.25)',
    icon: '#ef4444',
    iconPath: 'M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z',
  },
  warning: {
    bg: 'rgba(245, 158, 11, 0.1)',
    border: 'rgba(245, 158, 11, 0.25)',
    icon: '#f59e0b',
    iconPath: 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z',
  },
  info: {
    bg: 'rgba(59, 130, 246, 0.1)',
    border: 'rgba(59, 130, 246, 0.25)',
    icon: '#3b82f6',
    iconPath: 'm11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z',
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

  return (
    <div
      className="pointer-events-auto flex items-start gap-3 rounded-xl px-4 py-3 shadow-lg"
      style={{
        background: style.bg,
        border: `1px solid ${style.border}`,
        backdropFilter: 'blur(16px)',
        animation: item.exiting
          ? `toast-exit ${EXIT_ANIMATION_MS}ms cubic-bezier(0.4, 0, 1, 1) forwards`
          : `toast-enter 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards`,
      }}
      role="alert"
    >
      {/* Icon */}
      <svg
        className="w-5 h-5 mt-0.5 flex-shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke={style.icon}
        strokeWidth={1.5}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d={style.iconPath} />
      </svg>

      <p className="text-sm text-slate-200 flex-1">{item.message}</p>

      {/* Close button */}
      <button
        onClick={onClose}
        className="flex-shrink-0 text-slate-500 hover:text-slate-300 transition-colors mt-0.5"
        aria-label="Dismiss"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}
