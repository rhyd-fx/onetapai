"use client";

import { TrendingUp, TrendingDown, Minus, Crosshair, Shield, Zap, Target, ArrowUpRight, Flame } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { ProgressResponse, PillarKey, OtrMatch } from '@/lib/api';
import { Panel, SectionTitle } from './primitives';

const PILLAR_META: Record<PillarKey, { label: string; icon: typeof Crosshair; blurb: string }> = {
  damage:    { label: 'Damage',    icon: Crosshair, blurb: 'Damage dealt per round vs your lobby' },
  survival:  { label: 'Survival',  icon: Shield,    blurb: 'Rounds survived vs your lobby' },
  impact:    { label: 'Impact',    icon: Zap,       blurb: 'Opening duels won + multikill rounds' },
  precision: { label: 'Precision', icon: Target,    blurb: 'Headshot rate vs your lobby' },
};

function trendBadge(trend?: string) {
  if (trend === 'improving')
    return { icon: TrendingUp, cls: 'text-emerald-400 border-emerald-500/25 bg-emerald-500/[0.07]', label: 'Improving' };
  if (trend === 'declining')
    return { icon: TrendingDown, cls: 'text-amber-400 border-amber-500/25 bg-amber-500/[0.07]', label: 'Dipping' };
  return { icon: Minus, cls: 'text-muted border-white/10 bg-white/[0.03]', label: 'Holding steady' };
}

/** OTR color: below/at/above lobby average. */
function otrColor(otr: number) {
  if (otr >= 55) return 'text-emerald-400';
  if (otr >= 45) return 'text-white';
  return 'text-amber-400';
}

const OtrTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const m: OtrMatch = payload[0].payload;
  return (
    <div className="border border-line/80 p-2.5 rounded-xl shadow-2xl bg-ink-900/95 backdrop-blur-md text-xs min-w-[130px]">
      <div className="flex justify-between gap-3 mb-1">
        <span className="font-bold text-white">{m.map}</span>
        <span className={m.won ? 'text-emerald-400' : 'text-brand-red'}>{m.won ? 'W' : 'L'}</span>
      </div>
      <div className="text-muted">OTR <span className="text-white font-bold tabular-nums">{m.otr}</span></div>
      <div className="text-muted">ACS <span className="text-white/80 tabular-nums">{Math.round(m.acs)}</span></div>
    </div>
  );
};

