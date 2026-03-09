import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { computeApi } from '../api/client';
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
  Loader2,
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
import { formatCurrency, formatIndianNumber, getAssessmentYears } from '../utils/format';
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
    <div className={className}>
      <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">{'\u20B9'}</span>
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(Number(e.target.value) || 0)}
          placeholder={placeholder || '0'}
          className="w-full pl-7 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
        />
      </div>
    </div>
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
    <div className={className}>
      <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
      >
        {options.map((o) => {
          const optValue = typeof o === 'string' ? o : String(o.value);
          const optLabel = typeof o === 'string' ? o : o.label;
          return (
            <option key={optValue} value={optValue}>
              {optLabel}
            </option>
          );
        })}
      </select>
    </div>
  );
}

interface ResultCardProps {
  title: string;
  children: ReactNode;
  className?: string;
}

function ResultCard({ title, children, className = '' }: ResultCardProps) {
  return (
    <div className={`bg-white rounded-xl border border-slate-200 overflow-hidden ${className}`}>
      <div className="px-5 py-3 bg-slate-50 border-b border-slate-200">
        <h4 className="font-semibold text-slate-700 text-sm">{title}</h4>
      </div>
      <div className="p-5">{children}</div>
    </div>
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
    <div className={`flex justify-between py-1.5 ${bold ? 'font-semibold' : ''} ${highlight ? 'text-blue-700 bg-blue-50 -mx-2 px-2 rounded' : ''} ${indent ? 'pl-4' : ''}`}>
      <span className={`text-sm ${highlight ? 'text-blue-700' : bold ? 'text-slate-800' : 'text-slate-600'}`}>{label}</span>
      <span className={`text-sm font-mono ${highlight ? 'text-blue-700' : bold ? 'text-slate-800' : 'text-slate-700'}`}>{value}</span>
    </div>
  );
}

