import { ReactNode, InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes, forwardRef } from 'react';

interface FieldProps {
  label?: string;
  htmlFor?: string;
  error?: string;
  children: ReactNode;
  className?: string;
}

export function Field({ label, htmlFor, error, children, className = '' }: FieldProps) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      {label && (
        <label htmlFor={htmlFor} className="block text-sm font-medium text-textura-dim">
          {label}
        </label>
      )}
      {children}
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
}

const baseInput =
  'w-full rounded-xl bg-textura-panel-raised/60 border border-textura-line-subtle text-textura-text placeholder:textura-muted px-3 py-2.5 text-sm outline-none transition-all duration-300 ease-textura focus:border-textura-accent/45 focus:bg-textura-panel-raised focus:shadow-[0_0_0_3px_rgba(161,236,255,0.08),0_0_20px_rgba(161,236,255,0.04)]';

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className = '', ...rest }, ref) {
    return <input ref={ref} className={`${baseInput} ${className}`} {...rest} />;
  },
);

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className = '', children, ...rest }, ref) {
    return (
      <select ref={ref} className={`${baseInput} ${className}`} {...rest}>
        {children}
      </select>
    );
  },
);

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className = '', ...rest }, ref) {
    return <textarea ref={ref} className={`${baseInput} ${className}`} {...rest} />;
  },
);