export default function ProgressHome({ progress, riotId }: { progress: ProgressResponse; riotId: string }) {
  if (!progress.available || progress.otr == null) {
    return (
      <Panel className="p-8 text-center">
        <SectionTitle>Your Progress</SectionTitle>
        <p className="text-sm text-muted leading-relaxed max-w-md mx-auto">
          {progress.reason || 'Play a Competitive match and re-sync to start tracking your improvement.'}
        </p>
      </Panel>
    );
  }

  const { otr, otr_previous, trend, pillars, weakest_pillar, mission, percentile, recap, matches = [] } = progress;
  const tb = trendBadge(trend);
  const TrendIcon = tb.icon;
  const delta = otr_previous != null ? +(otr - otr_previous).toFixed(1) : null;

  return (
    <div className="space-y-4">
      {/* ── HERO: the number they come back for ── */}
      <section className="grid gap-4 lg:grid-cols-3">
        <Panel glow="red" className="lg:col-span-2 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-[10px] font-black uppercase tracking-widest text-muted mb-1">
                OneTap Rating · last 10 matches
              </div>
              <div className="flex items-end gap-3">
                <span className={`text-6xl font-black tabular-nums leading-none ${otrColor(otr)}`}>
                  {otr.toFixed(1)}
                </span>
                <div className="pb-1 space-y-1">
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[10px] font-black uppercase tracking-widest ${tb.cls}`}>
                    <TrendIcon size={12} />
                    {tb.label}
                    {delta != null && trend !== 'flat' && (
                      <span className="tabular-nums">{delta > 0 ? '+' : ''}{delta}</span>
                    )}
                  </span>
                  <div className="text-[10px] text-muted/70">
                    50 = average of your lobbies · beats opponents&apos; rank &amp; smurfs by design
                  </div>
                </div>
              </div>
            </div>
            {percentile && (
              <div className="text-right">
                <div className="text-[10px] font-black uppercase tracking-widest text-muted mb-1">
                  Among {percentile.cohort_rank_name}s
                </div>
                <div className="text-2xl font-black text-brand-blue tabular-nums">
                  Top {Math.max(1, 100 - percentile.percentile)}%
                </div>
                <div className="text-[10px] text-muted/60">of {percentile.cohort_size} tracked players</div>
              </div>
            )}
          </div>

          {/* OTR sparkline with the lobby-average reference */}
          <div className="mt-5 h-32">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={matches} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
                <defs>
                  <linearGradient id="otrFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.28} />
                    <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="map" hide />
                <YAxis domain={[20, 80]} hide />
                <ReferenceLine y={50} stroke="#8b9bb0" strokeDasharray="4 4" strokeOpacity={0.4} />
                <Tooltip content={<OtrTooltip />} />
                <Area type="monotone" dataKey="otr" stroke="#22d3ee" strokeWidth={2} fill="url(#otrFill)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        {/* ── MISSION: the reason to play tonight ── */}
        <Panel glow="blue" className="p-6 flex flex-col">
          <div className="flex items-center gap-2 mb-3">
            <Flame size={14} className="text-brand-red" />
            <span className="text-[10px] font-black uppercase tracking-widest text-white/80">Today&apos;s Mission</span>
          </div>
          {mission ? (
            <>
              <h3 className="text-lg font-black text-white leading-tight">{mission.title}</h3>
              <p className="mt-2 text-xs font-bold text-brand-blue leading-relaxed">{mission.goal}</p>
              <p className="mt-3 text-[11px] text-muted leading-relaxed flex-1">{mission.how}</p>
              <div className="mt-4 pt-3 border-t border-line/40 text-[10px] text-muted/70 leading-relaxed">
                <span className="text-white/60 font-bold uppercase tracking-wider">Why it matters: </span>
                {mission.why}
              </div>
            </>
          ) : (
            <p className="text-xs text-muted">Play more matches to unlock your first mission.</p>
          )}
        </Panel>
      </section>

      {/* ── PILLARS: where the rating comes from ── */}
      <Panel className="p-6">
        <SectionTitle>Skill Pillars · vs your lobbies</SectionTitle>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {(Object.keys(PILLAR_META) as PillarKey[]).map((key) => {
            const meta = PILLAR_META[key];
            const Icon = meta.icon;
            const score = pillars?.[key] ?? 50;
            const weakest = key === weakest_pillar;
            const barColor = weakest ? 'bg-brand-red' : score >= 55 ? 'bg-emerald-400' : 'bg-brand-blue';
            return (
              <div
                key={key}
                className={`rounded-xl border px-4 py-3.5 ${
                  weakest ? 'border-brand-red/40 bg-brand-red/[0.05]' : 'border-line/60 bg-ink-800/40'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Icon size={13} className={weakest ? 'text-brand-red' : 'text-brand-blue'} />
                    <span className="text-[11px] font-black uppercase tracking-wider text-white/90">{meta.label}</span>
                  </div>
                  <span className="text-lg font-black tabular-nums text-white">{score}</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                  <div className={`h-full rounded-full transition-all duration-700 ${barColor}`} style={{ width: `${score}%` }} />
                </div>
                <div className="mt-2 text-[10px] text-muted/70 leading-snug">
                  {weakest ? 'Your focus — the mission targets this' : meta.blurb}
                </div>
              </div>
            );
          })}
        </div>
      </Panel>

      {/* ── RECAP STRIP: the earned-progress story ── */}
      {recap && (
        <Panel className="px-6 py-4">
          <div className="flex flex-wrap items-center gap-x-8 gap-y-2 text-xs">
            <span className="text-[10px] font-black uppercase tracking-widest text-muted">This window</span>
            <span className="font-bold text-white tabular-nums">{recap.record}</span>
            <span className={`font-bold tabular-nums ${recap.otr_delta > 0 ? 'text-emerald-400' : recap.otr_delta < 0 ? 'text-amber-400' : 'text-muted'}`}>
              OTR {recap.otr_delta > 0 ? '+' : ''}{recap.otr_delta}
            </span>
            {recap.best_pillar_gain && (
              <span className="inline-flex items-center gap-1 text-emerald-400 font-bold">
                <ArrowUpRight size={12} />
                {PILLAR_META[recap.best_pillar_gain.pillar].label} +{recap.best_pillar_gain.delta}
              </span>
            )}
            {recap.rank_change && (
              <span className="text-brand-blue font-bold">{recap.rank_change}</span>
            )}
            <span className="text-muted/60 ml-auto">
              Best match: <span className="text-white/80 font-bold">{recap.best_match?.map}</span>{' '}
              <span className="tabular-nums">OTR {recap.best_match?.otr}</span>
            </span>
          </div>
        </Panel>
      )}
    </div>
  );
}
