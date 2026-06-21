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
 * Status badge color mapping (Textura dark theme)
 */
export function statusColor(status: string | null | undefined): string {
  const map: Record<string, string> = {
    completed: 'bg-success/15 text-success border border-success/20',
    done: 'bg-success/15 text-success border border-success/20',
    active: 'bg-textura-accent/15 text-textura-accent border border-textura-accent/20',
    in_progress: 'bg-textura-accent/15 text-textura-accent border border-textura-accent/20',
    pending: 'bg-warning/15 text-warning border border-warning/20',
    overdue: 'bg-danger/15 text-danger border border-danger/20',
    failed: 'bg-danger/15 text-danger border border-danger/20',
    draft: 'bg-textura-muted/15 text-textura-muted border border-textura-muted/20',
    draft_ready: 'bg-purple-500/15 text-purple-400 border border-purple-500/20',
    processing: 'bg-purple-500/15 text-purple-400 border border-purple-500/20',
    uploaded: 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/20',
    responded: 'bg-success/15 text-success border border-success/20',
    closed: 'bg-textura-muted/15 text-textura-muted border border-textura-muted/20',
  };
  return map[status?.toLowerCase() ?? ''] || 'bg-textura-muted/15 text-textura-muted border border-textura-muted/20';
}