// ─── INCOME TAX TAB ───────────────────────────────────────────
function IncomeTaxTab() {
  const [showDeductions, setShowDeductions] = useState<boolean>(false);
  const [form, setForm] = useState<IncomeTaxRequest>({
    assessment_year: getAssessmentYears()[0],
    age_category: 'below_60',
    gross_salary: 0,
    house_property_income: 0,
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
      hra: 0,
      lta: 0,
      standard_deduction: 50000,
      nps_employer: 0,
    },
  });

  const mutation = useMutation<IncomeTaxResponse, Error, IncomeTaxRequest>({
    mutationFn: computeApi.tax,
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
    <div className="space-y-6">
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
        <NumInput label="House Property Income" value={form.house_property_income || ''} onChange={(v) => update('house_property_income', v)} />
        <NumInput label="Business Income" value={form.business_income || ''} onChange={(v) => update('business_income', v)} />
        <NumInput label="Long-Term Capital Gains" value={form.capital_gains_lt || ''} onChange={(v) => update('capital_gains_lt', v)} />
        <NumInput label="Short-Term Capital Gains" value={form.capital_gains_st || ''} onChange={(v) => update('capital_gains_st', v)} />
        <NumInput label="Other Income" value={form.other_income || ''} onChange={(v) => update('other_income', v)} />
      </div>

      {/* Deductions section */}
      <div className="border border-slate-200 rounded-xl overflow-hidden">
        <button
          onClick={() => setShowDeductions(!showDeductions)}
          className="w-full flex items-center justify-between px-5 py-3 bg-slate-50 hover:bg-slate-100 transition-colors"
        >
          <span className="text-sm font-semibold text-slate-700">Deductions</span>
          {showDeductions ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
        </button>
        {showDeductions && (
          <div className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <NumInput label="Section 80C" value={form.deductions.section_80c || ''} onChange={(v) => updateDed('section_80c', v)} />
            <NumInput label="Section 80D (Medical)" value={form.deductions.section_80d || ''} onChange={(v) => updateDed('section_80d', v)} />
            <NumInput label="Section 80G (Donations)" value={form.deductions.section_80g || ''} onChange={(v) => updateDed('section_80g', v)} />
            <NumInput label="Section 80E (Education Loan)" value={form.deductions.section_80e || ''} onChange={(v) => updateDed('section_80e', v)} />
            <NumInput label="Section 80CCD(1B) (NPS)" value={form.deductions.section_80ccd_1b || ''} onChange={(v) => updateDed('section_80ccd_1b', v)} />
            <NumInput label="Section 80TTA (Savings Interest)" value={form.deductions.section_80tta || ''} onChange={(v) => updateDed('section_80tta', v)} />
            <NumInput label="HRA Exemption" value={form.deductions.hra || ''} onChange={(v) => updateDed('hra', v)} />
            <NumInput label="LTA Exemption" value={form.deductions.lta || ''} onChange={(v) => updateDed('lta', v)} />
            <NumInput label="Standard Deduction" value={form.deductions.standard_deduction || ''} onChange={(v) => updateDed('standard_deduction', v)} />
            <NumInput label="NPS Employer Contribution" value={form.deductions.nps_employer || ''} onChange={(v) => updateDed('nps_employer', v)} />
          </div>
        )}
      </div>

      <button
        onClick={handleCalculate}
        disabled={mutation.isPending}
        className="px-6 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-medium rounded-lg flex items-center gap-2"
      >
        {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calculator className="w-4 h-4" />}
        Calculate Tax
      </button>

      {mutation.isError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {(mutation.error as { response?: { data?: { detail?: string } } } & Error)?.response?.data?.detail || 'Calculation failed. Please check your inputs.'}
        </div>
      )}

      {/* Results: Old vs New Regime */}
      {result && (
        <div className="space-y-4" id="tax-result">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-slate-800">Tax Computation Result</h3>
            <button
              onClick={() => window.print()}
              className="no-print inline-flex items-center gap-2 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 rounded-lg border border-slate-200"
            >
              <Printer className="w-4 h-4" /> Print
            </button>
          </div>

          {result.recommended_regime && (
            <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-green-600 shrink-0" />
              <p className="text-sm text-green-700">
                <strong>Recommended:</strong> {result.recommended_regime === 'old' ? 'Old Regime' : 'New Regime'} saves you{' '}
                {formatCurrency(Math.abs((result.old_regime?.total_tax || 0) - (result.new_regime?.total_tax || 0)))}
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Old Regime */}
            <ResultCard title="Old Regime" className={result.recommended_regime === 'old' ? 'ring-2 ring-green-500' : ''}>
              {result.old_regime ? (
                <div className="space-y-1">
                  <ResultRow label="Gross Total Income" value={formatCurrency(result.old_regime.gross_total_income)} />
                  <ResultRow label="Less: Deductions" value={formatCurrency(result.old_regime.total_deductions)} />
                  <ResultRow label="Taxable Income" value={formatCurrency(result.old_regime.taxable_income)} bold />
                  <div className="border-t border-slate-100 my-2" />
                  <ResultRow label="Tax on Income" value={formatCurrency(result.old_regime.tax_on_income)} />
                  {result.old_regime.surcharge > 0 && <ResultRow label="Surcharge" value={formatCurrency(result.old_regime.surcharge)} />}
                  <ResultRow label="Health & Education Cess (4%)" value={formatCurrency(result.old_regime.cess)} />
                  <div className="border-t border-slate-200 my-2" />
                  <ResultRow label="Total Tax Payable" value={formatCurrency(result.old_regime.total_tax)} bold highlight />
                </div>
              ) : (
                <p className="text-sm text-slate-400">Not computed</p>
              )}
            </ResultCard>

            {/* New Regime */}
            <ResultCard title="New Regime" className={result.recommended_regime === 'new' ? 'ring-2 ring-green-500' : ''}>
              {result.new_regime ? (
                <div className="space-y-1">
                  <ResultRow label="Gross Total Income" value={formatCurrency(result.new_regime.gross_total_income)} />
                  <ResultRow label="Less: Deductions" value={formatCurrency(result.new_regime.total_deductions)} />
                  <ResultRow label="Taxable Income" value={formatCurrency(result.new_regime.taxable_income)} bold />
                  <div className="border-t border-slate-100 my-2" />
                  <ResultRow label="Tax on Income" value={formatCurrency(result.new_regime.tax_on_income)} />
                  {result.new_regime.surcharge > 0 && <ResultRow label="Surcharge" value={formatCurrency(result.new_regime.surcharge)} />}
                  <ResultRow label="Health & Education Cess (4%)" value={formatCurrency(result.new_regime.cess)} />
                  <div className="border-t border-slate-200 my-2" />
                  <ResultRow label="Total Tax Payable" value={formatCurrency(result.new_regime.total_tax)} bold highlight />
                </div>
              ) : (
                <p className="text-sm text-slate-400">Not computed</p>
              )}
            </ResultCard>
          </div>

          {/* Detailed working (expandable) */}
          {(result.old_regime?.slab_breakdown || result.new_regime?.slab_breakdown) && (
            <details className="bg-white border border-slate-200 rounded-xl">
              <summary className="px-5 py-3 cursor-pointer text-sm font-semibold text-slate-700 hover:bg-slate-50">
                View Detailed Computation Working
              </summary>
              <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-6 border-t border-slate-200">
                {result.old_regime?.slab_breakdown && (
                  <div>
                    <h5 className="text-xs font-semibold text-slate-500 uppercase mb-2">Old Regime Slabs</h5>
                    {result.old_regime.slab_breakdown.map((slab, i) => (
                      <ResultRow key={i} label={slab.slab || slab.range || ''} value={formatCurrency(slab.tax)} />
                    ))}
                  </div>
                )}
                {result.new_regime?.slab_breakdown && (
                  <div>
                    <h5 className="text-xs font-semibold text-slate-500 uppercase mb-2">New Regime Slabs</h5>
                    {result.new_regime.slab_breakdown.map((slab, i) => (
                      <ResultRow key={i} label={slab.slab || slab.range || ''} value={formatCurrency(slab.tax)} />
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
  const [form, setForm] = useState<TDSRequest>({
    payment_type: 'salary',
    amount: 0,
    pan_available: true,
  });

  const mutation = useMutation<TDSResponse, Error, TDSRequest>({ mutationFn: computeApi.tds });

  const paymentTypes: SelectOption[] = [
    { value: 'salary', label: 'Salary (192)' },
    { value: 'interest_bank', label: 'Interest on Securities (193)' },
    { value: 'dividend', label: 'Dividend (194)' },
    { value: 'interest_other', label: 'Interest Other (194A)' },
    { value: 'lottery', label: 'Lottery / Crossword (194B)' },
    { value: 'contractor', label: 'Contractor (194C)' },
    { value: 'insurance_commission', label: 'Insurance Commission (194D)' },
    { value: 'nsc_interest', label: 'NSC Interest (194EE)' },
    { value: 'rent', label: 'Rent (194I)' },
    { value: 'professional_fees', label: 'Professional Fees (194J)' },
    { value: 'property_sale', label: 'Property Sale (194IA)' },
    { value: 'rent_by_individual', label: 'Rent by Individual (194IB)' },
    { value: 'ecommerce', label: 'E-Commerce (194-O)' },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <SelectInput
          label="Payment Type"
          value={form.payment_type}
          onChange={(v) => setForm((f) => ({ ...f, payment_type: v }))}
          options={paymentTypes}
        />
        <NumInput label="Payment Amount" value={form.amount || ''} onChange={(v) => setForm((f) => ({ ...f, amount: v }))} />
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">PAN Available</label>
          <div className="flex items-center gap-4 h-[38px]">
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" checked={form.pan_available} onChange={() => setForm((f) => ({ ...f, pan_available: true }))} className="text-blue-500" /> Yes
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" checked={!form.pan_available} onChange={() => setForm((f) => ({ ...f, pan_available: false }))} className="text-blue-500" /> No
            </label>
          </div>
        </div>
      </div>

      <button
        onClick={() => mutation.mutate(form)}
        disabled={mutation.isPending || !form.amount}
        className="px-6 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-medium rounded-lg flex items-center gap-2"
      >
        {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calculator className="w-4 h-4" />}
        Calculate TDS
      </button>

      {mutation.isError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {(mutation.error as { response?: { data?: { detail?: string } } } & Error)?.response?.data?.detail || 'Calculation failed'}
        </div>
      )}

      {mutation.data && (
        <ResultCard title="TDS Calculation Result">
          <div className="space-y-1">
            <ResultRow label="Section" value={mutation.data.section || '--'} />
            <ResultRow label="TDS Rate" value={`${mutation.data.rate || 0}%`} />
            <ResultRow label="Payment Amount" value={formatCurrency(mutation.data.amount || form.amount)} />
            <div className="border-t border-slate-200 my-2" />
            <ResultRow label="TDS Amount" value={formatCurrency(mutation.data.tds_amount)} bold highlight />
            {mutation.data.notes && (
              <div className="mt-3 p-3 bg-amber-50 rounded-lg text-xs text-amber-700">{mutation.data.notes}</div>
            )}
          </div>
        </ResultCard>
      )}
    </div>
  );
}

// ─── GST TAB ──────────────────────────────────────────────────
function GSTTab() {
  const [form, setForm] = useState<GSTRequest>({
    supply_type: 'goods',
    hsn_sac: '',
    place_of_supply: '',
    place_of_origin: '',
    taxable_value: 0,
    rate: 18,
  });

  const mutation = useMutation<GSTResponse, Error, GSTRequest>({ mutationFn: computeApi.gst });

  const gstRates: number[] = [0, 0.25, 3, 5, 12, 18, 28];

  return (
    <div className="space-y-6">
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
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">HSN/SAC Code</label>
          <input
            type="text"
            value={form.hsn_sac}
            onChange={(e) => setForm((f) => ({ ...f, hsn_sac: e.target.value }))}
            placeholder="e.g. 9983"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Place of Origin (State)</label>
          <input
            type="text"
            value={form.place_of_origin}
            onChange={(e) => setForm((f) => ({ ...f, place_of_origin: e.target.value }))}
            placeholder="e.g. Maharashtra"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Place of Supply (State)</label>
          <input
            type="text"
            value={form.place_of_supply}
            onChange={(e) => setForm((f) => ({ ...f, place_of_supply: e.target.value }))}
            placeholder="e.g. Karnataka"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>
        <NumInput label="Taxable Value" value={form.taxable_value || ''} onChange={(v) => setForm((f) => ({ ...f, taxable_value: v }))} />
        <SelectInput
          label="GST Rate (%)"
          value={form.rate}
          onChange={(v) => setForm((f) => ({ ...f, rate: Number(v) }))}
          options={gstRates.map((r) => ({ value: r, label: `${r}%` }))}
        />
      </div>

      <button
        onClick={() => mutation.mutate(form)}
        disabled={mutation.isPending || !form.taxable_value}
        className="px-6 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-medium rounded-lg flex items-center gap-2"
      >
        {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calculator className="w-4 h-4" />}
        Calculate GST
      </button>

      {mutation.isError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {(mutation.error as { response?: { data?: { detail?: string } } } & Error)?.response?.data?.detail || 'Calculation failed'}
        </div>
      )}

      {mutation.data && (
        <ResultCard title="GST Calculation Result">
          <div className="space-y-1">
            <ResultRow label="Taxable Value" value={formatCurrency(mutation.data.taxable_value || form.taxable_value)} />
            <ResultRow label="Supply Type" value={mutation.data.is_interstate ? 'Interstate (IGST)' : 'Intrastate (CGST + SGST)'} />
            <div className="border-t border-slate-100 my-2" />
            {mutation.data.cgst != null && <ResultRow label={`CGST @ ${(mutation.data.cgst_rate || form.rate / 2)}%`} value={formatCurrency(mutation.data.cgst)} />}
            {mutation.data.sgst != null && <ResultRow label={`SGST @ ${(mutation.data.sgst_rate || form.rate / 2)}%`} value={formatCurrency(mutation.data.sgst)} />}
            {mutation.data.igst != null && <ResultRow label={`IGST @ ${(mutation.data.igst_rate || form.rate)}%`} value={formatCurrency(mutation.data.igst)} />}
            <div className="border-t border-slate-200 my-2" />
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
  const [form, setForm] = useState<CapitalGainsRequest>({
    asset_type: 'equity_shares',
    purchase_date: '',
    sale_date: '',
    purchase_price: 0,
    sale_price: 0,
    improvement_cost: 0,
  });

  const mutation = useMutation<CapitalGainsResponse, Error, CapitalGainsRequest>({ mutationFn: computeApi.capitalGains });

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
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <SelectInput
          label="Asset Type"
          value={form.asset_type}
          onChange={(v) => setForm((f) => ({ ...f, asset_type: v }))}
          options={assetTypes}
        />
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Purchase Date</label>
          <input
            type="date"
            value={form.purchase_date}
            onChange={(e) => setForm((f) => ({ ...f, purchase_date: e.target.value }))}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Sale Date</label>
          <input
            type="date"
            value={form.sale_date}
            onChange={(e) => setForm((f) => ({ ...f, sale_date: e.target.value }))}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>
        <NumInput label="Purchase Price" value={form.purchase_price || ''} onChange={(v) => setForm((f) => ({ ...f, purchase_price: v }))} />
        <NumInput label="Sale Price" value={form.sale_price || ''} onChange={(v) => setForm((f) => ({ ...f, sale_price: v }))} />
        <NumInput label="Improvement Cost" value={form.improvement_cost || ''} onChange={(v) => setForm((f) => ({ ...f, improvement_cost: v }))} />
      </div>

      <button
        onClick={() => mutation.mutate(form)}
        disabled={mutation.isPending || !form.sale_price}
        className="px-6 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-medium rounded-lg flex items-center gap-2"
      >
        {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calculator className="w-4 h-4" />}
        Calculate Capital Gains
      </button>

      {mutation.isError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {(mutation.error as { response?: { data?: { detail?: string } } } & Error)?.response?.data?.detail || 'Calculation failed'}
        </div>
      )}

      {mutation.data && (
        <ResultCard title="Capital Gains Result">
          <div className="space-y-1">
            <ResultRow label="Gain Type" value={mutation.data.gain_type === 'ltcg' ? 'Long-Term Capital Gain' : 'Short-Term Capital Gain'} bold />
            <ResultRow label="Holding Period" value={mutation.data.holding_period || '--'} />
            <div className="border-t border-slate-100 my-2" />
            <ResultRow label="Sale Consideration" value={formatCurrency(mutation.data.sale_price || form.sale_price)} />
            <ResultRow label="Cost of Acquisition" value={formatCurrency(mutation.data.purchase_price || form.purchase_price)} />
            {(mutation.data.indexed_cost ?? 0) > 0 && <ResultRow label="Indexed Cost of Acquisition" value={formatCurrency(mutation.data.indexed_cost)} />}
            {(mutation.data.improvement_cost ?? 0) > 0 && <ResultRow label="Cost of Improvement" value={formatCurrency(mutation.data.improvement_cost)} />}
            <div className="border-t border-slate-200 my-2" />
            <ResultRow label="Capital Gain" value={formatCurrency(mutation.data.capital_gain)} bold />
            <ResultRow label="Tax Rate" value={`${mutation.data.tax_rate || 0}%`} />
            <ResultRow label="Tax Payable" value={formatCurrency(mutation.data.tax_amount)} bold highlight />

            {mutation.data.exemptions && mutation.data.exemptions.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Available Exemptions</p>
                {mutation.data.exemptions.map((ex, i) => (
                  <div key={i} className="text-xs text-slate-600 py-0.5">- {ex}</div>
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
  const [form, setForm] = useState<InterestRequest>({
    section: '234b',
    tax_liability: 0,
    tax_paid: 0,
    due_date: '',
    payment_date: '',
  });

  const mutation = useMutation<InterestResponse, Error, InterestRequest>({ mutationFn: computeApi.interest });

  const sections: SelectOption[] = [
    { value: '234a', label: '234A - Delay in Filing Return' },
    { value: '234b', label: '234B - Default in Advance Tax' },
    { value: '234c', label: '234C - Deferment of Advance Tax' },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <SelectInput
          label="Interest Section"
          value={form.section}
          onChange={(v) => setForm((f) => ({ ...f, section: v }))}
          options={sections}
        />
        <NumInput label="Tax Liability" value={form.tax_liability || ''} onChange={(v) => setForm((f) => ({ ...f, tax_liability: v }))} />
        <NumInput label="Tax Paid (Advance Tax / TDS)" value={form.tax_paid || ''} onChange={(v) => setForm((f) => ({ ...f, tax_paid: v }))} />
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Due Date</label>
          <input
            type="date"
            value={form.due_date}
            onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Payment Date</label>
          <input
            type="date"
            value={form.payment_date}
            onChange={(e) => setForm((f) => ({ ...f, payment_date: e.target.value }))}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>
      </div>

      <button
        onClick={() => mutation.mutate(form)}
        disabled={mutation.isPending || !form.tax_liability}
        className="px-6 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-medium rounded-lg flex items-center gap-2"
      >
        {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calculator className="w-4 h-4" />}
        Calculate Interest
      </button>

      {mutation.isError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {(mutation.error as { response?: { data?: { detail?: string } } } & Error)?.response?.data?.detail || 'Calculation failed'}
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
            <div className="border-t border-slate-200 my-2" />
            <ResultRow label="Interest Amount" value={formatCurrency(mutation.data.interest_amount)} bold highlight />

            {mutation.data.month_wise_breakdown && mutation.data.month_wise_breakdown.length > 0 && (
              <details className="mt-3">
                <summary className="text-xs font-semibold text-slate-500 cursor-pointer hover:text-slate-700">
                  Month-wise Breakdown
                </summary>
                <div className="mt-2 space-y-0.5">
                  {mutation.data.month_wise_breakdown.map((m, i) => (
                    <ResultRow key={i} label={m.month || m.period || ''} value={formatCurrency(m.interest)} indent />
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
  const [form, setForm] = useState<HRARequest>({
    basic_salary: 0,
    da: 0,
    hra_received: 0,
    rent_paid: 0,
    is_metro: true,
  });

  const mutation = useMutation<HRAResponse, Error, HRARequest>({ mutationFn: computeApi.hra });

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <NumInput label="Basic Salary (Annual)" value={form.basic_salary || ''} onChange={(v) => setForm((f) => ({ ...f, basic_salary: v }))} />
        <NumInput label="Dearness Allowance (DA)" value={form.da || ''} onChange={(v) => setForm((f) => ({ ...f, da: v }))} />
        <NumInput label="HRA Received (Annual)" value={form.hra_received || ''} onChange={(v) => setForm((f) => ({ ...f, hra_received: v }))} />
        <NumInput label="Rent Paid (Annual)" value={form.rent_paid || ''} onChange={(v) => setForm((f) => ({ ...f, rent_paid: v }))} />
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Metro City</label>
          <div className="flex items-center gap-4 h-[38px]">
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" checked={form.is_metro} onChange={() => setForm((f) => ({ ...f, is_metro: true }))} className="text-blue-500" />
              Yes (Delhi/Mumbai/Kolkata/Chennai)
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" checked={!form.is_metro} onChange={() => setForm((f) => ({ ...f, is_metro: false }))} className="text-blue-500" />
              No
            </label>
          </div>
        </div>
      </div>

      <button
        onClick={() => mutation.mutate(form)}
        disabled={mutation.isPending || !form.basic_salary}
        className="px-6 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-medium rounded-lg flex items-center gap-2"
      >
        {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calculator className="w-4 h-4" />}
        Calculate HRA Exemption
      </button>

      {mutation.isError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {(mutation.error as { response?: { data?: { detail?: string } } } & Error)?.response?.data?.detail || 'Calculation failed'}
        </div>
      )}

      {mutation.data && (
        <ResultCard title="HRA Exemption Calculation">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Least of the following is exempt:</p>
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
            <div className="border-t border-slate-200 my-2" />
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
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Tax Calculator</h1>
        <p className="text-sm text-slate-500 mt-1">Compute taxes, TDS, GST, capital gains, interest, and HRA</p>
      </div>

      {/* Tab bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-1.5 flex flex-wrap gap-1">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors
                ${activeTab === tab.id
                  ? 'bg-blue-500 text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-100'
                }`}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Active tab content */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <ActiveComponent />
      </div>
    </div>
  );
}
