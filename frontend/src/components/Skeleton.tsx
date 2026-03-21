import { ReactNode } from 'react';

// ── Base skeleton block ──────────────────────────────────────────────────────

interface SkeletonBlockProps {
  className?: string;
  style?: React.CSSProperties;
}

export function SkeletonBlock({ className = '', style }: SkeletonBlockProps) {
  return <div className={`skeleton ${className}`} style={style} />;
}

// ── Skeleton line (text placeholder) ─────────────────────────────────────────

interface SkeletonLineProps {
  width?: string;
  height?: string;
  className?: string;
}

export function SkeletonLine({ width = '100%', height = '14px', className = '' }: SkeletonLineProps) {
  return <div className={`skeleton rounded-md ${className}`} style={{ width, height }} />;
}

// ── Skeleton card ────────────────────────────────────────────────────────────

export function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`card rounded-xl p-5 ${className}`}>
      <div className="flex items-start justify-between">
        <div className="space-y-3 flex-1">
          <SkeletonLine width="60%" height="12px" />
          <SkeletonLine width="35%" height="24px" />
          <SkeletonLine width="45%" height="10px" />
        </div>
        <SkeletonBlock className="w-10 h-10 rounded-xl flex-shrink-0" />
      </div>
    </div>
  );
}

// ── Skeleton table rows ──────────────────────────────────────────────────────

export function SkeletonTableRows({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 px-5 py-3.5"
          style={{ animationDelay: `${i * 80}ms` }}
        >
          {Array.from({ length: cols }).map((_, j) => (
            <SkeletonLine
              key={j}
              width={j === 0 ? '30%' : j === cols - 1 ? '15%' : '20%'}
              height="14px"
            />
          ))}
        </div>
      ))}
    </>
  );
}

// ── Skeleton chat messages ───────────────────────────────────────────────────

export function SkeletonChat({ messages = 3 }: { messages?: number }) {
  return (
    <div className="space-y-4 p-4">
      {Array.from({ length: messages }).map((_, i) => {
        const isUser = i % 2 === 0;
        return (
          <div key={i} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[70%] space-y-2 ${isUser ? 'items-end' : 'items-start'}`}>
              <SkeletonBlock
                className="rounded-xl"
                style={{
                  width: isUser ? 180 : 260,
                  height: isUser ? 40 : 60,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Dashboard skeleton ───────────────────────────────────────────────────────

export function SkeletonDashboard() {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="space-y-2">
        <SkeletonLine width="180px" height="24px" />
        <SkeletonLine width="280px" height="14px" />
      </div>
      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
      {/* Quick actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonBlock key={i} className="rounded-xl" style={{ height: 72 }} />
        ))}
      </div>
      {/* Two-column */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card rounded-xl p-5 space-y-3">
          <SkeletonLine width="40%" height="16px" />
          <SkeletonTableRows rows={4} cols={3} />
        </div>
        <div className="card rounded-xl p-5 space-y-3">
          <SkeletonLine width="40%" height="16px" />
          <SkeletonTableRows rows={4} cols={3} />
        </div>
      </div>
    </div>
  );
}

// ── Form skeleton (for TaxComputer etc.) ─────────────────────────────────────

export function SkeletonForm({ fields = 6 }: { fields?: number }) {
  return (
    <div className="space-y-4 animate-fade-in">
      {/* Tab bar */}
      <div className="flex gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonBlock key={i} className="rounded-lg" style={{ width: 90, height: 36 }} />
        ))}
      </div>
      {/* Fields */}
      <div className="card rounded-xl p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: fields }).map((_, i) => (
            <div key={i} className="space-y-2">
              <SkeletonLine width="80px" height="10px" />
              <SkeletonBlock className="rounded-xl" style={{ height: 40 }} />
            </div>
          ))}
        </div>
        <SkeletonBlock className="rounded-xl mt-4" style={{ width: 140, height: 42 }} />
      </div>
    </div>
  );
}

// ── Document list skeleton ───────────────────────────────────────────────────

export function SkeletonDocumentList({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-4 animate-fade-in">
      {/* Upload zone */}
      <SkeletonBlock className="rounded-xl" style={{ height: 100 }} />
      {/* Filter bar */}
      <div className="flex gap-3">
        <SkeletonBlock className="rounded-xl flex-1" style={{ height: 40 }} />
        <SkeletonBlock className="rounded-xl" style={{ width: 120, height: 40 }} />
      </div>
      {/* Rows */}
      <div className="card rounded-xl overflow-hidden">
        <SkeletonTableRows rows={rows} cols={5} />
      </div>
    </div>
  );
}
