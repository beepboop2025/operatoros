/**
 * Format a number as Indian currency (INR)
 * e.g. 1234567 -> "12,34,567"
 */
export function formatIndianNumber(num: number | string | null | undefined): string {
  if (num == null || isNaN(Number(num))) return '0';
  const n = Number(num);
  const isNeg = n < 0;
  const abs = Math.abs(n);
  const str = Math.floor(abs).toString();

  if (str.length <= 3) return (isNeg ? '-' : '') + str;

  // Last 3 digits
  let result = str.slice(-3);
  let remaining = str.slice(0, -3);

  // Group in pairs from right
  while (remaining.length > 0) {
    const chunk = remaining.slice(-2);
    result = chunk + ',' + result;
    remaining = remaining.slice(0, -2);
  }

  return (isNeg ? '-' : '') + result;
}

/**
 * Format currency with INR symbol
 * e.g. 1234567.89 -> "Rs.12,34,567.89"
 */
export function formatCurrency(amount: number | string | null | undefined, decimals: number = 0): string {
  if (amount == null || isNaN(Number(amount))) return '\u20B90';
  const n = Number(amount);
  const whole = formatIndianNumber(Math.floor(Math.abs(n)));
  const sign = n < 0 ? '-' : '';

  if (decimals > 0) {
    const frac = Math.abs(n % 1).toFixed(decimals).slice(2);
    return `${sign}\u20B9${whole}.${frac}`;
  }
  return `${sign}\u20B9${whole}`;
}

/**
 * Format currency in lakhs/crores for large numbers
 */
export function formatCurrencyShort(amount: number | string | null | undefined): string {
  if (amount == null || isNaN(Number(amount))) return '\u20B90';
  const n = Number(amount);
  const abs = Math.abs(n);
  const sign = n < 0 ? '-' : '';

  if (abs >= 1e7) return `${sign}\u20B9${(abs / 1e7).toFixed(2)} Cr`;
  if (abs >= 1e5) return `${sign}\u20B9${(abs / 1e5).toFixed(2)} L`;
  if (abs >= 1e3) return `${sign}\u20B9${formatIndianNumber(Math.round(abs))}`;
  return `${sign}\u20B9${abs.toFixed(0)}`;
}

/**
 * Format date as DD/MM/YYYY (Indian standard)
 */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return '--';
  const d = new Date(date);
  if (isNaN(d.getTime())) return '--';
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  return `${dd}/${mm}/${yyyy}`;
}

/**
 * Format date and time
 */
export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return '--';
  const d = new Date(date);
  if (isNaN(d.getTime())) return '--';
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  const hh = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${dd}/${mm}/${yyyy} ${hh}:${min}`;
}

/**
 * Assessment years list
 */
export function getAssessmentYears(): string[] {
  const current = new Date().getFullYear();
  const years: string[] = [];
  for (let y = current + 1; y >= current - 3; y--) {
    years.push(`${y - 1}-${String(y).slice(2)}`);
  }
  return years;
}

/**
 * Status badge color mapping (dark theme)
 */
export function statusColor(status: string | null | undefined): string {
  const map: Record<string, string> = {
    completed: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20',
    done: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20',
    active: 'bg-blue-500/15 text-blue-400 border border-blue-500/20',
    in_progress: 'bg-blue-500/15 text-blue-400 border border-blue-500/20',
    pending: 'bg-amber-500/15 text-amber-400 border border-amber-500/20',
    overdue: 'bg-red-500/15 text-red-400 border border-red-500/20',
    failed: 'bg-red-500/15 text-red-400 border border-red-500/20',
    draft: 'bg-slate-500/15 text-slate-400 border border-slate-500/20',
    draft_ready: 'bg-violet-500/15 text-violet-400 border border-violet-500/20',
    processing: 'bg-violet-500/15 text-violet-400 border border-violet-500/20',
    uploaded: 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/20',
    responded: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20',
    closed: 'bg-slate-500/15 text-slate-400 border border-slate-500/20',
  };
  return map[status?.toLowerCase() ?? ''] || 'bg-slate-500/15 text-slate-400 border border-slate-500/20';
}
