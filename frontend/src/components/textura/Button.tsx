import { ReactNode, ButtonHTMLAttributes, forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

type ButtonVariant = 'primary' | 'gradient' | 'ghost' | 'danger' | 'success';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
  className?: string;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    children,
    variant = 'primary',
    size = 'md',
    loading = false,
    icon,
    className = '',
    disabled,
    ...rest
  },
  ref,
) {
  const base =
    'inline-flex items-center justify-center gap-2 font-medium rounded-xl transition-all duration-300 ease-textura focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-textura-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-black disabled:opacity-50 disabled:cursor-not-allowed';

  const sizeClasses: Record<ButtonSize, string> = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-6 py-3 text-sm',
  };

  const variantClasses: Record<ButtonVariant, string> = {
    primary:
      'bg-textura-text text-textura-bg hover:bg-textura-dim shadow-lg shadow-white/5',
    gradient:
      'bg-gradient-to-r from-textura-warm to-textura-accent text-textura-bg hover:shadow-[0_8px_28px_rgba(161,236,255,0.22)] hover:brightness-105',
    ghost:
      'bg-transparent text-textura-dim border border-textura-line-subtle hover:bg-textura-panel-raised hover:text-textura-text hover:border-textura-line',
    danger:
      'bg-danger/10 text-danger border border-danger/20 hover:bg-danger/15',
    success:
      'bg-success/10 text-success border border-success/20 hover:bg-success/15',
  };

  return (
    <button
      ref={ref}
      className={`${base} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : icon}
      {children}
    </button>
  );
});

export default Button;
