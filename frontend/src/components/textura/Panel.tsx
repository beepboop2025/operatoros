import { ReactNode, CSSProperties } from 'react';

interface PanelProps {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  elevated?: boolean;
  interactive?: boolean;
  overflowHidden?: boolean;
}

export default function Panel({
  children,
  className = '',
  style,
  elevated = false,
  interactive = false,
  overflowHidden = false,
}: PanelProps) {
  const base = 'rounded-2xl border border-textura-line-subtle backdrop-blur-xl';
  const bg = elevated
    ? 'bg-textura-panel-raised/90'
    : 'bg-textura-panel/80';
  const hover = interactive
    ? 'transition-all duration-300 ease-textura hover:border-textura-accent/25 hover:shadow-[0_12px_40px_rgba(0,0,0,0.45)] hover:-translate-y-0.5 cursor-pointer'
    : 'transition-all duration-300 ease-textura hover:border-textura-line';
  const overflow = overflowHidden ? 'overflow-hidden' : '';

  return (
    <div className={`${base} ${bg} ${hover} ${overflow} ${className}`} style={style}>
      {children}
    </div>
  );
}
