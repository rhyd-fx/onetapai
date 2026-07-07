"use client";

import { useState, useEffect } from 'react';
import { DashboardVM, MapPerf } from '@/lib/viewModel';
import { SectionTitle, LockedTile } from './primitives';

// Cache for official map splash images fetched from Valorant API
const mapSplashCache: Record<string, string> = {};

function MapCard({ 
  perf, 
  kind, 
  splashUrl 
}: { 
  perf?: MapPerf; 
  kind: 'best' | 'worst'; 
  splashUrl?: string; 
}) {
  const isBest = kind === 'best';
  const accent = isBest ? 'text-brand-blue' : 'text-brand-red';
  const ring = isBest ? 'ring-brand-blue/30' : 'ring-brand-red/30';

  if (!perf) {
    return (
      <div className="relative h-40 overflow-hidden rounded-2xl border border-line/60 bg-ink-700/50">
        <div className="flex h-full items-center justify-center text-sm text-muted">
          {isBest ? 'Best map' : 'Worst map'} — need more games
        </div>
      </div>
    );
  }

  return (
    <div className={`relative h-40 overflow-hidden rounded-2xl ring-1 ${ring} group cursor-pointer`}>
      {/* High-definition official map splash art with premium zoom interaction */}
      <div
        className="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-105"
        style={{ backgroundImage: `url(${splashUrl || `/maps/${perf.map}.png`})` }}
      />
      <div className="absolute inset-0 bg-gradient-to-r from-ink-900 via-ink-900/80 to-transparent" />
      <div className="relative flex h-full flex-col justify-between p-5">
        <div>
          <div className={`text-[10px] font-bold uppercase tracking-[0.2em] ${accent}`}>
            {isBest ? 'Best Map' : 'Worst Map'}
          </div>
          <div className="text-2xl font-extrabold text-white">{perf.map}</div>
        </div>
        <div className="flex items-end gap-5">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-muted">Avg ACS</div>
            <div className={`text-xl font-bold tabular-nums ${accent}`}>{perf.avgAcs.toFixed(0)}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-widest text-muted">Win Rate</div>
            <div className="text-xl font-bold tabular-nums text-white">{perf.winRate.toFixed(0)}%</div>
          </div>
          <div className="ml-auto text-[11px] text-muted">{perf.games} games</div>
        </div>
      </div>
    </div>
  );
}

function TeleTile({
  label,
  value,
  unit,
  hint,
  tone,
  signed,
}: {
  label: string;
  value?: number | null;
  unit: string;
  hint: string;
  tone?: 'red' | 'blue' | 'neutral';
  signed?: boolean; // show an explicit +/- sign (e.g. FK/FD differential)
}) {
  if (value == null) return <LockedTile label={label} />;
  const color = tone === 'red' ? 'text-brand-red' : tone === 'blue' ? 'text-brand-blue' : 'text-white';
  const display = signed && value > 0 ? `+${value}` : String(value);
  return (
    <div className="rounded-xl border border-line/60 bg-ink-800/40 px-3 py-4">
      <div className="text-[10px] font-medium uppercase tracking-widest text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${color}`}>
        {display}
        <span className="text-base">{unit}</span>
      </div>
      <div className="text-[11px] text-muted">{hint}</div>
    </div>
  );
}

