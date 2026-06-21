import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { computeApi, getErrorMessage } from '../api/client';
import { useToast } from './Toast';
import { Panel, Button, Field, Input, Select } from './textura';
import type {
  IncomeTaxRequest,
  IncomeTaxDeductions,
  IncomeTaxResponse,
  TDSRequest,
  TDSResponse,
  GSTRequest,
  GSTResponse,
  CapitalGainsRequest,
  CapitalGainsResponse,
  InterestRequest,
  InterestResponse,
  HRARequest,
  HRAResponse,
} from '../api/client';
import {
  Calculator,
  ChevronDown,
  ChevronUp,
  Printer,
  CheckCircle2,
  IndianRupee,
  ReceiptText,
  FileBarChart,
  TrendingUp,
  Percent,
  Home,
  LucideIcon,
} from 'lucide-react';
import { formatCurrency, getAssessmentYears } from '../utils/format';
import { ReactNode } from 'react';

interface TabDef {
  id: string;
  label: string;
  icon: LucideIcon;
}

const TABS: TabDef[] = [
  { id: 'tax', label: 'Income Tax', icon: IndianRupee },
  { id: 'tds', label: 'TDS', icon: ReceiptText },
  { id: 'gst', label: 'GST', icon: FileBarChart },
  { id: 'capitalGains', label: 'Capital Gains', icon: TrendingUp },
  { id: 'interest', label: 'Interest', icon: Percent },
  { id: 'hra', label: 'HRA', icon: Home },
];

// ─── Number Input Helper ──────────────────────────────────────
interface NumInputProps {
  label: string;
  value: number | string;
  onChange: (value: number) => void;
  placeholder?: string;
  className?: string;
}

function NumInput({ label, value, onChange, placeholder, className = '' }: NumInputProps) {
  return (
    <Field label={label} className={className}>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-textura-muted text-sm">{'\u20B9'}</span>
        <Input
          type="number"
          value={value}
          onChange={(e) => onChange(Number(e.target.value) || 0)}
          placeholder={placeholder || '0'}
          className="pl-7"
        />
      </div>
    </Field>
  );
}

interface SelectOption {
  value: string | number;
  label: string;
}

interface SelectInputProps {
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  options: (string | SelectOption)[];
  className?: string;
}

function SelectInput({ label, value, onChange, options, className = '' }: SelectInputProps) {
  return (
    <Field label={label} className={className}>
      <Select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => {
          const optValue = typeof o === 'string' ? o : String(o.value);
          const optLabel = typeof o === 'string' ? o : o.label;
          return (
            <option key={optValue} value={optValue}>
              {optLabel}
            </option>
          );
        })}
      </Select>
    </Field>
  );
}

interface ResultCardProps {
  title: string;
  children: ReactNode;
  className?: string;
  gradient?: string;
}

function ResultCard({ title, children, className = '', gradient }: ResultCardProps) {
  return (
    <Panel className={`animate-fade-in overflow-hidden ${className}`} elevated={!!gradient}>
      <div className={`px-5 py-3 border-b border-textura-line-subtle ${gradient || 'bg-textura-panel-raised/40'}`}>
        <h4 className="font-semibold text-textura-text text-sm">{title}</h4>
      </div>
      <div className="p-5">{children}</div>
    </Panel>
  );
}

interface ResultRowProps {
  label: string;
  value: string;
  bold?: boolean;
  highlight?: boolean;
  indent?: boolean;
}

function ResultRow({ label, value, bold, highlight, indent }: ResultRowProps) {
  return (
    <div className={`flex justify-between py-1.5 ${bold ? 'font-semibold' : ''} ${highlight ? 'text-textura-accent bg-textura-accent/8 -mx-2 px-2 rounded-lg' : ''} ${indent ? 'pl-4' : ''}`}>
      <span className={`text-sm ${highlight ? 'text-textura-accent' : bold ? 'text-textura-text' : 'text-textura-dim'}`}>{label}</span>
      <span className={`text-sm font-mono ${highlight ? 'text-textura-accent' : bold ? 'text-textura-text' : 'text-textura-dim'}`}>{value}</span>
    </div>
  );
}

