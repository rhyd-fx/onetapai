"use client";

import { DashboardVM } from '@/lib/viewModel';

function ProfileStatTile({ 
  label, 
  value, 
  sub, 
  accent 
}: { 
  label: string; 
  value: string | number; 
  sub?: string; 
  accent?: 'red' | 'blue';
}) {
  const valCls = accent === 'red' ? 'text-brand-red' : accent === 'blue' ? 'text-brand-blue' : 'text-white';
  return (
    <div className="rounded-xl border border-white/5 bg-ink-900/50 backdrop-blur-md px-3.5 py-3.5 transition duration-300 hover:border-white/10 hover:bg-ink-900/80">
      <div className="text-[10px] font-bold uppercase tracking-widest text-muted">{label}</div>
      <div className={`mt-0.5 text-2xl font-black tabular-nums ${valCls}`}>{value}</div>
      {sub && <div className="text-[10px] text-muted/70 font-semibold mt-0.5">{sub}</div>}
    </div>
  );
}

export default function ProfileCard({ vm }: { vm: DashboardVM }) {
  const [name, tag] = vm.riotId.split('#');
  
  return (
    <div className="relative flex h-full flex-col justify-between overflow-hidden rounded-2xl bg-ink-950/60 border border-white/5 group">
      {/* Top Banner (Player Card wideart) */}
      {vm.cardUrl ? (
        <div className="relative w-full h-20 overflow-hidden border-b border-white/5">
          <img 
            src={vm.cardUrl} 
            alt="Player Banner" 
            className="w-full h-full object-cover object-center transition-transform duration-700 group-hover:scale-105"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-ink-950 via-ink-950/20 to-transparent" />
        </div>
      ) : (
        <div className="w-full h-6 bg-gradient-to-r from-brand-red/20 to-brand-blue/20" />
      )}

      {/* Foreground Content */}
      <div className="flex-1 flex flex-col justify-between p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-baseline gap-1">
              <h1 className="text-3xl font-black tracking-tight text-white">{name}</h1>
              <span className="text-xl font-bold text-muted/80">#{tag}</span>
            </div>
            <div className="mt-1.5 flex items-center gap-2 text-xs">
              <span className="rounded bg-brand-blue/15 px-2 py-0.5 font-bold tracking-wider text-brand-blue border border-brand-blue/20">
                {vm.region}
              </span>
              <span className="text-muted/90 font-medium">
                Main: <span className="text-white font-semibold">{vm.mainAgent}</span>
              </span>
            </div>
          </div>

          {/* Performance-tier badge (derived from ACS — not an official rank) */}
          <div className="glow-red flex flex-col items-center rounded-xl border border-brand-red/40 bg-gradient-to-b from-brand-red/25 to-ink-950/80 px-4 py-2 text-center backdrop-blur-sm shadow-lg">
            <span className="text-xs font-black tracking-widest text-brand-red">{vm.tier.label}</span>
            <span className="text-[8px] uppercase tracking-widest text-muted/80 font-bold mt-0.5">{vm.tier.hint}</span>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-3 grid-rows-2 gap-3.5">
          <ProfileStatTile label="K/D" value={vm.stats.kd} accent={Number(vm.stats.kd) >= 1 ? 'blue' : 'red'} />
          <ProfileStatTile label="Headshot %" value={`${vm.stats.hsPct.toFixed(0)}%`} accent="red" />
          <ProfileStatTile label="ACS" value={vm.stats.acs.toFixed(0)} accent="red" />
          <ProfileStatTile
            label="Win Rate"
            value={vm.stats.winRate != null ? `${vm.stats.winRate.toFixed(0)}%` : '—'}
            accent={vm.stats.winRate != null && vm.stats.winRate >= 50 ? 'blue' : 'red'}
          />
          <ProfileStatTile label="Kills" value={vm.stats.kills} sub={`${vm.stats.games} games`} />
          <ProfileStatTile label="Deaths" value={vm.stats.deaths} sub={`CV: ${vm.consistency.cv.toFixed(2)}`} />
        </div>
      </div>
    </div>
  );
}
