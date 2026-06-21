import { useState, type ChangeEvent, type ReactNode } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  nriApi,
  getErrorMessage,
  type ResidentialStatusRequest,
  type ResidentialStatusResponse,
  type DTAARequest,
  type DTAAResponse,
  type Section195Request,
  type Section195Response,
  type FTCRequest,
  type FTCResponse,
  type FTCCreditCountryInput,
  type CustomsTariffRequest,
  type CustomsTariffResponse,
  type CrossBorderGSTRequest,
  type CrossBorderGSTResponse,
  type DTAARateEntry,
} from '../api/client';
import { useToast } from './Toast';
import {
  Panel,
  Button,
  Field,
  Input,
  Select,
  Tabs,
  StatCard,
  DataTable,
  DataTableHeader,
  DataTableHead,
  DataTableBody,
  DataTableRow,
  DataTableCell,
} from './textura';
import {
  Globe,
  Home,
  Landmark,
  FileCheck,
  Briefcase,
  Ship,
  Calculator,
  Plus,
  Trash2,
  AlertCircle,
  CheckCircle2,
  type LucideIcon,
} from 'lucide-react';
import { formatCurrency, formatDate, getAssessmentYears, statusColor } from '../utils/format';

// ─── Shared helpers ───────────────────────────────────────────

interface SelectOption {
  value: string;
  label: string;
}

function SelectInput({
  label,
  value,
  onChange,
  options,
  className = '',
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  className?: string;
}) {
  return (
    <Field label={label} className={className}>
      <Select value={value} onChange={(e: ChangeEvent<HTMLSelectElement>) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>
    </Field>
  );
}

function NumInput({
  label,
  value,
  onChange,
  placeholder = '0',
  prefix,
  className = '',
}: {
  label: string;
  value: number | string;
  onChange: (value: number) => void;
  placeholder?: string;
  prefix?: ReactNode;
  className?: string;
}) {
  return (
    <Field label={label} className={className}>
      <div className="relative">
        {prefix && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-textura-muted text-sm">{prefix}</span>
        )}
        <Input
          type="number"
          min={0}
          step="any"
          value={value}
          onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value === '' ? 0 : Number(e.target.value))}
          placeholder={placeholder}
          className={prefix ? 'pl-7' : ''}
        />
      </div>
    </Field>
  );
}

function CheckInput({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-textura-dim cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.checked)}
        className="rounded border-textura-line-subtle bg-textura-panel-raised text-textura-accent focus:ring-textura-accent"
      />
      {label}
    </label>
  );
}

interface ResultCardProps {
  title: string;
  children: ReactNode;
  className?: string;
}

function ResultCard({ title, children, className = '' }: ResultCardProps) {
  return (
    <Panel className={`overflow-hidden animate-fade-in ${className}`}>
      <div className="px-5 py-3 border-b border-textura-line-subtle bg-textura-panel-raised/40">
        <h4 className="font-semibold text-textura-text text-sm">{title}</h4>
      </div>
      <div className="p-5">{children}</div>
    </Panel>
  );
}

function ResultRow({
  label,
  value,
  bold,
  highlight,
}: {
  label: string;
  value: ReactNode;
  bold?: boolean;
  highlight?: boolean;
}) {
  return (
    <div
      className={`flex justify-between py-1.5 ${bold ? 'font-semibold' : ''} ${
        highlight ? 'text-textura-accent bg-textura-accent/8 -mx-2 px-2 rounded-lg' : ''
      }`}
    >
      <span
        className={`text-sm ${highlight ? 'text-textura-accent' : bold ? 'text-textura-text' : 'text-textura-dim'}`}
      >
        {label}
      </span>
      <span
        className={`text-sm font-mono ${
          highlight ? 'text-textura-accent' : bold ? 'text-textura-text' : 'text-textura-dim'
        }`}
      >
        {value}
      </span>
    </div>
  );
}

