"use client";

import { Crosshair, Swords, DollarSign, MousePointer } from 'lucide-react';
import { DashboardVM } from '@/lib/viewModel';
import { Panel, SectionTitle } from './primitives';

export default function CoachingDiagnostics({ vm }: { vm: DashboardVM }) {
  const aim = vm.aimByDistance;
  const econ = vm.economyEfficiency;
  const side = vm.sideBias;
  const hw = vm.hardwareCheck;

  // 1. Aim by distance alerts
  const longRangeHS = aim.find((a) => a.range === 'long')?.headshot_pct ?? 0;
  const aimInsight = longRangeHS < 12 
    ? "Your long-range headshot rate is low. Stop spraying past 15 meters; practice 2-bullet tap bursts."
    : "Your distance precision is solid. Maintain crosshair placement when holding long angles.";

  // 2. Tactical side bias alerts
  const earlyDeathPct = side?.early_defense_death_pct ?? 0;
  const sideInsight = earlyDeathPct > 20
    ? `You die early in ${earlyDeathPct.toFixed(0)}% of Defense rounds. Avoid dry-peeking early; hold passive angles.`
    : "Good patience on Defense. You are staying alive to absorb enemy site executes.";

  // 3. Economy alerts
  const ecoThrows = econ?.eco_throws ?? 0;
  const econInsight = ecoThrows > 0
    ? `Lost ${ecoThrows} full-buy rounds to enemy eco saves. Keep your distance against cheap pistols.`
    : "Clean conversions. You play discipline rounds well when you hold the economic advantage.";

  // 4. eDPI check
  const edpi = hw?.edpi ?? 280;
  let edpiRating = "Optimal";
  let edpiColor = "text-brand-blue";
  let edpiBarColor = "bg-brand-blue";
  let edpiInsight = "Your sensitivity is in the optimal range (200-400 eDPI) for precise micro-adjustments.";

  if (edpi > 600) {
    edpiRating = "CRITICAL (Too High)";
    edpiColor = "text-brand-red";
    edpiBarColor = "bg-brand-red";
    edpiInsight = "Sens is extremely high! Lowering it below 400 eDPI will instantly improve your precision.";
  } else if (edpi > 400) {
    edpiRating = "High";
    edpiColor = "text-amber-400";
    edpiBarColor = "bg-amber-400";
    edpiInsight = "Your sensitivity is slightly high. Try lowering it to improve long-range headshot consistency.";
  } else if (edpi < 180) {
    edpiRating = "Low";
    edpiColor = "text-zinc-400";
    edpiBarColor = "bg-zinc-400";
    edpiInsight = "Your sensitivity is low. Ensure you have enough mousepad space for 180-degree swipes.";
  }

  return (
    <section className="space-y-4">
      <SectionTitle accent="red">Coaching Diagnostics &amp; Insights</SectionTitle>
      
      <div className="grid gap-4 md:grid-cols-2">
        {/* Module 1: Aim by Distance */}
        <Panel className="p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Crosshair size={18} className="text-brand-red" />
              <h3 className="text-sm font-black uppercase tracking-wider text-white">Aim by Engagement Distance</h3>
            </div>
            
            <div className="space-y-3 mt-4">
              {aim.map((a) => {
                const rangeLabel = a.range === 'close' ? 'Close (<10m)' : a.range === 'medium' ? 'Medium (10m-20m)' : 'Long (>20m)';
                return (
                  <div key={a.range} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold text-muted">
                      <span>{rangeLabel}</span>
                      <span className="text-white">{a.headshot_pct}% HS <span className="text-[10px] text-muted">({a.kills} kills)</span></span>
                    </div>
                    {/* Progress bar */}
                    <div className="w-full h-2 bg-ink-600 rounded-full flex overflow-hidden">
                      <div className="h-full bg-brand-red" style={{ width: `${a.headshot_pct}%` }} />
                      <div className="h-full bg-white/70" style={{ width: `${a.bodyshot_pct}%` }} />
                      <div className="h-full bg-brand-blue" style={{ width: `${a.legshot_pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          
          <div className="mt-4 pt-3 border-t border-line/30 text-xs text-muted leading-relaxed">
            <strong className="text-brand-red font-bold block uppercase text-[10px] tracking-wider mb-0.5">Aim Tip:</strong>
            {aimInsight}
          </div>
        </Panel>

        {/* Module 2: Tactical Side Bias */}
        <Panel className="p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Swords size={18} className="text-brand-blue" />
              <h3 className="text-sm font-black uppercase tracking-wider text-white">Tactical Side Bias</h3>
            </div>

            {side ? (
              <div className="space-y-3.5 mt-4">
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold text-muted">
                    <span>Attack Win Rate</span>
                    <span className="text-white">{side.attack_win_pct}% <span className="text-[10px] text-muted">({side.attack_rounds} rounds)</span></span>
                  </div>
                  <div className="w-full h-2 bg-ink-600 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-blue" style={{ width: `${side.attack_win_pct}%` }} />
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold text-muted">
                    <span>Defense Win Rate</span>
                    <span className="text-white">{side.defense_win_pct}% <span className="text-[10px] text-muted">({side.defense_rounds} rounds)</span></span>
                  </div>
                  <div className="w-full h-2 bg-ink-600 rounded-full overflow-hidden">
                    <div className="h-full bg-white/80" style={{ width: `${side.defense_win_pct}%` }} />
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold text-muted">
                    <span>Defense Early Death Rate (&lt;15s)</span>
                    <span className={earlyDeathPct > 20 ? 'text-brand-red' : 'text-white'}>{side.early_defense_death_pct}%</span>
                  </div>
                  <div className="w-full h-2 bg-ink-600 rounded-full overflow-hidden">
                    <div className={`h-full ${earlyDeathPct > 20 ? 'bg-brand-red' : 'bg-brand-blue'}`} style={{ width: `${side.early_defense_death_pct}%` }} />
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-6 text-sm text-muted">No side data found.</div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-line/30 text-xs text-muted leading-relaxed">
            <strong className="text-brand-blue font-bold block uppercase text-[10px] tracking-wider mb-0.5">Positioning Tip:</strong>
            {sideInsight}
          </div>
        </Panel>

        {/* Module 3: Buy & Economy Efficiency */}
        <Panel className="p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <DollarSign size={18} className="text-emerald-400" />
              <h3 className="text-sm font-black uppercase tracking-wider text-white">Economy &amp; Buy Efficiency</h3>
            </div>

            {econ ? (
              <div className="grid grid-cols-2 gap-3 mt-4">
                <div className="rounded-lg bg-ink-800/40 border border-line/30 p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-muted">Eco Win Rate</div>
                  <div className="text-lg font-black text-white mt-0.5">{econ.by_class.eco.win_rate}%</div>
                  <div className="text-[9px] text-muted">{econ.by_class.eco.rounds} rounds played</div>
                </div>
                <div className="rounded-lg bg-ink-800/40 border border-line/30 p-2.5">
                  <div className="text-[9px] uppercase tracking-wider text-muted">Full Buy Win Rate</div>
                  <div className="text-lg font-black text-white mt-0.5">{econ.by_class.full_buy.win_rate}%</div>
                  <div className="text-[9px] text-muted">{econ.by_class.full_buy.rounds} rounds played</div>
                </div>
                <div className="col-span-2 rounded-lg bg-ink-800/40 border border-line/30 p-2.5 flex justify-between items-center">
                  <div>
                    <div className="text-[9px] uppercase tracking-wider text-muted">Eco-Throws (Full-Buy Lost vs Saves)</div>
                    <div className="text-[10px] text-muted">Indicates lack of spacing control</div>
                  </div>
                  <div className={`text-xl font-black ${ecoThrows > 0 ? 'text-brand-red animate-pulse' : 'text-emerald-400'}`}>
                    {ecoThrows}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-6 text-sm text-muted">No economy stats found.</div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-line/30 text-xs text-muted leading-relaxed">
            <strong className="text-emerald-400 font-bold block uppercase text-[10px] tracking-wider mb-0.5">Econ Tip:</strong>
            {econInsight}
          </div>
        </Panel>

        {/* Module 4: Hardware & Sensitivity Check */}
        <Panel className="p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <MousePointer size={18} className="text-brand-blue" />
              <h3 className="text-sm font-black uppercase tracking-wider text-white">Hardware &amp; Sensitivity</h3>
            </div>

            {hw ? (
              <div className="space-y-3.5 mt-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-[9px] uppercase tracking-wider text-muted">Mouse Model</div>
                    <div className="text-xs font-bold text-white truncate mt-0.5">{hw.mouse_model}</div>
                  </div>
                  <div>
                    <div className="text-[9px] uppercase tracking-wider text-muted">Monitor Refresh</div>
                    <div className="text-xs font-bold text-white mt-0.5">{hw.monitor_refresh_rate}Hz</div>
                  </div>
                </div>

                <div className="rounded-lg bg-ink-800/60 border border-line/40 p-3">
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-muted">In-Game eDPI</div>
                      <div className="text-[9px] text-muted">{hw.mouse_dpi} DPI · {hw.in_game_sens} Sens</div>
                    </div>
                    <div className="text-right">
                      <div className={`text-xl font-black ${edpiColor}`}>{edpi.toFixed(0)}</div>
                      <div className={`text-[9px] font-black uppercase tracking-wider ${edpiColor}`}>{edpiRating}</div>
                    </div>
                  </div>
                  {/* Gauge bar */}
                  <div className="w-full h-1.5 bg-ink-900 rounded-full mt-2.5 overflow-hidden">
                    <div className={`h-full ${edpiBarColor}`} style={{ width: `${Math.min(100, (edpi / 800) * 100)}%` }} />
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-6 text-sm text-muted">No hardware profile found.</div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-line/30 text-xs text-muted leading-relaxed">
            <strong className="text-brand-blue font-bold block uppercase text-[10px] tracking-wider mb-0.5">Sens Tip:</strong>
            {edpiInsight}
          </div>
        </Panel>
      </div>
    </section>
  );
}
