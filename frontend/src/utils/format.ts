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
 * Status badge color mapping
 */
export function statusColor(status: string | null | undefined): string {
  const map: Record<string, string> = {
    completed: 'bg-green-100 text-green-700',
    done: 'bg-green-100 text-green-700',
    active: 'bg-blue-100 text-blue-700',
    in_progress: 'bg-blue-100 text-blue-700',
    pending: 'bg-yellow-100 text-yellow-700',
    overdue: 'bg-red-100 text-red-700',
    failed: 'bg-red-100 text-red-700',
    draft: 'bg-slate-100 text-slate-600',
    processing: 'bg-purple-100 text-purple-700',
    uploaded: 'bg-cyan-100 text-cyan-700',
  };
  return map[status?.toLowerCase() ?? ''] || 'bg-slate-100 text-slate-600';
}