export default function MapsAndTelemetry({ vm }: { vm: DashboardVM }) {
  const tel = vm.telemetry;
  const [showAllMaps, setShowAllMaps] = useState(false);
  const [mapSplashes, setMapSplashes] = useState<Record<string, string>>(mapSplashCache);

  useEffect(() => {
    // If cache is populated, skip fetch
    if (Object.keys(mapSplashes).length > 0) return;

    fetch('https://valorant-api.com/v1/maps')
      .then((res) => res.json())
      .then((res) => {
        if (res?.data) {
          const mapping: Record<string, string> = {};
          res.data.forEach((m: any) => {
            if (m.displayName && m.splash) {
              mapping[m.displayName.toLowerCase()] = m.splash;
            }
          });
          Object.assign(mapSplashCache, mapping);
          setMapSplashes({ ...mapping });
        }
      })
      .catch((err) => console.error('Failed to fetch official map splashes from Valorant API:', err));
  }, [mapSplashes]);

  const getSplashUrl = (mapName?: string) => {
    if (!mapName) return undefined;
    return mapSplashes[mapName.toLowerCase()];
  };
  
  return (
    <section className="space-y-5">
      <div>
        <SectionTitle accent="blue">Map Performance</SectionTitle>
        <div className="grid gap-4 md:grid-cols-2">
          <MapCard 
            perf={vm.bestMap} 
            kind="best" 
            splashUrl={getSplashUrl(vm.bestMap?.map)} 
          />
          <MapCard 
            perf={vm.worstMap} 
            kind="worst" 
            splashUrl={getSplashUrl(vm.worstMap?.map)} 
          />
        </div>

        {vm.topMaps && vm.topMaps.length > 0 && (
          <div className="space-y-3">
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {(showAllMaps ? vm.topMaps : vm.topMaps.slice(0, 4)).map((mapStats) => {
                const winRate = mapStats.win_rate;
                const barColor = winRate >= 55 ? 'bg-brand-blue' : winRate >= 45 ? 'bg-white/80' : 'bg-brand-red';
                return (
                  <div key={mapStats.map} className="rounded-xl border border-line/40 bg-ink-800/40 px-4 py-3 flex items-center justify-between gap-4 transition hover:border-line">
                    <div className="flex flex-col">
                      <span className="text-sm font-bold text-white uppercase tracking-wider">{mapStats.map}</span>
                      <span className="text-[11px] text-muted mt-0.5">{mapStats.games} games ({mapStats.wins}W · {mapStats.losses}L)</span>
                    </div>
                    <div className="flex flex-col items-end min-w-[70px]">
                      <span className="text-sm font-extrabold text-white tabular-nums">{winRate.toFixed(0)}% WR</span>
                      <div className="w-16 h-1.5 bg-ink-600 rounded-full mt-1.5 overflow-hidden">
                        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${winRate}%` }} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            {vm.topMaps.length > 4 && (
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => setShowAllMaps(!showAllMaps)}
                  className="text-xs font-black uppercase tracking-widest text-brand-blue hover:text-brand-blue-soft transition"
                >
                  {showAllMaps ? 'Hide Map Performance' : 'See All Map Performance'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <div>
        <SectionTitle>Advanced Telemetry</SectionTitle>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
          <TeleTile
            label="ADR"
            value={tel?.adr}
            unit=""
            hint="Avg damage / round"
            tone={tel?.adr == null ? undefined : tel.adr >= 150 ? 'blue' : tel.adr < 120 ? 'red' : 'neutral'}
          />
          <TeleTile
            label="First Duels (FK/FD)"
            value={tel?.fk_fd_diff}
            unit=""
            hint={tel?.first_kills != null ? `${tel.first_kills} FK · ${tel.first_deaths} FD` : 'Opening impact'}
            tone={tel?.fk_fd_diff == null ? undefined : tel.fk_fd_diff > 0 ? 'blue' : tel.fk_fd_diff < 0 ? 'red' : 'neutral'}
            signed
          />
          <TeleTile
            label="Opening Duels"
            value={tel?.opening_duel_win_pct}
            unit="%"
            hint="First-fight win rate"
            tone={tel?.opening_duel_win_pct == null ? undefined : tel.opening_duel_win_pct >= 50 ? 'blue' : 'red'}
          />
          <TeleTile
            label="Movement Error"
            value={tel?.movement_error_pct}
            unit="%"
            hint="Zero-dmg deaths"
            tone={tel?.movement_error_pct == null ? undefined : tel.movement_error_pct > 25 ? 'red' : tel.movement_error_pct < 15 ? 'blue' : 'neutral'}
          />
          <TeleTile
            label="Multi-Kill"
            value={tel?.multikill_pct}
            unit="%"
            hint="Rounds with 2+ kills"
            tone={tel?.multikill_pct == null ? undefined : tel.multikill_pct >= 15 ? 'blue' : 'neutral'}
          />
          <TeleTile
            label="Time-to-Damage"
            value={tel?.avg_time_to_damage_s}
            unit="s"
            hint="Avg first engage"
            tone="neutral"
          />
        </div>
      </div>
    </section>
  );
}