function PendingBadge({ text = 'Pending CA review' }: { text?: string }) {
  return <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${statusColor('pending')}`}>{text}</span>;
}

function EmptyValue() {
  return <span className="text-textura-muted">--</span>;
}

function rateValue(rate: number | null | undefined, fallback = 'pending'): ReactNode {
  if (rate == null) return <EmptyValue />;
  return `${(rate * 100).toFixed(2)}%`;
}

const COUNTRY_OPTIONS: SelectOption[] = [
  { value: '', label: 'Select country' },
  { value: 'United States', label: 'United States' },
  { value: 'UAE', label: 'UAE' },
  { value: 'United Kingdom', label: 'United Kingdom' },
  { value: 'Canada', label: 'Canada' },
  { value: 'Australia', label: 'Australia' },
  { value: 'Singapore', label: 'Singapore' },
];

const SECTION_195_PAYMENT_OPTIONS: SelectOption[] = [
  { value: 'interest', label: 'Interest' },
  { value: 'dividend', label: 'Dividend' },
  { value: 'royalty', label: 'Royalty' },
  { value: 'fees_for_technical_services', label: 'Fees for Technical Services' },
  { value: 'rent', label: 'Rent' },
  { value: 'property_sale', label: 'Property Sale' },
  { value: 'other', label: 'Other' },
];

const CB_GST_TRANSACTION_OPTIONS: SelectOption[] = [
  { value: 'import', label: 'Import' },
  { value: 'export', label: 'Export' },
  { value: 'oidar', label: 'OIDAR' },
  { value: 'domestic', label: 'Domestic' },
];

// ─── 1. RESIDENTIAL STATUS ────────────────────────────────────

function ResidentialStatusTab() {
  const toast = useToast();
  const [form, setForm] = useState<ResidentialStatusRequest>({
    assessment_year: getAssessmentYears()[0],
    days_in_india_current_fy: 0,
    days_in_india_prior_4_fys: [0, 0, 0, 0],
    is_indian_citizen: false,
    is_person_of_indian_origin: false,
    leaving_for_employment: false,
    is_crew_of_indian_ship: false,
    indian_source_income: 0,
    tax_resident_elsewhere: false,
  });

  const mutation = useMutation<ResidentialStatusResponse, Error, ResidentialStatusRequest>({
    mutationFn: (data) => nriApi.residentialStatus(data),
    onSuccess: () => toast.success('Residential status determined'),
    onError: (err) => toast.error(`Determination failed: ${err.message}`),
  });

  const update = <K extends keyof ResidentialStatusRequest>(field: K, value: ResidentialStatusRequest[K]) =>
    setForm((f) => ({ ...f, [field]: value }));

  const updatePriorYear = (index: number, value: number) => {
    const next = [...form.days_in_india_prior_4_fys];
    next[index] = value;
    update('days_in_india_prior_4_fys', next);
  };

  const result = mutation.data;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SelectInput
          label="Assessment Year"
          value={form.assessment_year}
          onChange={(v) => update('assessment_year', v)}
          options={getAssessmentYears().map((y) => ({ value: y, label: y }))}
        />
        <NumInput
          label="Days in India (current FY)"
          value={form.days_in_india_current_fy}
          onChange={(v) => update('days_in_india_current_fy', v)}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-textura-dim mb-2">Days in India (prior 4 FYs)</label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {form.days_in_india_prior_4_fys.map((days, i) => (
            <NumInput
              key={i}
              label={`FY -${i + 1}`}
              value={days}
              onChange={(v) => updatePriorYear(i, v)}
            />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <NumInput
          label="Indian-source income"
          value={form.indian_source_income}
          onChange={(v) => update('indian_source_income', v)}
          prefix="₹"
        />
        <div className="space-y-2">
          <CheckInput label="Indian citizen" checked={form.is_indian_citizen} onChange={(v) => update('is_indian_citizen', v)} />
          <CheckInput label="Person of Indian origin" checked={form.is_person_of_indian_origin} onChange={(v) => update('is_person_of_indian_origin', v)} />
        </div>
        <div className="space-y-2">
          <CheckInput label="Leaving India for employment" checked={form.leaving_for_employment} onChange={(v) => update('leaving_for_employment', v)} />
          <CheckInput label="Crew of Indian ship" checked={form.is_crew_of_indian_ship} onChange={(v) => update('is_crew_of_indian_ship', v)} />
        </div>
        <div className="space-y-2">
          <CheckInput label="Tax resident elsewhere" checked={form.tax_resident_elsewhere} onChange={(v) => update('tax_resident_elsewhere', v)} />
        </div>
      </div>

      <Button
        variant="gradient"
        loading={mutation.isPending}
        icon={<Calculator className="w-4 h-4" />}
        onClick={() => mutation.mutate(form)}
        className="hover-lift"
      >
        Determine Status
      </Button>

      {mutation.isError && (
        <div className="p-4 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
          {getErrorMessage(mutation.error, 'Determination failed')}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard title="Status" value={result.status} icon={Home} variant="accent" />
            <StatCard title="Taxable Scope" value={result.taxable_scope} icon={Globe} variant="warm" />
            <StatCard title="Threshold Days" value={result.threshold_days} icon={CheckCircle2} variant="success" />
          </div>
          <ResultCard title="Determination Working">
            <ResultRow label="Controlling Rule" value={result.controlling_rule} bold />
            <ResultRow label="Deemed Resident" value={result.is_deemed_resident ? 'Yes' : 'No'} />
            {result.rnor_test_result && <ResultRow label="RNOR Test" value={result.rnor_test_result} />}
          </ResultCard>
        </div>
      )}
    </div>
  );
}

// ─── 2. DTAA EXPLORER ─────────────────────────────────────────

function DTAAExplorerTab() {
  const toast = useToast();
  const [form, setForm] = useState<DTAARequest>({ country: '', income_type: null });

  const mutation = useMutation<DTAAResponse, Error, DTAARequest>({
    mutationFn: (data) => nriApi.dtaa(data),
    onSuccess: () => toast.success('DTAA details loaded'),
    onError: (err) => toast.error(`DTAA lookup failed: ${err.message}`),
  });

  const incomeTypeOptions: SelectOption[] = [
    { value: '', label: 'All income types' },
    { value: 'dividends', label: 'Dividends' },
    { value: 'interest', label: 'Interest' },
    { value: 'royalty', label: 'Royalty' },
    { value: 'fees_for_technical_services', label: 'Fees for Technical Services' },
    { value: 'capital_gains', label: 'Capital Gains' },
  ];

  const result = mutation.data;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <SelectInput
          label="Treaty Partner Country"
          value={form.country}
          onChange={(v) => setForm((f) => ({ ...f, country: v }))}
          options={COUNTRY_OPTIONS}
        />
        <SelectInput
          label="Income Type (optional)"
          value={form.income_type || ''}
          onChange={(v) => setForm((f) => ({ ...f, income_type: (v || null) as DTAARequest['income_type'] }))}
          options={incomeTypeOptions}
        />
      </div>

      <Button
        variant="gradient"
        loading={mutation.isPending}
        icon={<Landmark className="w-4 h-4" />}
        onClick={() => mutation.mutate(form)}
        disabled={!form.country}
        className="hover-lift"
      >
        Explore Treaty
      </Button>

      {mutation.isError && (
        <div className="p-4 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
          {getErrorMessage(mutation.error, 'DTAA lookup failed')}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <h3 className="text-lg font-bold text-textura-text">
              {result.country} ({result.country_code})
            </h3>
            {result.ca_review_required && <PendingBadge />}
          </div>

          <ResultCard title="Treaty Rates">
            <DataTable>
              <DataTableHeader>
                <DataTableHead>Income Type</DataTableHead>
                <DataTableHead>Rate</DataTableHead>
                <DataTableHead>Notes</DataTableHead>
              </DataTableHeader>
              <DataTableBody>
                {result.rates.map((rate, i) => (
                  <DataTableRow key={i}>
                    <DataTableCell className="capitalize">{rate.income_type.replace(/_/g, ' ')}</DataTableCell>
                    <DataTableCell>
                      {rate.rate == null && rate.rate_percent == null ? (
                        <PendingBadge text="Rate pending" />
                      ) : (
                        rateValue(rate.rate_percent ?? rate.rate ?? null)
                      )}
                    </DataTableCell>
                    <DataTableCell className="text-textura-muted">{rate.notes || '--'}</DataTableCell>
                  </DataTableRow>
                ))}
              </DataTableBody>
            </DataTable>
          </ResultCard>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ResultCard title="Documentation Requirements">
              <div className="space-y-2">
                <ResultRow label="TRC Required" value={result.trc_required ? 'Yes' : 'No'} />
                <ResultRow label="Form 10F Required" value={result.form_10f_required ? 'Yes' : 'No'} />
                {result.documentation.length > 0 && (
                  <ul className="mt-3 space-y-1">
                    {result.documentation.map((doc, i) => (
                      <li key={i} className="text-xs text-textura-dim flex items-start gap-2">
                        <FileCheck className="w-3.5 h-3.5 text-textura-accent shrink-0 mt-0.5" />
                        {doc}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </ResultCard>
            <ResultCard title="Tie-Breaker & Source">
              <p className="text-sm text-textura-dim mb-2">{result.residency_tie_breaker || '--'}</p>
              {result.source_citation && (
                <p className="text-xs text-textura-muted">Source: {result.source_citation}</p>
              )}
            </ResultCard>
          </div>

          {result.notes && (
            <div className="p-4 bg-warning/10 border border-warning/20 rounded-xl text-sm text-warning">
              {result.notes}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── 3. SECTION 195 / REPATRIATION ────────────────────────────

function Section195Tab() {
  const toast = useToast();
  const [form, setForm] = useState<Section195Request>({
    payment_type: 'interest',
    payment_amount: 0,
    payee_is_nri: true,
    payee_country: '',
    payee_has_trc: false,
    payee_has_pan: true,
    property_is_long_term: false,
    has_form_15e_certificate: false,
  });

  const mutation = useMutation<Section195Response, Error, Section195Request>({
    mutationFn: (data) => nriApi.section195(data),
    onSuccess: () => toast.success('Section 195 computation completed'),
    onError: (err) => toast.error(`Computation failed: ${err.message}`),
  });

  const update = <K extends keyof Section195Request>(field: K, value: Section195Request[K]) =>
    setForm((f) => ({ ...f, [field]: value }));

  const result = mutation.data;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <SelectInput
          label="Payment Type"
          value={form.payment_type}
          onChange={(v) => update('payment_type', v as Section195Request['payment_type'])}
          options={SECTION_195_PAYMENT_OPTIONS}
        />
        <NumInput label="Payment Amount" value={form.payment_amount} onChange={(v) => update('payment_amount', v)} prefix="₹" />
        <Field label="Payee Country">
          <Input
            type="text"
            value={form.payee_country}
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('payee_country', e.target.value)}
            placeholder="e.g. USA"
          />
        </Field>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <CheckInput label="Payee is NRI" checked={form.payee_is_nri} onChange={(v) => update('payee_is_nri', v)} />
        <CheckInput label="Payee has PAN" checked={form.payee_has_pan} onChange={(v) => update('payee_has_pan', v)} />
        <CheckInput label="Payee has TRC" checked={form.payee_has_trc} onChange={(v) => update('payee_has_trc', v)} />
        <CheckInput label="Form 15E certificate" checked={form.has_form_15e_certificate} onChange={(v) => update('has_form_15e_certificate', v)} />
      </div>

      {form.payment_type === 'property_sale' && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 rounded-xl border border-textura-line-subtle bg-textura-panel-raised/30">
          <NumInput
            label="Property Sale Consideration"
            value={form.property_sale_consideration ?? ''}
            onChange={(v) => update('property_sale_consideration', v)}
            prefix="₹"
          />
          <CheckInput label="Long-term capital asset" checked={form.property_is_long_term} onChange={(v) => update('property_is_long_term', v)} />
          <NumInput
            label="Certificate Rate (if any)"
            value={form.certificate_rate ?? ''}
            onChange={(v) => update('certificate_rate', v)}
            placeholder="0.10"
          />
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <NumInput label="Domestic Rate Override" value={form.domestic_rate_override ?? ''} onChange={(v) => update('domestic_rate_override', v)} placeholder="0.10" />
        <NumInput label="Treaty Rate Override" value={form.treaty_rate_override ?? ''} onChange={(v) => update('treaty_rate_override', v)} placeholder="0.10" />
      </div>

      <Button
        variant="gradient"
        loading={mutation.isPending}
        icon={<Calculator className="w-4 h-4" />}
        onClick={() => mutation.mutate(form)}
        disabled={!form.payment_amount}
        className="hover-lift"
      >
        Compute TDS
      </Button>

      {mutation.isError && (
        <div className="p-4 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
          {getErrorMessage(mutation.error, 'Computation failed')}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard title="Applicable Rate" value={rateValue(result.applicable_rate)} icon={Landmark} variant="accent" />
            <StatCard title="TDS Amount" value={formatCurrency(result.tds_amount)} icon={Briefcase} variant="warm" />
            <StatCard title="Regime" value={result.applicable_regime} icon={FileCheck} variant="success" />
          </div>

          <ResultCard title="Form 15CA / 15CB Workflow">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className={`p-3 rounded-xl border text-sm ${result.form_15ca_required ? statusColor('active') : statusColor('muted')}`}>
                Form 15CA {result.form_15ca_required ? 'Required' : 'Not required'}
              </div>
              <div className={`p-3 rounded-xl border text-sm ${result.form_15cb_required ? statusColor('active') : statusColor('muted')}`}>
                Form 15CB {result.form_15cb_required ? 'Required' : 'Not required'}
              </div>
              <div className={`p-3 rounded-xl border text-sm ${result.form_15e_applied ? statusColor('active') : statusColor('muted')}`}>
                Form 15E {result.form_15e_applied ? 'Applied' : 'Not applied'}
              </div>
            </div>
            {result.repatriation_note && (
              <p className="mt-4 text-sm text-textura-dim">{result.repatriation_note}</p>
            )}
          </ResultCard>

          {result.notes && (
            <div className="p-4 bg-warning/10 border border-warning/20 rounded-xl text-sm text-warning">
              {result.notes}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── 4. FOREIGN TAX CREDIT ────────────────────────────────────

function FTCTab() {
  const toast = useToast();
  const [form, setForm] = useState<FTCRequest>({
    assessment_year: getAssessmentYears()[0],
    total_income: 0,
    total_indian_tax: 0,
    countries: [{ country: '', foreign_income: 0, foreign_tax_paid: 0, has_dtaa: false }],
  });

  const mutation = useMutation<FTCResponse, Error, FTCRequest>({
    mutationFn: (data) => nriApi.ftc(data),
    onSuccess: () => toast.success('FTC computed successfully'),
    onError: (err) => toast.error(`FTC computation failed: ${err.message}`),
  });

  const updateCountry = (index: number, field: keyof FTCCreditCountryInput, value: FTCCreditCountryInput[keyof FTCCreditCountryInput]) => {
    const next = [...form.countries];
    next[index] = { ...next[index], [field]: value };
    setForm((f) => ({ ...f, countries: next }));
  };

  const addCountry = () =>
    setForm((f) => ({ ...f, countries: [...f.countries, { country: '', foreign_income: 0, foreign_tax_paid: 0, has_dtaa: false }] }));

  const removeCountry = (index: number) =>
    setForm((f) => ({ ...f, countries: f.countries.filter((_, i) => i !== index) }));

  const result = mutation.data;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <SelectInput
          label="Assessment Year"
          value={form.assessment_year}
          onChange={(v) => setForm((f) => ({ ...f, assessment_year: v }))}
          options={getAssessmentYears().map((y) => ({ value: y, label: y }))}
        />
        <NumInput label="Total Income" value={form.total_income} onChange={(v) => setForm((f) => ({ ...f, total_income: v }))} prefix="₹" />
        <NumInput label="Total Indian Tax" value={form.total_indian_tax} onChange={(v) => setForm((f) => ({ ...f, total_indian_tax: v }))} prefix="₹" />
      </div>

      <Field label="Form 67 Filing Date (optional)">
        <Input
          type="date"
          value={form.filing_date || ''}
          onChange={(e: ChangeEvent<HTMLInputElement>) =>
            setForm((f) => ({ ...f, filing_date: e.target.value || null }))
          }
        />
      </Field>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="block text-sm font-medium text-textura-dim">Per-Country Details</label>
          <Button variant="ghost" size="sm" icon={<Plus className="w-3.5 h-3.5" />} onClick={addCountry}>
            Add Country
          </Button>
        </div>
        {form.countries.map((c, i) => (
          <Panel key={i} className="p-4">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 items-end">
              <Field label="Country">
                <Input
                  type="text"
                  value={c.country}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => updateCountry(i, 'country', e.target.value)}
                  placeholder="e.g. USA"
                />
              </Field>
              <NumInput
                label="Foreign Income"
                value={c.foreign_income}
                onChange={(v) => updateCountry(i, 'foreign_income', v)}
                prefix="₹"
              />
              <NumInput
                label="Foreign Tax Paid"
                value={c.foreign_tax_paid}
                onChange={(v) => updateCountry(i, 'foreign_tax_paid', v)}
                prefix="₹"
              />
              <div className="flex items-center justify-between gap-3">
                <CheckInput label="Has DTAA" checked={c.has_dtaa} onChange={(v) => updateCountry(i, 'has_dtaa', v)} />
                {form.countries.length > 1 && (
                  <button
                    onClick={() => removeCountry(i)}
                    className="p-2 text-danger hover:bg-danger/10 rounded-lg transition-colors"
                    aria-label="Remove country"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </Panel>
        ))}
      </div>

      <Button
        variant="gradient"
        loading={mutation.isPending}
        icon={<Calculator className="w-4 h-4" />}
        onClick={() => mutation.mutate(form)}
        disabled={form.countries.some((c) => !c.country)}
        className="hover-lift"
      >
        Compute FTC
      </Button>

      {mutation.isError && (
        <div className="p-4 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
          {getErrorMessage(mutation.error, 'FTC computation failed')}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard title="Allowable Credit" value={formatCurrency(result.total_allowable_credit)} icon={Landmark} variant="accent" />
            <StatCard title="Disallowance" value={formatCurrency(result.total_disallowance)} icon={AlertCircle} variant="danger" />
            <StatCard title="Avg Indian Tax Rate" value={rateValue(result.average_indian_tax_rate)} icon={Briefcase} variant="warm" />
          </div>

          <ResultCard title="Form 67 Filing">
            <ResultRow label="Due Date" value={formatDate(result.form_67_due_date)} />
            <ResultRow label="Filed on Time" value={result.is_filed_on_time ? 'Yes' : 'No'} />
          </ResultCard>

          <ResultCard title="Per-Country Credit">
            <DataTable>
              <DataTableHeader>
                <DataTableHead>Country</DataTableHead>
                <DataTableHead>Foreign Income</DataTableHead>
                <DataTableHead>Foreign Tax</DataTableHead>
                <DataTableHead>Allowable Credit</DataTableHead>
                <DataTableHead>Method</DataTableHead>
              </DataTableHeader>
              <DataTableBody>
                {result.per_country.map((c, i) => (
                  <DataTableRow key={i}>
                    <DataTableCell>{c.country}</DataTableCell>
                    <DataTableCell>{formatCurrency(c.foreign_income)}</DataTableCell>
                    <DataTableCell>{formatCurrency(c.foreign_tax_paid)}</DataTableCell>
                    <DataTableCell className="text-textura-accent">{formatCurrency(c.allowable_credit)}</DataTableCell>
                    <DataTableCell className="text-textura-muted">{c.method}</DataTableCell>
                  </DataTableRow>
                ))}
              </DataTableBody>
            </DataTable>
          </ResultCard>

          {result.notes && (
            <div className="p-4 bg-warning/10 border border-warning/20 rounded-xl text-sm text-warning">
              {result.notes}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── 5. CUSTOMS TARIFF ────────────────────────────────────────

function CustomsTariffTab() {
  const toast = useToast();
  const [form, setForm] = useState<CustomsTariffRequest>({
    hsn_code: '',
    cif_value: 0,
  });

  const mutation = useMutation<CustomsTariffResponse, Error, CustomsTariffRequest>({
    mutationFn: (data) => nriApi.customsTariff(data),
    onSuccess: () => toast.success('Customs landed cost computed'),
    onError: (err) => toast.error(`Customs computation failed: ${err.message}`),
  });

  const update = <K extends keyof CustomsTariffRequest>(field: K, value: CustomsTariffRequest[K]) =>
    setForm((f) => ({ ...f, [field]: value }));

  const result = mutation.data;
  const hasMissingRates = result && (result.missing_rates.length > 0 || result.total_landed_cost == null);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Field label="HSN Code">
          <Input
            type="text"
            value={form.hsn_code}
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('hsn_code', e.target.value)}
            placeholder="e.g. 8471.30"
          />
        </Field>
        <NumInput label="CIF Value" value={form.cif_value} onChange={(v) => update('cif_value', v)} prefix="₹" />
        <Field label="Country of Origin">
          <Input
            type="text"
            value={form.country_of_origin || ''}
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('country_of_origin', e.target.value || null)}
            placeholder="e.g. China"
          />
        </Field>
        <Field label="FTA Code (optional)">
          <Input
            type="text"
            value={form.fta_code || ''}
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('fta_code', e.target.value || null)}
            placeholder="e.g. ASEAN"
          />
        </Field>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <NumInput label="BCD Rate Override" value={form.bcd_rate_override ?? ''} onChange={(v) => update('bcd_rate_override', v)} placeholder="0.10" />
        <NumInput label="SWS Rate Override" value={form.sws_rate_override ?? ''} onChange={(v) => update('sws_rate_override', v)} placeholder="0.10" />
        <NumInput label="Cess Rate Override" value={form.cess_rate_override ?? ''} onChange={(v) => update('cess_rate_override', v)} placeholder="0.10" />
        <NumInput label="IGST Rate Override" value={form.igst_rate_override ?? ''} onChange={(v) => update('igst_rate_override', v)} placeholder="0.18" />
      </div>

      <label className="flex items-center gap-2.5 text-sm text-textura-muted cursor-pointer select-none">
        <input
          type="checkbox"
          checked={!!form.demo}
          onChange={(e: ChangeEvent<HTMLInputElement>) => update('demo', e.target.checked)}
          className="w-4 h-4 accent-textura-accent"
        />
        <span>Demo data</span>
        <span className="text-xs text-textura-dim">— fill illustrative sample rates when real Customs Tariff rates aren't sourced</span>
      </label>

      <Button
        variant="gradient"
        loading={mutation.isPending}
        icon={<Ship className="w-4 h-4" />}
        onClick={() => mutation.mutate(form)}
        disabled={!form.hsn_code || !form.cif_value}
        className="hover-lift"
      >
        Compute Landed Cost
      </Button>

      {mutation.isError && (
        <div className="p-4 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
          {getErrorMessage(mutation.error, 'Customs computation failed')}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {result.is_sample_data && (
            <div className="flex items-center gap-3 p-4 bg-textura-warm/10 border border-textura-warm/30 rounded-xl text-sm text-textura-warm animate-fade-in">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <div>
                <p className="font-medium">Sample data — illustrative only</p>
                <p className="text-xs opacity-80">These figures use demo rates, not authoritative Customs Tariff values. Not for filing or client advice.</p>
              </div>
            </div>
          )}
          {hasMissingRates && (
            <div className="flex items-center gap-3 p-4 bg-warning/10 border border-warning/20 rounded-xl text-sm text-warning">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <div>
                <p className="font-medium">Rates pending</p>
                <p className="text-xs opacity-80">
                  {result.missing_rates.length > 0 ? result.missing_rates.join(', ') : 'Some tariff rates are not available yet.'}
                </p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard title="Import Duty Total" value={formatCurrency(result.import_duty_total)} icon={Ship} variant="accent" />
            <StatCard title="Total Landed Cost" value={formatCurrency(result.total_landed_cost)} icon={Briefcase} variant="warm" />
            <StatCard title="FTA Applied" value={result.fta_applied ? 'Yes' : 'No'} icon={CheckCircle2} variant="success" />
          </div>

          <ResultCard title="Duty Breakdown">
            <ResultRow label="BCD" value={`${rateValue(result.bcd_rate)} ${result.bcd_amount != null ? formatCurrency(result.bcd_amount) : ''}`} />
            <ResultRow label="SWS" value={`${rateValue(result.sws_rate)} ${result.sws_amount != null ? formatCurrency(result.sws_amount) : ''}`} />
            <ResultRow label="Cess" value={`${rateValue(result.cess_rate)} ${result.cess_amount != null ? formatCurrency(result.cess_amount) : ''}`} />
            <ResultRow label="IGST" value={`${rateValue(result.igst_rate)} ${result.igst_amount != null ? formatCurrency(result.igst_amount) : ''}`} />
          </ResultCard>

          {result.notes && (
            <div className="p-4 bg-warning/10 border border-warning/20 rounded-xl text-sm text-warning">
              {result.notes}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── 6. GST CROSS-BORDER ──────────────────────────────────────

function CrossBorderGSTTab() {
  const toast = useToast();
  const [form, setForm] = useState<CrossBorderGSTRequest>({
    taxable_value: 0,
    transaction_type: 'import',
    supply_type: 'services',
    has_lut: false,
    is_b2b: false,
    recipient_country: '',
    import_duty_amount: 0,
  });

  const mutation = useMutation<CrossBorderGSTResponse, Error, CrossBorderGSTRequest>({
    mutationFn: (data) => nriApi.gstCrossBorder(data),
    onSuccess: () => toast.success('Cross-border GST computed'),
    onError: (err) => toast.error(`GST computation failed: ${err.message}`),
  });

  const update = <K extends keyof CrossBorderGSTRequest>(field: K, value: CrossBorderGSTRequest[K]) =>
    setForm((f) => ({ ...f, [field]: value }));

  const result = mutation.data;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SelectInput
          label="Transaction Type"
          value={form.transaction_type}
          onChange={(v) => update('transaction_type', v as CrossBorderGSTRequest['transaction_type'])}
          options={CB_GST_TRANSACTION_OPTIONS}
        />
        <SelectInput
          label="Supply Type"
          value={form.supply_type}
          onChange={(v) => update('supply_type', v as CrossBorderGSTRequest['supply_type'])}
          options={[
            { value: 'goods', label: 'Goods' },
            { value: 'services', label: 'Services' },
          ]}
        />
        <NumInput label="Taxable Value" value={form.taxable_value} onChange={(v) => update('taxable_value', v)} prefix="₹" />
        <NumInput label="GST Rate Override" value={form.gst_rate ?? ''} onChange={(v) => update('gst_rate', v)} placeholder="0.18" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Field label="HSN/SAC (optional)">
          <Input
            type="text"
            value={form.hsn_sac || ''}
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('hsn_sac', e.target.value || null)}
            placeholder="e.g. 9983"
          />
        </Field>
        <Field label="Recipient Country">
          <Input
            type="text"
            value={form.recipient_country}
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('recipient_country', e.target.value)}
            placeholder="e.g. USA"
          />
        </Field>
        <Field label="Place of Supply (optional)">
          <Input
            type="text"
            value={form.place_of_supply || ''}
            onChange={(e: ChangeEvent<HTMLInputElement>) => update('place_of_supply', e.target.value || null)}
            placeholder="e.g. Karnataka"
          />
        </Field>
        <NumInput
          label="Import Duty Amount"
          value={form.import_duty_amount}
          onChange={(v) => update('import_duty_amount', v)}
          prefix="₹"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <CheckInput label="Has LUT (for exports)" checked={form.has_lut} onChange={(v) => update('has_lut', v)} />
        <CheckInput label="Is B2B" checked={form.is_b2b} onChange={(v) => update('is_b2b', v)} />
      </div>

      <Button
        variant="gradient"
        loading={mutation.isPending}
        icon={<Calculator className="w-4 h-4" />}
        onClick={() => mutation.mutate(form)}
        disabled={!form.taxable_value}
        className="hover-lift"
      >
        Compute GST
      </Button>

      {mutation.isError && (
        <div className="p-4 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
          {getErrorMessage(mutation.error, 'GST computation failed')}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard title="Total GST" value={formatCurrency(result.total_gst)} icon={Briefcase} variant="accent" />
            <StatCard title="Invoice Total" value={formatCurrency(result.invoice_total)} icon={CheckCircle2} variant="warm" />
            <StatCard title="Place of Supply" value={result.place_of_supply || '--'} icon={Globe} variant="success" />
          </div>

          <ResultCard title="GST Breakdown">
            <ResultRow label="IGST" value={formatCurrency(result.igst)} />
            <ResultRow label="CGST" value={formatCurrency(result.cgst)} />
            <ResultRow label="SGST" value={formatCurrency(result.sgst)} />
            <div className="border-t border-textura-line-subtle my-2" />
            <ResultRow label="Export Zero-Rated" value={result.export_zero_rated ? 'Yes' : 'No'} />
            <ResultRow label="Reverse Charge" value={result.reverse_charge ? 'Yes' : 'No'} />
          </ResultCard>

          {result.notes && (
            <div className="p-4 bg-warning/10 border border-warning/20 rounded-xl text-sm text-warning">
              {result.notes}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── MAIN WORKSPACE ───────────────────────────────────────────

const TABS: { id: string; label: string; icon: LucideIcon; content: ReactNode }[] = [
  { id: 'residency', label: 'Residency', icon: Home, content: <ResidentialStatusTab /> },
  { id: 'dtaa', label: 'DTAA', icon: Landmark, content: <DTAAExplorerTab /> },
  { id: 'section195', label: '§195', icon: FileCheck, content: <Section195Tab /> },
  { id: 'ftc', label: 'FTC', icon: Briefcase, content: <FTCTab /> },
  { id: 'customs', label: 'Customs', icon: Ship, content: <CustomsTariffTab /> },
  { id: 'gst', label: 'GST', icon: Globe, content: <CrossBorderGSTTab /> },
];

export default function NriWorkspace() {
  return (
    <div className="space-y-6">
      <div className="animate-stagger-1">
        <h1 className="text-2xl font-bold text-textura-text">NRI Workspace</h1>
        <p className="text-sm text-textura-dim mt-1">
          Cross-border tax engines for NRIs, returning Indians, and global founders.
        </p>
      </div>

      <Panel className="p-1 animate-stagger-2">
        <Tabs tabs={TABS} defaultTab="residency" />
      </Panel>
    </div>
  );
}