// ─── INCOME TAX TAB ───────────────────────────────────────────
function IncomeTaxTab() {
  const toast = useToast();
  const [showDeductions, setShowDeductions] = useState<boolean>(false);
  const [form, setForm] = useState<IncomeTaxRequest>({
    assessment_year: getAssessmentYears()[0],
    age_category: 'below_60',
    gross_salary: 0,
    income_hp: 0,
    business_income: 0,
    capital_gains_lt: 0,
    capital_gains_st: 0,
    other_income: 0,
    deductions: {
      section_80c: 0,
      section_80d: 0,
      section_80g: 0,
      section_80e: 0,
      section_80ccd_1b: 0,
      section_80tta: 0,
      hra_exempt: 0,
      lta_exempt: 0,
      standard_deduction: 50000,
      nps_employer: 0,
    },
  });

  const mutation = useMutation<IncomeTaxResponse, Error, IncomeTaxRequest>({
    mutationFn: (data) => computeApi.tax(data),
    onSuccess: () => toast.success('Tax computation completed successfully'),
    onError: (err) => toast.error(`Tax computation failed: ${err.message}`),
  });

  const update = (field: keyof Omit<IncomeTaxRequest, 'deductions'>, value: string | number) =>
    setForm((f) => ({ ...f, [field]: value }));

  const updateDed = (field: keyof IncomeTaxDeductions, value: number) =>
    setForm((f) => ({ ...f, deductions: { ...f.deductions, [field]: value } }));

  const handleCalculate = () => {
    mutation.mutate(form);
  };

  const result = mutation.data;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SelectInput
          label="Assessment Year"
          value={form.assessment_year}
          onChange={(v) => update('assessment_year', v)}
          options={getAssessmentYears()}
        />
        <SelectInput
          label="Age Category"
          value={form.age_category}
          onChange={(v) => update('age_category', v)}
          options={[
            { value: 'below_60', label: 'Below 60 years' },
            { value: '60_to_80', label: '60 to 80 years (Senior)' },
            { value: 'above_80', label: 'Above 80 years (Super Senior)' },
          ]}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <NumInput label="Gross Salary" value={form.gross_salary || ''} onChange={(v) => update('gross_salary', v)} />
        <NumInput label="House Property Income" value={form.income_hp || ''} onChange={(v) => update('income_hp', v)} />
        <NumInput label="Business Income" value={form.business_income || ''} onChange={(v) => update('business_income', v)} />
        <NumInput label="Long-Term Capital Gains" value={form.capital_gains_lt || ''} onChange={(v) => update('capital_gains_lt', v)} />
        <NumInput label="Short-Term Capital Gains" value={form.capital_gains_st || ''} onChange={(v) => update('capital_gains_st', v)} />
        <NumInput label="Other Income" value={form.other_income || ''} onChange={(v) => update('other_income', v)} />
      </div>

      {/* Deductions section */}
      <div className="card overflow-hidden">
        <button
          onClick={() => setShowDeductions(!showDeductions)}
          className="w-full flex items-center justify-between px-5 py-3 bg-textura-panel-raised/40 hover:bg-textura-panel-raised transition-colors"
        >
          <span className="text-sm font-semibold text-textura-text">Deductions</span>
          {showDeductions ? <ChevronUp className="w-4 h-4 text-textura-dim" /> : <ChevronDown className="w-4 h-4 text-textura-dim" />}
        </button>
        <div
          className={`overflow-hidden transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] ${showDeductions ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0'}`}
        >
          <div className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 border-t border-textura-line-subtle">
            <NumInput label="Section 80C" value={form.deductions.section_80c || ''} onChange={(v) => updateDed('section_80c', v)} />
            <NumInput label="Section 80D (Medical)" value={form.deductions.section_80d || ''} onChange={(v) => updateDed('section_80d', v)} />
            <NumInput label="Section 80G (Donations)" value={form.deductions.section_80g || ''} onChange={(v) => updateDed('section_80g', v)} />
            <NumInput label="Section 80E (Education Loan)" value={form.deductions.section_80e || ''} onChange={(v) => updateDed('section_80e', v)} />
            <NumInput label="Section 80CCD(1B) (NPS)" value={form.deductions.section_80ccd_1b || ''} onChange={(v) => updateDed('section_80ccd_1b', v)} />
            <NumInput label="Section 80TTA (Savings Interest)" value={form.deductions.section_80tta || ''} onChange={(v) => updateDed('section_80tta', v)} />
            <NumInput label="HRA Exemption" value={form.deductions.hra_exempt || ''} onChange={(v) => updateDed('hra_exempt', v)} />
            <NumInput label="LTA Exemption" value={form.deductions.lta_exempt || ''} onChange={(v) => updateDed('lta_exempt', v)} />
            <NumInput label="Standard Deduction" value={form.deductions.standard_deduction || ''} onChange={(v) => updateDed('standard_deduction', v)} />
            <NumInput label="NPS Employer Contribution" value={form.deductions.nps_employer || ''} onChange={(v) => updateDed('nps_employer', v)} />
          </div>
        </div>
      </div>

      <Button
        variant="gradient"
        loading={mutation.isPending}
        icon={<Calculator className="w-4 h-4" />}
        onClick={handleCalculate}
        className="hover-lift"
      >
        Calculate Tax
      </Button>

      {mutation.isError && (
        <div className="p-4 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
          {getErrorMessage(mutation.error, 'Calculation failed. Please check your inputs.')}
        </div>
      )}

      {/* Results: Old vs New Regime */}
      {result && (
        <div className="space-y-4 animate-float-in" id="tax-result">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-textura-text">Tax Computation Result</h3>
            <Button
              variant="ghost"
              size="sm"
              icon={<Printer className="w-4 h-4" />}
              onClick={() => window.print()}
              className="no-print"
            >
              Print
            </Button>
          </div>

          {result.recommended_regime && (
            <div className="flex items-center gap-2 p-3 bg-success/10 border border-success/20 rounded-xl animate-fade-in">
              <CheckCircle2 className="w-5 h-5 text-success shrink-0" />
              <p className="text-sm text-success">
                <strong>Recommended:</strong> {result.recommended_regime === 'old_regime' ? 'Old Regime' : 'New Regime'} saves you{' '}
                {formatCurrency(Math.abs((result.old_regime?.total_tax_liability || 0) - (result.new_regime?.total_tax_liability || 0)))}
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Old Regime */}
            <ResultCard
              title="Old Regime"
              className={result.recommended_regime === 'old_regime' ? 'ring-2 ring-success/50 shadow-lg shadow-success/10' : ''}
              gradient={result.recommended_regime === 'old_regime' ? 'bg-success/8' : undefined}
            >
              {result.old_regime ? (
                <div className="space-y-1">
                  <ResultRow label="Gross Total Income" value={formatCurrency(result.old_regime.gross_total_income)} />
                  <ResultRow label="Less: Deductions" value={formatCurrency(result.old_regime.total_deductions)} />
                  <ResultRow label="Taxable Income" value={formatCurrency(result.old_regime.taxable_income)} bold />
                  <div className="border-t border-textura-line-subtle my-2" />
                  <ResultRow label="Tax on Income" value={formatCurrency(result.old_regime.tax_on_income)} />
                  {result.old_regime.surcharge > 0 && <ResultRow label="Surcharge" value={formatCurrency(result.old_regime.surcharge)} />}
                  <ResultRow label="Health & Education Cess (4%)" value={formatCurrency(result.old_regime.education_cess)} />
                  <div className="border-t border-textura-line-subtle my-2" />
                  <ResultRow label="Total Tax Payable" value={formatCurrency(result.old_regime.total_tax_liability)} bold highlight />
                </div>
              ) : (
                <p className="text-sm text-textura-muted">Not computed</p>
              )}
            </ResultCard>

            {/* New Regime */}
            <ResultCard
              title="New Regime"
              className={result.recommended_regime === 'new_regime' ? 'ring-2 ring-success/50 shadow-lg shadow-success/10' : ''}
              gradient={result.recommended_regime === 'new_regime' ? 'bg-success/8' : undefined}
            >
              {result.new_regime ? (
                <div className="space-y-1">
                  <ResultRow label="Gross Total Income" value={formatCurrency(result.new_regime.gross_total_income)} />
                  <ResultRow label="Less: Deductions" value={formatCurrency(result.new_regime.total_deductions)} />
                  <ResultRow label="Taxable Income" value={formatCurrency(result.new_regime.taxable_income)} bold />
                  <div className="border-t border-textura-line-subtle my-2" />
                  <ResultRow label="Tax on Income" value={formatCurrency(result.new_regime.tax_on_income)} />
                  {result.new_regime.surcharge > 0 && <ResultRow label="Surcharge" value={formatCurrency(result.new_regime.surcharge)} />}
                  <ResultRow label="Health & Education Cess (4%)" value={formatCurrency(result.new_regime.education_cess)} />
                  <div className="border-t border-textura-line-subtle my-2" />
                  <ResultRow label="Total Tax Payable" value={formatCurrency(result.new_regime.total_tax_liability)} bold highlight />
                </div>
              ) : (
                <p className="text-sm text-textura-muted">Not computed</p>
              )}
            </ResultCard>
          </div>

          {/* Detailed working (expandable) */}
          {(result.old_regime?.slab_breakdown || result.new_regime?.slab_breakdown) && (
            <details className="card overflow-hidden">
              <summary className="px-5 py-3 cursor-pointer text-sm font-semibold text-textura-text hover:bg-textura-panel-raised/40 transition-colors flex items-center justify-between">
                View Detailed Computation Working
                <ChevronDown className="w-4 h-4 text-textura-muted" />
              </summary>
              <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-6 border-t border-textura-line-subtle">
                {result.old_regime?.slab_breakdown && (
                  <div>
                    <h5 className="text-xs font-semibold text-textura-muted uppercase mb-2">Old Regime Slabs</h5>
                    {result.old_regime.slab_breakdown.map((slab, i) => (
                      <ResultRow key={`old-${slab.slab || slab.range || i}`} label={slab.slab || slab.range || ''} value={formatCurrency(slab.tax)} />
                    ))}
                  </div>
                )}
                {result.new_regime?.slab_breakdown && (
                  <div>
                    <h5 className="text-xs font-semibold text-textura-muted uppercase mb-2">New Regime Slabs</h5>
                    {result.new_regime.slab_breakdown.map((slab, i) => (
                      <ResultRow key={`new-${slab.slab || slab.range || i}`} label={slab.slab || slab.range || ''} value={formatCurrency(slab.tax)} />
                    ))}
                  </div>
                )}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

// ─── TDS TAB ──────────────────────────────────────────────────
function TDSTab() {
  const toast = useToast();
  const [form, setForm] = useState<TDSRequest>({
    payment_type: 'salary',
    amount: 0,
    pan_available: true,
  });

  const mutation = useMutation<TDSResponse, Error, TDSRequest>({
    mutationFn: (data) => computeApi.tds(data),
    onSuccess: () => toast.success('TDS computed successfully'),
    onError: (err) => toast.error(`TDS computation failed: ${err.message}`),
  });

  const paymentTypes: SelectOption[] = [
    { value: 'salary', label: 'Salary (192)' },
    { value: 'professional_fees', label: 'Professional Fees (194J)' },
    { value: 'rent_land', label: 'Rent - Land/Building (194I(a))' },
    { value: 'rent_plant', label: 'Rent - Plant/Machinery (194I(b))' },
    { value: 'contract', label: 'Contractor (194C)' },
    { value: 'commission', label: 'Commission / Brokerage (194H)' },
    { value: 'interest', label: 'Interest (194A)' },
    { value: 'dividend', label: 'Dividend (194)' },
    { value: 'lottery', label: 'Lottery / Crossword (194B)' },
    { value: 'transfer_of_property', label: 'Transfer of Property (194IA)' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <SelectInput
          label="Payment Type"
          value={form.payment_type}
          onChange={(v) => setForm((f) => ({ ...f, payment_type: v }))}
          options={paymentTypes}
        />
        <NumInput label="Payment Amount" value={form.amount || ''} onChange={(v) => setForm((f) => ({ ...f, amount: v }))} />
        <div>
          <label className="block text-xs font-medium text-textura-dim mb-1">PAN Available</label>
          <div className="flex items-center gap-4 h-[38px]">
            <label className="flex items-center gap-2 text-sm text-textura-dim cursor-pointer">
              <input type="radio" checked={form.pan_available} onChange={() => setForm((f) => ({ ...f, pan_available: true }))} className="text-textura-accent accent-textura-accent" /> Yes
            </label>
            <label className="flex items-center gap-2 text-sm text-textura-dim cursor-pointer">
              <input type="radio" checked={!form.pan_available} onChange={() => setForm((f) => ({ ...f, pan_available: false }))} className="text-textura-accent accent-textura-accent" /> No
            </label>
          </div>
        </div>
      </div>

      <Button
        variant="gradient"
        loading={mutation.isPending}
        icon={<Calculator className="w-4 h-4" />}
        onClick={() => mutation.mutate(form)}
        disabled={!form.amount}
        className="hover-lift"
      >
        Calculate TDS
      </Button>

      {mutation.isError && (
        <div className="p-4 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
          {getErrorMessage(mutation.error, 'Calculation failed')}
        </div>
      )}

      {mutation.data && (
        <ResultCard title="TDS Calculation Result">
          <div className="space-y-1">
            <ResultRow label="Section" value={mutation.data.section || '--'} />
            <ResultRow label="TDS Rate" value={`${mutation.data.rate || 0}%`} />
            <ResultRow label="Payment Amount" value={formatCurrency(mutation.data.amount || form.amount)} />
            <div className="border-t border-textura-line-subtle my-2" />
            <ResultRow label="TDS Amount" value={formatCurrency(mutation.data.tds_amount)} bold highlight />
            {mutation.data.notes && (
              <div className="mt-3 p-3 bg-warning/10 border border-warning/20 rounded-xl text-xs text-warning">{mutation.data.notes}</div>
            )}
          </div>
        </ResultCard>
      )}
    </div>
  );
}

// ─── GST TAB ──────────────────────────────────────────────────
function GSTTab() {
  const toast = useToast();
  const [form, setForm] = useState<GSTRequest>({
    supply_type: 'goods',
    hsn_sac: '',
    place_of_supply: '',
    place_of_origin: '',
    taxable_value: 0,
    gst_rate: 18,
  });

  const mutation = useMutation<GSTResponse, Error, GSTRequest>({
    mutationFn: (data) => computeApi.gst(data),
    onSuccess: () => toast.success('GST computed successfully'),
    onError: (err) => toast.error(`GST computation failed: ${err.message}`),
  });

  const gstRates: number[] = [0, 0.25, 3, 5, 12, 18, 28];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <SelectInput
          label="Supply Type"
          value={form.supply_type}
          onChange={(v) => setForm((f) => ({ ...f, supply_type: v }))}
          options={[
            { value: 'goods', label: 'Goods' },
            { value: 'services', label: 'Services' },
          ]}
        />
        <Field label="HSN/SAC Code">
          <Input
            type="text"
            value={form.hsn_sac}
            onChange={(e) => setForm((f) => ({ ...f, hsn_sac: e.target.value }))}
            placeholder="e.g. 9983"
          />
        </Field>
        <Field label="Place of Origin (State)">
          <Input
            type="text"
            value={form.place_of_origin}
            onChange={(e) => setForm((f) => ({ ...f, place_of_origin: e.target.value }))}
            placeholder="e.g. Maharashtra"
          />
        </Field>
        <Field label="Place of Supply (State)">
          <Input
            type="text"
            value={form.place_of_supply}
            onChange={(e) => setForm((f) => ({ ...f, place_of_supply: e.target.value }))}
            placeholder="e.g. Karnataka"
          />
        </Field>
        <NumInput label="Taxable Value" value={form.taxable_value || ''} onChange={(v) => setForm((f) => ({ ...f, taxable_value: v }))} />
        <SelectInput
          label="GST Rate (%)"
          value={form.gst_rate}
          onChange={(v) => setForm((f) => ({ ...f, gst_rate: Number(v) }))}
          options={gstRates.map((r) => ({ value: r, label: `${r}%` }))}
        />
      </div>

      <Button
        variant="gradient"
        loading={mutation.isPending}
        icon={<Calculator className="w-4 h-4" />}
        onClick={() => mutation.mutate(form)}
        disabled={!form.taxable_value}
        className="hover-lift"
      >
        Calculate GST
      </Button>

      {mutation.isError && (
        <div className="p-4 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
          {getErrorMessage(mutation.error, 'Calculation failed')}
        </div>
      )}

      {mutation.data && (
        <ResultCard title="GST Calculation Result">
          <div className="space-y-1">
            <ResultRow label="Taxable Value" value={formatCurrency(mutation.data.taxable_value || form.taxable_value)} />
            <ResultRow label="Supply Type" value={mutation.data.is_interstate ? 'Interstate (IGST)' : 'Intrastate (CGST + SGST)'} />
            <div className="border-t border-textura-line-subtle my-2" />
            {mutation.data.cgst != null && <ResultRow label={`CGST @ ${(mutation.data.cgst_rate || form.gst_rate / 2)}%`} value={formatCurrency(mutation.data.cgst)} />}
            {mutation.data.sgst != null && <ResultRow label={`SGST @ ${(mutation.data.sgst_rate || form.gst_rate / 2)}%`} value={formatCurrency(mutation.data.sgst)} />}
            {mutation.data.igst != null && <ResultRow label={`IGST @ ${(mutation.data.igst_rate || form.gst_rate)}%`} value={formatCurrency(mutation.data.igst)} />}
            <div className="border-t border-textura-line-subtle my-2" />
            <ResultRow label="Total GST" value={formatCurrency(mutation.data.total_gst)} bold />
            <ResultRow label="Invoice Total" value={formatCurrency(mutation.data.total_amount || ((form.taxable_value) + (mutation.data.total_gst || 0)))} bold highlight />
          </div>
        </ResultCard>
      )}
    </div>
  );
}

// ─── CAPITAL GAINS TAB ────────────────────────────────────────
function CapitalGainsTab() {
  const toast = useToast();
  const [form, setForm] = useState<CapitalGainsRequest>({
    asset_type: 'equity_shares',
    purchase_date: '',
    sale_date: '',
    purchase_price: 0,
    sale_price: 0,
    improvement_cost: 0,
  });

  const mutation = useMutation<CapitalGainsResponse, Error, CapitalGainsRequest>({
    mutationFn: (data) => computeApi.capitalGains(data),
    onSuccess: () => toast.success('Capital gains computed successfully'),
    onError: (err) => toast.error(`Capital gains computation failed: ${err.message}`),
  });

  const assetTypes: SelectOption[] = [
    { value: 'equity_shares', label: 'Listed Equity Shares' },
    { value: 'equity_mf', label: 'Equity Mutual Funds' },
    { value: 'debt_mf', label: 'Debt Mutual Funds' },
    { value: 'property', label: 'Immovable Property' },
    { value: 'gold', label: 'Gold / Jewellery' },
    { value: 'bonds', label: 'Bonds / Debentures' },
    { value: 'other', label: 'Other Capital Assets' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <SelectInput
          label="Asset Type"
          value={form.asset_type}
          onChange={(v) => setForm((f) => ({ ...f, asset_type: v }))}
          options={assetTypes}
        />
        <Field label="Purchase Date">
          <Input
            type="date"
            value={form.purchase_date}
            onChange={(e) => setForm((f) => ({ ...f, purchase_date: e.target.value }))}
          />
        </Field>
        <Field label="Sale Date">
          <Input
            type="date"
            value={form.sale_date}
            onChange={(e) => setForm((f) => ({ ...f, sale_date: e.target.value }))}
          />
        </Field>
        <NumInput label="Purchase Price" value={form.purchase_price || ''} onChange={(v) => setForm((f) => ({ ...f, purchase_price: v }))} />
        <NumInput label="Sale Price" value={form.sale_price || ''} onChange={(v) => setForm((f) => ({ ...f, sale_price: v }))} />
        <NumInput label="Improvement Cost" value={form.improvement_cost || ''} onChange={(v) => setForm((f) => ({ ...f, improvement_cost: v }))} />
      </div>

      <Button
        variant="gradient"
        loading={mutation.isPending}
        icon={<Calculator className="w-4 h-4" />}
        onClick={() => mutation.mutate(form)}
        disabled={!form.sale_price}
        className="hover-lift"
      >
        Calculate Capital Gains
      </Button>

      {mutation.isError && (
        <div className="p-4 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
          {getErrorMessage(mutation.error, 'Calculation failed')}
        </div>
      )}

      {mutation.data && (
        <ResultCard title="Capital Gains Result">
          <div className="space-y-1">
            <ResultRow label="Gain Type" value={mutation.data.gain_type === 'ltcg' ? 'Long-Term Capital Gain' : 'Short-Term Capital Gain'} bold />
            <ResultRow label="Holding Period" value={mutation.data.holding_period || '--'} />
            <div className="border-t border-textura-line-subtle my-2" />
            <ResultRow label="Sale Consideration" value={formatCurrency(mutation.data.sale_price || form.sale_price)} />
            <ResultRow label="Cost of Acquisition" value={formatCurrency(mutation.data.purchase_price || form.purchase_price)} />
            {(mutation.data.indexed_cost ?? 0) > 0 && <ResultRow label="Indexed Cost of Acquisition" value={formatCurrency(mutation.data.indexed_cost)} />}
            {(mutation.data.improvement_cost ?? 0) > 0 && <ResultRow label="Cost of Improvement" value={formatCurrency(mutation.data.improvement_cost)} />}
            <div className="border-t border-textura-line-subtle my-2" />
            <ResultRow label="Capital Gain" value={formatCurrency(mutation.data.capital_gain)} bold />
            <ResultRow label="Tax Rate" value={`${mutation.data.tax_rate || 0}%`} />
            <ResultRow label="Tax Payable" value={formatCurrency(mutation.data.tax_amount)} bold highlight />

            {mutation.data.exemptions && mutation.data.exemptions.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-semibold text-textura-muted uppercase mb-1">Available Exemptions</p>
                {mutation.data.exemptions.map((ex) => (
                  <div key={ex} className="text-xs text-textura-dim py-0.5">- {ex}</div>
                ))}
              </div>
            )}
          </div>
        </ResultCard>
      )}
    </div>
  );
}

// ─── INTEREST TAB ─────────────────────────────────────────────
function InterestTab() {
  const toast = useToast();
  const [form, setForm] = useState<InterestRequest>({
    section: '234b',
    tax_liability: 0,
    tax_paid: 0,
    due_date: '',
    payment_date: '',
  });

  const mutation = useMutation<InterestResponse, Error, InterestRequest>({
    mutationFn: (data) => computeApi.interest(data),
    onSuccess: () => toast.success('Interest computed successfully'),
    onError: (err) => toast.error(`Interest computation failed: ${err.message}`),
  });

  const sections: SelectOption[] = [
    { value: '234a', label: '234A - Delay in Filing Return' },
    { value: '234b', label: '234B - Default in Advance Tax' },
    { value: '234c', label: '234C - Deferment of Advance Tax' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <SelectInput
          label="Interest Section"
          value={form.section}
          onChange={(v) => setForm((f) => ({ ...f, section: v }))}
          options={sections}
        />
        <NumInput label="Tax Liability" value={form.tax_liability || ''} onChange={(v) => setForm((f) => ({ ...f, tax_liability: v }))} />
        <NumInput label="Tax Paid (Advance Tax / TDS)" value={form.tax_paid || ''} onChange={(v) => setForm((f) => ({ ...f, tax_paid: v }))} />
        <Field label="Due Date">
          <Input
            type="date"
            value={form.due_date}
            onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))}
          />
        </Field>
        <Field label="Payment Date">
          <Input
            type="date"
            value={form.payment_date}
            onChange={(e) => setForm((f) => ({ ...f, payment_date: e.target.value }))}
          />
        </Field>
      </div>

      <Button
        variant="gradient"
        loading={mutation.isPending}
        icon={<Calculator className="w-4 h-4" />}
        onClick={() => mutation.mutate(form)}
        disabled={!form.tax_liability}
        className="hover-lift"
      >
        Calculate Interest
      </Button>

      {mutation.isError && (
        <div className="p-4 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
          {getErrorMessage(mutation.error, 'Calculation failed')}
        </div>
      )}

      {mutation.data && (
        <ResultCard title={`Interest u/s ${form.section.toUpperCase()} Result`}>
          <div className="space-y-1">
            <ResultRow label="Tax Liability" value={formatCurrency(mutation.data.tax_liability || form.tax_liability)} />
            <ResultRow label="Tax Paid" value={formatCurrency(mutation.data.tax_paid || form.tax_paid)} />
            <ResultRow label="Shortfall" value={formatCurrency(mutation.data.shortfall)} />
            <ResultRow label="Number of Months" value={`${mutation.data.months || 0} months`} />
            <ResultRow label="Rate" value={`${mutation.data.rate || 1}% per month`} />
            <div className="border-t border-textura-line-subtle my-2" />
            <ResultRow label="Interest Amount" value={formatCurrency(mutation.data.interest_amount)} bold highlight />

            {mutation.data.month_wise_breakdown && mutation.data.month_wise_breakdown.length > 0 && (
              <details className="mt-3">
                <summary className="text-xs font-semibold text-textura-muted cursor-pointer hover:text-textura-dim transition-colors">
                  Month-wise Breakdown
                </summary>
                <div className="mt-2 space-y-0.5">
                  {mutation.data.month_wise_breakdown.map((m, i) => (
                    <ResultRow key={`month-${m.month || m.period || i}`} label={m.month || m.period || ''} value={formatCurrency(m.interest)} indent />
                  ))}
                </div>
              </details>
            )}
          </div>
        </ResultCard>
      )}
    </div>
  );
}

// ─── HRA TAB ──────────────────────────────────────────────────
function HRATab() {
  const toast = useToast();
  const [form, setForm] = useState<HRARequest>({
    basic_salary: 0,
    da: 0,
    hra_received: 0,
    rent_paid: 0,
    is_metro: true,
  });

  const mutation = useMutation<HRAResponse, Error, HRARequest>({
    mutationFn: (data) => computeApi.hra(data),
    onSuccess: () => toast.success('HRA exemption computed successfully'),
    onError: (err) => toast.error(`HRA computation failed: ${err.message}`),
  });

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <NumInput label="Basic Salary (Annual)" value={form.basic_salary || ''} onChange={(v) => setForm((f) => ({ ...f, basic_salary: v }))} />
        <NumInput label="Dearness Allowance (DA)" value={form.da || ''} onChange={(v) => setForm((f) => ({ ...f, da: v }))} />
        <NumInput label="HRA Received (Annual)" value={form.hra_received || ''} onChange={(v) => setForm((f) => ({ ...f, hra_received: v }))} />
        <NumInput label="Rent Paid (Annual)" value={form.rent_paid || ''} onChange={(v) => setForm((f) => ({ ...f, rent_paid: v }))} />
        <div>
          <label className="block text-xs font-medium text-textura-dim mb-1">Metro City</label>
          <div className="flex items-center gap-4 h-[38px]">
            <label className="flex items-center gap-2 text-sm text-textura-dim cursor-pointer">
              <input type="radio" checked={form.is_metro} onChange={() => setForm((f) => ({ ...f, is_metro: true }))} className="accent-textura-accent" />
              Yes (Delhi/Mumbai/Kolkata/Chennai)
            </label>
            <label className="flex items-center gap-2 text-sm text-textura-dim cursor-pointer">
              <input type="radio" checked={!form.is_metro} onChange={() => setForm((f) => ({ ...f, is_metro: false }))} className="accent-textura-accent" />
              No
            </label>
          </div>
        </div>
      </div>

      <Button
        variant="gradient"
        loading={mutation.isPending}
        icon={<Calculator className="w-4 h-4" />}
        onClick={() => mutation.mutate(form)}
        disabled={!form.basic_salary}
        className="hover-lift"
      >
        Calculate HRA Exemption
      </Button>

      {mutation.isError && (
        <div className="p-4 bg-danger/10 border border-danger/20 rounded-xl text-sm text-danger animate-fade-in">
          {getErrorMessage(mutation.error, 'Calculation failed')}
        </div>
      )}

      {mutation.data && (
        <ResultCard title="HRA Exemption Calculation">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-textura-muted uppercase mb-2">Least of the following is exempt:</p>
            <ResultRow
              label="(a) Actual HRA Received"
              value={formatCurrency(mutation.data.actual_hra || form.hra_received)}
            />
            <ResultRow
              label={`(b) ${form.is_metro ? '50%' : '40%'} of (Basic + DA)`}
              value={formatCurrency(mutation.data.percent_of_salary)}
            />
            <ResultRow
              label="(c) Rent Paid - 10% of (Basic + DA)"
              value={formatCurrency(mutation.data.rent_minus_10_percent)}
            />
            <div className="border-t border-textura-line-subtle my-2" />
            <ResultRow label="HRA Exemption (Least of above)" value={formatCurrency(mutation.data.exemption_amount)} bold highlight />
            <ResultRow label="Taxable HRA" value={formatCurrency(mutation.data.taxable_hra)} />
          </div>
        </ResultCard>
      )}
    </div>
  );
}

// ─── MAIN COMPONENT ───────────────────────────────────────────
export default function TaxComputer() {
  const [activeTab, setActiveTab] = useState<string>('tax');

  const tabComponents: Record<string, React.FC> = {
    tax: IncomeTaxTab,
    tds: TDSTab,
    gst: GSTTab,
    capitalGains: CapitalGainsTab,
    interest: InterestTab,
    hra: HRATab,
  };

  const ActiveComponent = tabComponents[activeTab];

  return (
    <div className="space-y-6">
      <div className="animate-stagger-1">
        <h1 className="text-2xl font-bold text-textura-text">Tax Calculator</h1>
        <p className="text-sm text-textura-dim mt-1">Compute taxes, TDS, GST, capital gains, interest, and HRA</p>
      </div>

      {/* Tab bar */}
      <div className="card p-1.5 flex flex-wrap gap-1 animate-stagger-2">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`relative flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200
                ${isActive
                  ? 'bg-textura-accent/15 text-textura-accent shadow-lg shadow-textura-accent/10'
                  : 'text-textura-muted hover:bg-textura-panel-raised hover:text-textura-text'
                }`}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
              {isActive && (
                <div className="absolute bottom-0 left-2 right-2 h-0.5 bg-gradient-to-r from-textura-warm to-textura-accent rounded-full" style={{ animation: 'tab-underline 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards', transformOrigin: 'left' }} />
              )}
            </button>
          );
        })}
      </div>

      {/* Active tab content */}
      <div key={activeTab} className="card p-6 tab-content-enter">
        <ActiveComponent />
      </div>
    </div>
  );
}
