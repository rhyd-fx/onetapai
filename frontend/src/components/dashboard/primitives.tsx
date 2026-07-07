"use client";

import { Lock } from 'lucide-react';
import { ReactNode } from 'react';

export function Panel({
  children,
  className = '',
  glow,
}: {
  children: ReactNode;
  className?: string;
  glow?: 'red' | 'blue';
}) {
  const glowCls = glow === 'red' ? 'hover:glow-red' : glow === 'blue' ? 'hover:glow-blue' : '';
  return (
    <div className={`glass rounded-2xl transition-shadow duration-300 ${glowCls} ${className}`}>
      {children}
    </div>
  );
}

export function SectionTitle({ children, accent = 'red' }: { children: ReactNode; accent?: 'red' | 'blue' }) {
  const bar = accent === 'red' ? 'bg-brand-red' : 'bg-brand-blue';
  return (
    <div className="mb-4 flex items-center gap-3">
      <span className={`h-4 w-1 rounded-full ${bar}`} />
      <h2 className="text-sm font-bold uppercase tracking-[0.18em] text-white/80">{children}</h2>
    </div>
  );
}

export function StatTile({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: 'red' | 'blue';
}) {
  const valCls = accent === 'red' ? 'text-brand-red' : accent === 'blue' ? 'text-brand-blue' : 'text-white';
  return (
    <div className="rounded-xl border border-line/60 bg-ink-800/40 px-3 py-3">
      <div className="text-[10px] font-medium uppercase tracking-widest text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${valCls}`}>{value}</div>
      {sub && <div className="text-[11px] text-muted">{sub}</div>}
    </div>
  );
}

/** "Data Incoming" locked telemetry tile with shimmer skeleton. */
export function LockedTile({ label }: { label: string }) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-line/60 bg-ink-800/40 px-3 py-4">
      <div className="flex items-center justify-between">
        <div className="text-[10px] font-medium uppercase tracking-widest text-muted">{label}</div>
        <Lock size={12} className="text-muted/70" />
      </div>
      <div className="skeleton-shimmer mt-3 h-6 w-2/3 rounded" />
      <div className="skeleton-shimmer mt-2 h-2 w-1/2 rounded" />
      <div className="mt-3 text-[9px] font-semibold uppercase tracking-widest text-brand-blue/70">
        Data Incoming
      </div>
    </div>
  );
}
