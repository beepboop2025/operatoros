import { ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: ReactNode;
  icon: LucideIcon;
  sub?: string;
  variant?: 'accent' | 'warm' | 'success' | 'danger' | 'muted';
  delay?: number;
  className?: string;
}

const variantMap: Record<string, { iconBg: string; border: string; text: string }> = {
  accent: {
    iconBg: 'bg-textura-accent/10 text-textura-accent',
    border: 'border-textura-accent/15',
    text: 'text-textura-accent',
  },
  warm: {
    iconBg: 'bg-textura-warm/10 text-textura-warm',
    border: 'border-textura-warm/15',
    text: 'text-textura-warm',
  },
  success: {
    iconBg: 'bg-success/10 text-success',
    border: 'border-success/15',
    text: 'text-success',
  },
  danger: {
    iconBg: 'bg-danger/10 text-danger',
    border: 'border-danger/15',
    text: 'text-danger',
  },
  muted: {
    iconBg: 'bg-textura-line-subtle text-textura-dim',
    border: 'border-textura-line-subtle',
    text: 'text-textura-dim',
  },
};

export default function StatCard({
  title,
  value,
  icon: Icon,
  sub,
  variant = 'accent',
  delay = 0,
  className = '',
}: StatCardProps) {
  const styles = variantMap[variant];

  return (
    <div
      className={`relative rounded-2xl border backdrop-blur-xl bg-textura-panel/70 p-5 transition-all duration-300 ease-textura hover:border-textura-line hover:shadow-[0_8px_32px_rgba(0,0,0,0.35)] ${styles.border} ${className}`}
      style={delay ? { animationDelay: `${delay}ms` } : undefined}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[13px] font-medium text-textura-muted">{title}</p>
          <p className={`text-2xl font-bold text-textura-text mt-1 ${styles.text}`}>{value ?? '--'}</p>
          {sub && <p className="text-xs text-textura-muted mt-1">{sub}</p>}
        </div>
        <div
          className={`w-10 h-10 rounded-xl flex items-center justify-center ${styles.iconBg}`}
        >
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}
