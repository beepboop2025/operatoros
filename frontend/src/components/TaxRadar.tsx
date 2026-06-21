import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { taxIntelApi, type TaxIntelItem } from '../api/client';
import { Panel, Button, Field, Input, Select, StatCard } from './textura';
import { formatDate } from '../utils/format';
import {
  Radio,
  Globe,
  TrendingUp,
  ExternalLink,
  Filter,
  AlertCircle,
} from 'lucide-react';

// World Tax Radar — live international-tax intelligence feed for NRIs and
// cross-border clients. Data is supplied by the social_scraper OperatorOS
// connector and surfaced through GET /api/tax-intel. Until the feed is
// populated the screen shows a clear empty state rather than fabricated items.

interface Filters {
  jurisdiction: string;
  topic: string;
  impact: string; // minimum NRI-impact score, '' = any
}

const IMPACT_OPTIONS = [
  { value: '', label: 'Any impact' },
  { value: '25', label: 'Low (25+)' },
  { value: '50', label: 'Medium (50+)' },
  { value: '75', label: 'High (75+)' },
];

function impactTone(score: number): { label: string; cls: string } {
  if (score >= 75) return { label: 'High', cls: 'bg-textura-warm/10 text-textura-warm border-textura-warm/20' };
  if (score >= 50) return { label: 'Medium', cls: 'bg-textura-accent/10 text-textura-accent border-textura-accent/20' };
  return { label: 'Low', cls: 'bg-textura-panel-raised text-textura-dim border-textura-line-subtle' };
}

function RadarCard({ item }: { item: TaxIntelItem }) {
  const tone = impactTone(item.nri_impact_score);
  return (
    <Panel interactive className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="text-base font-semibold text-textura-text leading-snug">{item.title}</h3>
          <div className="flex flex-wrap items-center gap-2 mt-2 text-xs">
            {item.jurisdiction && (
              <span className="inline-flex items-center gap-1 text-textura-muted">
                <Globe className="w-3.5 h-3.5" /> {item.jurisdiction}
              </span>
            )}
            {item.topic && (
              <span className="px-2 py-0.5 rounded-full bg-textura-panel-raised text-textura-dim border border-textura-line-subtle">
                {item.topic}
              </span>
            )}
            <span className={`px-2 py-0.5 rounded-full border ${tone.cls}`}>
              {tone.label} impact · {item.nri_impact_score}
            </span>
            {item.published_at && (
              <span className="text-textura-dim">{formatDate(item.published_at)}</span>
            )}
          </div>
        </div>
        {item.source_url && (
          <a
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 inline-flex items-center gap-1 text-xs text-textura-accent hover:underline"
          >
            Source <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
      </div>

      {item.summary && <p className="text-sm text-textura-muted mt-3 leading-relaxed">{item.summary}</p>}

      {item.matched_terms?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {item.matched_terms.slice(0, 8).map((term) => (
            <span
              key={term}
              className="px-1.5 py-0.5 rounded text-[11px] bg-textura-panel-raised text-textura-dim border border-textura-line-subtle"
            >
              {term}
            </span>
          ))}
        </div>
      )}
    </Panel>
  );
}

export default function TaxRadar() {
  const [filters, setFilters] = useState<Filters>({ jurisdiction: '', topic: '', impact: '' });
  const [applied, setApplied] = useState<Filters>(filters);

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['tax-intel', applied],
    queryFn: () =>
      taxIntelApi.list({
        jurisdiction: applied.jurisdiction || undefined,
        topic: applied.topic || undefined,
        impact: applied.impact ? Number(applied.impact) : undefined,
      }),
  });

  const items = data?.items ?? [];
  const highImpact = items.filter((i) => i.nri_impact_score >= 75).length;
  const jurisdictions = new Set(items.map((i) => i.jurisdiction).filter(Boolean)).size;

  return (
    <div className="space-y-6">
      <div className="animate-stagger-1">
        <h1 className="text-2xl font-bold text-textura-text flex items-center gap-2">
          <Radio className="w-6 h-6 text-textura-accent" /> World Tax Radar
        </h1>
        <p className="text-sm text-textura-dim mt-1">
          Live international tax &amp; trade developments relevant to NRIs and cross-border clients —
          DTAA changes, BEPS / Pillar Two, tariffs, FEMA and more.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 animate-stagger-2">
        <StatCard title="Feed items" value={items.length} icon={Radio} variant="accent" />
        <StatCard title="High impact" value={highImpact} icon={TrendingUp} variant="warm" />
        <StatCard title="Jurisdictions" value={jurisdictions} icon={Globe} variant="muted" />
      </div>

      <Panel className="p-4 animate-stagger-3">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Jurisdiction" className="flex-1 min-w-[160px]">
            <Input
              value={filters.jurisdiction}
              onChange={(e) => setFilters((f) => ({ ...f, jurisdiction: e.target.value }))}
              placeholder="e.g. UAE, USA, OECD"
            />
          </Field>
          <Field label="Topic" className="flex-1 min-w-[160px]">
            <Input
              value={filters.topic}
              onChange={(e) => setFilters((f) => ({ ...f, topic: e.target.value }))}
              placeholder="e.g. DTAA, Pillar Two, tariff"
            />
          </Field>
          <Field label="Min. impact" className="w-40">
            <Select
              value={filters.impact}
              onChange={(e) => setFilters((f) => ({ ...f, impact: e.target.value }))}
            >
              {IMPACT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
          </Field>
          <Button variant="gradient" icon={<Filter className="w-4 h-4" />} onClick={() => setApplied(filters)} loading={isFetching}>
            Apply
          </Button>
        </div>
      </Panel>

      {isLoading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Panel key={i} className="p-5">
              <div className="h-4 w-2/3 bg-textura-panel-raised rounded animate-pulse" />
              <div className="h-3 w-full bg-textura-panel-raised rounded animate-pulse mt-3" />
              <div className="h-3 w-5/6 bg-textura-panel-raised rounded animate-pulse mt-2" />
            </Panel>
          ))}
        </div>
      ) : isError ? (
        <Panel className="p-8 text-center">
          <AlertCircle className="w-8 h-8 text-textura-warm mx-auto mb-3" />
          <p className="text-textura-text font-medium">Couldn't load the radar feed</p>
          <p className="text-sm text-textura-dim mt-1">The tax-intel service may be unavailable.</p>
          <Button variant="ghost" className="mt-4" onClick={() => refetch()}>
            Retry
          </Button>
        </Panel>
      ) : items.length === 0 ? (
        <Panel className="p-10 text-center">
          <Radio className="w-8 h-8 text-textura-dim mx-auto mb-3" />
          <p className="text-textura-text font-medium">The radar is quiet</p>
          <p className="text-sm text-textura-dim mt-1 max-w-md mx-auto">
            No matching intelligence yet. Items appear here as the scraper feeds international
            tax &amp; trade developments into OperatorOS.
          </p>
        </Panel>
      ) : (
        <div className="space-y-3 animate-stagger-4">
          {items.map((item) => (
            <RadarCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
