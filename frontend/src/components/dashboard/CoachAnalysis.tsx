"use client";

import { Crosshair, Swords, DollarSign, MousePointer, ShieldCheck, HelpCircle, Target, Compass, Zap, Clock, Award } from 'lucide-react';
import { DashboardVM } from '@/lib/viewModel';
import { Panel, SectionTitle } from './primitives';

const DuelistIcon = () => (
  <svg className="w-4 h-4 text-brand-red fill-current" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <path d="M50 5C50 5 75 32 75 55C75 72 63.8 85 50 85C36.2 85 25 72 25 55C25 38 41 18 41 18C41 18 35 30 35 43C35 55 42 63 50 63C58 63 61 53 61 43C61 32 50 5 50 5Z" />
  </svg>
);

const InitiatorIcon = () => (
  <svg className="w-4 h-4 text-amber-400 fill-current" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <path d="M50 15C30.7 15 15 30.7 15 50C15 69.3 30.7 85 50 85C69.3 85 85 69.3 85 50C85 30.7 69.3 15 50 15ZM50 73C37.3 73 27 62.7 27 50C27 37.3 37.3 27 50 27C62.7 27 73 37.3 73 50C73 62.7 62.7 73 50 73ZM50 35C41.7 35 35 41.7 35 50C35 58.3 41.7 65 50 65C58.3 65 65 58.3 65 50C65 41.7 58.3 35 50 35Z" />
  </svg>
);

const SentinelIcon = () => (
  <svg className="w-4 h-4 text-brand-blue fill-current" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <path d="M50 10L15 25V55C15 72.5 32 87.5 50 90C68 87.5 85 72.5 85 55V25L50 10ZM50 78C37.3 75.3 27 64 27 52V34.5L50 24.5L73 34.5V52C73 64 62.7 75.3 50 78Z" />
  </svg>
);

const ControllerIcon = () => (
  <svg className="w-4 h-4 text-purple-400 fill-current" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <path d="M50 15C30.7 15 15 30.7 15 50C15 69.3 30.7 85 50 85C69.3 85 85 69.3 85 50C85 30.7 69.3 15 50 15ZM50 67C40.6 67 33 59.4 33 50H67C67 59.4 59.4 67 50 67ZM33 50C33 40.6 40.6 33 50 33C59.4 33 67 40.6 67 50H33Z" />
  </svg>
);

const ROLE_ICONS: Record<string, string> = {
  Duelist: 'https://media.valorant-api.com/agents/roles/dbe8757e-9e92-4ed4-b39f-9dfc589691d4/displayicon.png',
  Initiator: 'https://media.valorant-api.com/agents/roles/1b47567f-8f7b-444b-aae3-b0c634622d10/displayicon.png',
  Controller: 'https://media.valorant-api.com/agents/roles/4ee40330-ecdd-4f2f-98a8-eb1243428373/displayicon.png',
  Sentinel: 'https://media.valorant-api.com/agents/roles/5fc02f99-4091-4486-a531-98459a3e95e9/displayicon.png'
};

export default function CoachAnalysis({ vm }: { vm: DashboardVM }) {
  const aim = vm.aimByDistance;
  const econ = vm.economyEfficiency;
  const side = vm.sideBias;
  const hw = vm.hardwareCheck;

  // 1. Aim by distance alerts
  const longRangeHS = aim.find((a) => a.range === 'long')?.headshot_pct ?? 0;
  const aimInsight = longRangeHS < 12 
    ? "Stop spraying past 15 meters; practice 2-bullet tap bursts in deathmatch."
    : "Your distance precision is excellent. Continue holding long choke points with confidence.";

  // 2. Tactical side bias alerts
  const earlyDeathPct = side?.early_defense_death_pct ?? 0;
  const sideInsight = earlyDeathPct > 20
    ? `You die early in ${earlyDeathPct.toFixed(0)}% of Defense rounds. Play passive; let the enemy execute first.`
    : "Good patience on Defense. You stay alive to support team retakes.";

  // 3. Economy alerts
  const ecoThrows = econ?.eco_throws ?? 0;
  const econInsight = ecoThrows > 0
    ? `Lost ${ecoThrows} full-buy rounds to enemy eco saves. Keep distance against short-range pistols.`
    : "Clean conversions. You hold range and respect eco rounds.";

  // 4. eDPI check
  const edpi = hw?.edpi ?? 280;
  let edpiRating = "Optimal";
  let edpiColor = "text-brand-blue";
  let edpiBarColor = "bg-brand-blue";
  let edpiInsight = "Sensitivity is in the optimal range (200-400 eDPI) for micro-adjustments.";

  if (edpi > 600) {
    edpiRating = "CRITICAL (Too High)";
    edpiColor = "text-brand-red";
    edpiBarColor = "bg-brand-red";
    edpiInsight = "Sens is extremely high! Lowering it below 400 eDPI will instantly improve your precision.";
  } else if (edpi > 400) {
    edpiRating = "High";
    edpiColor = "text-amber-400";
    edpiBarColor = "bg-amber-400";
    edpiInsight = "Sensitivity is high. Lowering it slightly will help with distance headshot consistency.";
  } else if (edpi < 180) {
    edpiRating = "Low";
    edpiColor = "text-zinc-400";
    edpiBarColor = "bg-zinc-400";
    edpiInsight = "Sensitivity is low. Ensure you have ample mousepad space for large swipes.";
  }

  return (
    <section className="space-y-6">
      {/* Brutally honest quote banner */}
      <div className="relative overflow-hidden rounded-2xl border border-brand-red/30 bg-gradient-to-r from-brand-red/15 via-ink-700/60 to-ink-700/40 p-6 shadow-lg">
        <div className="absolute -left-2 top-2 text-7xl font-black leading-none text-brand-red/10">“</div>
        <div className="relative pl-8">
          <div className="text-[10px] font-bold uppercase tracking-[0.25em] text-brand-red">
            OneTap AI · Brutally Honest Review
          </div>
          <p className="mt-2 text-base md:text-lg font-black leading-relaxed text-white tracking-wide italic">
            "{vm.quote}"
          </p>
        </div>
      </div>

      {/* Deep Dive & Diagnostics */}
      <div>
        <SectionTitle>Diagnostics &amp; Deep Dive</SectionTitle>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          
          {/* Panel 1: Combat Profile & Consistency */}
          <Panel glow="red" className="p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-line/10">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={18} className="text-brand-red" />
                  <h3 className="text-xs font-black uppercase tracking-wider text-white">Combat &amp; Consistency</h3>
                </div>
              </div>
              
              {/* Agent & Role Summary */}
              <div className="mt-4 mb-4 flex items-center justify-between p-3 rounded-xl bg-ink-850/40 border border-line/10">
                <div className="flex flex-col">
                  <span className="text-[9px] uppercase tracking-wider text-muted font-bold">Main Agent</span>
                  <span className="text-sm font-black text-white uppercase tracking-wider mt-0.5">{vm.mainAgent}</span>
                </div>
                <span className="rounded bg-brand-red/15 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-brand-red border border-brand-red/20">
                  {vm.bestRole?.role || 'Flex'}
                </span>
              </div>

              {/* Stats Grid (2 Columns) */}
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="p-3 rounded-xl bg-ink-850/20 border border-line/10">
                  <span className="text-[9px] uppercase tracking-wider text-muted font-bold block">Avg ACS</span>
                  <span className="text-base font-black text-white mt-1 block">{vm.stats.acs.toFixed(0)}</span>
                </div>
                <div className="p-3 rounded-xl bg-ink-850/20 border border-line/10">
                  <span className="text-[9px] uppercase tracking-wider text-muted font-bold block">Headshot %</span>
                  <span className="text-base font-black text-white mt-1 block">{vm.stats.hsPct.toFixed(1)}%</span>
                </div>
              </div>

              {/* Stability Gauge Meter */}
              <div className="space-y-1.5 pt-3 border-t border-line/10">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-muted/80">Combat Consistency</span>
                  <span className="text-white font-extrabold uppercase">{vm.consistency.label}</span>
                </div>
                <div className="w-full h-1.5 bg-ink-950/80 rounded-full overflow-hidden border border-white/[0.03]">
                  <div 
                    className={`h-full ${vm.consistency.cv < 0.25 ? 'bg-emerald-400' : vm.consistency.cv < 0.4 ? 'bg-amber-400' : 'bg-brand-red'}`} 
                    style={{ width: `${Math.max(5, Math.min(100, 100 - (vm.consistency.cv * 100)))}%` }} 
                  />
                </div>
                <div className="flex justify-between text-[9px] text-muted/60">
                  <span>ACS Variance ({vm.consistency.cv.toFixed(2)} CV)</span>
                  <span>{vm.stats.games} matches</span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-line/30 text-xs text-muted leading-relaxed">
              <strong className="text-brand-red font-bold block uppercase text-[10px] tracking-wider mb-0.5">Consistency Tip:</strong>
              {vm.consistency.cv > 0.4 
                ? "Your combat score is unstable. Work on standardizing your positioning to eliminate round-to-round variance." 
                : "You maintain a highly consistent performance output. Excellent stability."}
            </div>
          </Panel>

          {/* Panel 2: Aim by Distance */}
          <Panel className="p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-line/10">
                <div className="flex items-center gap-2">
                  <Crosshair size={18} className="text-brand-red" />
                  <h3 className="text-xs font-black uppercase tracking-wider text-white">Engagement Accuracy</h3>
                </div>
                
                {/* Visual Zone Legend */}
                <div className="flex gap-2.5 text-[8px] uppercase tracking-widest text-muted/80 font-black">
                  <div className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-brand-red" />
                    <span>HS</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-white/70" />
                    <span>Body</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-brand-blue" />
                    <span>Leg</span>
                  </div>
                </div>
              </div>
              
              <div className="space-y-4 mt-4">
                {aim.map((a) => {
                  let rangeName = "Close Range";
                  let rangeMeters = "< 10m";
                  let rangeGlow = "border-zinc-500/10 text-zinc-400 bg-zinc-500/[0.04]";
                  
                  if (a.range === 'medium') {
                    rangeName = "Medium Range";
                    rangeMeters = "10 - 20m";
                    rangeGlow = "border-amber-500/10 text-amber-400 bg-amber-500/[0.04]";
                  } else if (a.range === 'long') {
                    rangeName = "Long Range";
                    rangeMeters = "> 20m";
                    rangeGlow = "border-brand-red/10 text-brand-red bg-brand-red/[0.04]";
                  }
                  
                  return (
                    <div key={a.range} className="space-y-2">
                      <div className="flex justify-between items-center text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-extrabold text-white uppercase tracking-wider text-[11px]">{rangeName}</span>
                          <span className={`text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded border ${rangeGlow}`}>
                            {rangeMeters}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-muted font-bold uppercase tracking-wider">Kills: {a.kills}</span>
                          <span className="text-white font-extrabold">{a.headshot_pct}% <span className="text-[9px] text-brand-red/80 font-black">HS</span></span>
                        </div>
                      </div>
                      
                      <div className="w-full h-2 bg-ink-950/80 rounded-full flex overflow-hidden border border-white/[0.03]">
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

          {/* Panel 3: Tactical Side Bias */}
          <Panel glow="blue" className="p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Swords size={18} className="text-brand-blue" />
                <h3 className="text-xs font-black uppercase tracking-wider text-white">Tactical Side Bias</h3>
              </div>

              {side ? (
                <div className="space-y-3 mt-4">
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold text-muted">
                      <span>Attack Win Rate</span>
                      <span className="text-white">{side.attack_win_pct}% <span className="text-[10px] text-muted">({side.attack_rounds} rds)</span></span>
                    </div>
                    <div className="w-full h-1.5 bg-ink-600 rounded-full overflow-hidden">
                      <div className="h-full bg-brand-blue" style={{ width: `${side.attack_win_pct}%` }} />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold text-muted">
                      <span>Defense Win Rate</span>
                      <span className="text-white">{side.defense_win_pct}% <span className="text-[10px] text-muted">({side.defense_rounds} rds)</span></span>
                    </div>
                    <div className="w-full h-1.5 bg-ink-600 rounded-full overflow-hidden">
                      <div className="h-full bg-white/80" style={{ width: `${side.defense_win_pct}%` }} />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold text-muted">
                      <span>Defense Early Death Rate</span>
                      <span className={earlyDeathPct > 20 ? 'text-brand-red' : 'text-white'}>{side.early_defense_death_pct}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-ink-600 rounded-full overflow-hidden">
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

        {/* Panel 4: Economy Efficiency */}
        <Panel className="p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-line/10">
              <div className="flex items-center gap-2">
                <DollarSign size={18} className="text-emerald-400" />
                <h3 className="text-xs font-black uppercase tracking-wider text-white">Economy Impact</h3>
              </div>
              {vm.economyImpactLabel && (
                <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[9px] font-black uppercase tracking-wider text-emerald-400 border border-emerald-500/20">
                  {vm.economyImpactLabel}
                </span>
              )}
            </div>

            {econ ? (
              <div className="space-y-4">
                {/* Win Rates Progress Bar Split */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <div className="flex justify-between text-[10px] text-muted font-bold uppercase tracking-wider">
                      <span>Eco WR</span>
                      <span className="text-white font-bold">{econ.by_class.eco.win_rate}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-ink-600 rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-400" style={{ width: `${econ.by_class.eco.win_rate}%` }} />
                    </div>
                    <span className="text-[9px] text-muted/60 block">{econ.by_class.eco.rounds} rounds</span>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[10px] text-muted font-bold uppercase tracking-wider">
                      <span>Full Buy WR</span>
                      <span className="text-white font-bold">{econ.by_class.full_buy.win_rate}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-ink-600 rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-400" style={{ width: `${econ.by_class.full_buy.win_rate}%` }} />
                    </div>
                    <span className="text-[9px] text-muted/60 block">{econ.by_class.full_buy.rounds} rounds</span>
                  </div>
                </div>

                {/* ACS by Buy Tier visual progress bars */}
                {vm.economySplit && (
                  <div className="space-y-2.5 pt-3 border-t border-line/10">
                    <div className="text-[10px] uppercase tracking-wider text-muted font-bold">ACS by Purchase Tier</div>
                    <div className="space-y-2">
                      {[
                        { key: 'eco', label: 'Eco (<2k)', color: 'bg-zinc-400' },
                        { key: 'half_buy', label: 'Half (2k-3.9k)', color: 'bg-amber-405' }, // Using a slightly shifted yellow for nice range
                        { key: 'force_buy', label: 'Force (3.9k-4.5k)', color: 'bg-amber-500' },
                        { key: 'full_buy', label: 'Full (≥4.5k)', color: 'bg-emerald-400' }
                      ].map((tier) => {
                        const stats = vm.economySplit?.[tier.key as 'eco' | 'half_buy' | 'force_buy' | 'full_buy'];
                        const acs = stats?.avg_acs ?? 0;
                        const rounds = stats?.rounds ?? 0;
                        const pct = Math.min((acs / 350) * 100, 100);
                        
                        // Map color class
                        let colorClass = "bg-zinc-500";
                        if (tier.key === 'half_buy') colorClass = "bg-sky-400";
                        if (tier.key === 'force_buy') colorClass = "bg-amber-500";
                        if (tier.key === 'full_buy') colorClass = "bg-emerald-400";

                        return (
                          <div key={tier.key} className="space-y-1">
                            <div className="flex justify-between text-[11px] font-medium">
                              <span className="text-muted/80">{tier.label}</span>
                              <span className="text-white font-semibold">
                                {acs} <span className="text-[9px] text-muted/60 font-medium">ACS</span> 
                                <span className="text-[9px] text-muted/40 font-medium ml-1">({rounds} rds)</span>
                              </span>
                            </div>
                            <div className="w-full h-1 bg-ink-900 rounded-full overflow-hidden">
                              <div className={`h-full ${colorClass}`} style={{ width: `${pct}%` }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Eco throws summary line */}
                <div className="flex items-center justify-between pt-2.5 border-t border-line/10 text-xs">
                  <span className="text-muted/80">Eco-Throws (Lost vs Saves)</span>
                  <div className="flex items-center gap-1.5">
                    {ecoThrows > 0 ? (
                      <>
                        <span className="w-1.5 h-1.5 rounded-full bg-brand-red animate-ping" />
                        <span className="font-extrabold text-brand-red tabular-nums">{ecoThrows} rounds</span>
                      </>
                    ) : (
                      <>
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        <span className="font-extrabold text-emerald-400">None</span>
                      </>
                    )}
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

        {/* Panel 5: Agent Role Performance */}
        <Panel className="p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-line/10">
              <div className="flex items-center gap-2">
                <Swords size={18} className="text-brand-red animate-pulse" />
                <h3 className="text-xs font-black uppercase tracking-wider text-white">Agent Role Performance</h3>
              </div>
            </div>

            {vm.roleStats.length > 0 ? (
              <div className="space-y-3 mt-4">
                {vm.roleStats.map((rs) => {
                  const isBest = rs.role === vm.bestRole?.role;
                  
                  // Role details
                  let barClass = "bg-brand-red";
                  if (rs.role === 'Initiator') {
                    barClass = "bg-amber-400";
                  } else if (rs.role === 'Sentinel') {
                    barClass = "bg-brand-blue";
                  } else if (rs.role === 'Controller') {
                    barClass = "bg-purple-400";
                  }

                  return (
                    <div 
                      key={rs.role} 
                      className={`rounded-2xl border p-4 transition-all duration-300 ease-out hover:scale-[1.01] ${
                        isBest 
                          ? 'bg-gradient-to-r from-brand-red/[0.04] via-brand-red/[0.01] to-transparent border-brand-red/35 shadow-lg shadow-brand-red/5' 
                          : 'bg-ink-850/40 border-line/10 hover:border-line/25'
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <div className="flex items-center gap-3">
                          <div className={`p-1.5 rounded-xl bg-ink-950/60 border ${
                            rs.role === 'Initiator' 
                              ? 'border-amber-500/20' 
                              : rs.role === 'Sentinel' 
                                ? 'border-sky-500/20' 
                                : rs.role === 'Controller' 
                                  ? 'border-purple-500/20' 
                                  : 'border-brand-red/20'
                          }`}>
                            <img 
                              src={ROLE_ICONS[rs.role] || ''} 
                              alt={rs.role} 
                              className="w-5 h-5 object-contain" 
                            />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-black text-white uppercase tracking-wider">{rs.role}</span>
                              {isBest && (
                                <span className="rounded bg-brand-red/15 px-1.5 py-0.5 text-[8px] font-black uppercase tracking-wider text-brand-red">
                                  BEST
                                  </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Win Rate Progress Bar */}
                      <div className="mt-3">
                        <div className="w-full h-1 bg-ink-900 rounded-full overflow-hidden">
                          <div className={`h-full ${barClass}`} style={{ width: `${rs.winRate}%` }} />
                        </div>
                      </div>

                      {/* Stats Row */}
                      <div className="grid grid-cols-3 gap-2 mt-3 pt-2.5 border-t border-line/10 text-center">
                        <div>
                          <span className="text-[9px] uppercase tracking-wider text-muted font-bold block">Avg ACS</span>
                          <span className="text-xs font-extrabold text-white mt-0.5 block">{rs.avgAcs}</span>
                        </div>
                        <div>
                          <span className="text-[9px] uppercase tracking-wider text-muted font-bold block">Win Rate</span>
                          <span className="text-xs font-extrabold text-white mt-0.5 block">{rs.winRate}%</span>
                        </div>
                        <div>
                          <span className="text-[9px] uppercase tracking-wider text-muted font-bold block">Games</span>
                          <span className="text-xs font-extrabold text-white mt-0.5 block">{rs.games}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8 text-sm text-muted">No role performance data recorded.</div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-line/30 text-xs text-muted leading-relaxed">
            <strong className="text-brand-red font-bold block uppercase text-[10px] tracking-wider mb-0.5">Role Insight:</strong>
            {vm.bestRole 
              ? `You excel most on ${vm.bestRole.role} with a ${vm.bestRole.winRate}% Win Rate. Keep playing this role to climb.` 
              : "Flex player profile. Master one role to gain consistent rank rating."}
          </div>
        </Panel>

        {/* Panel 6: Help & Help Center */}
        <Panel className="p-5 flex flex-col justify-between border-dashed">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <HelpCircle size={18} className="text-muted" />
              <h3 className="text-xs font-black uppercase tracking-wider text-muted font-bold">Analysis Guide</h3>
            </div>
            
            <p className="mt-4 text-xs text-muted leading-relaxed">
              These diagnostics are calculated in real-time by analyzing spatial coordinates, kill feed timestamps, purchase history, and recoil dynamics across your match history. Use these to target your daily custom lobby drills.
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-line/30 text-xs text-muted leading-relaxed">
            <strong className="text-muted font-bold block uppercase text-[10px] tracking-wider mb-0.5">Status:</strong>
            All telemetry systems nominal. Diagnostic report complete.
          </div>
        </Panel>

      </div>
    </div>

      {/* Actionable tips */}
      <div>
        <SectionTitle accent="blue">Actionable Training Plan</SectionTitle>
        <div className="grid gap-4 md:grid-cols-3">
          {vm.tips.map((t) => {
            // Helper to determine meta data per tip category
            let icon = <Zap size={18} className="text-amber-400" />;
            let duration = "Per Round";
            let frequency = "In-Game Focus";
            let focus = "Tactical Control";

            const cat = t.category.toLowerCase();
            if (cat.includes('mechanical')) {
              icon = <Target size={18} className="text-brand-red animate-pulse" />;
              duration = "10-15 Mins";
              frequency = "Daily Drill";
              focus = "Aim & Reflex";
            } else if (cat.includes('macro') || cat.includes('map')) {
              icon = <Compass size={18} className="text-brand-blue" />;
              duration = "1 Match";
              frequency = "Custom Lobby";
              focus = "Map Control";
            }

            return (
              <Panel
                key={t.category}
                glow={t.accent}
                className="flex flex-col justify-between p-5 rounded-2xl border border-line/45 bg-ink-800/40 hover:scale-[1.01] hover:border-line transition duration-300"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {icon}
                      <span className={`text-[10px] font-black uppercase tracking-[0.2em] ${t.accent === 'red' ? 'text-brand-red' : 'text-brand-blue'}`}>
                        {t.category}
                      </span>
                    </div>
                    <span className="rounded-lg bg-ink-900/60 border border-line/20 px-2 py-0.5 text-[9px] font-black text-muted flex items-center gap-1">
                      <Clock size={10} />
                      {duration}
                    </span>
                  </div>
                  
                  <div className="mt-3.5 text-base font-black text-white uppercase tracking-wider">
                    {t.title}
                  </div>
                  
                  <p className="mt-2.5 text-xs leading-relaxed text-muted font-medium">
                    {t.body}
                  </p>
                </div>
                
                <div className="mt-4 pt-3.5 border-t border-line/30 flex items-center justify-between">
                  <span className="text-[10px] font-bold text-muted flex items-center gap-1.5">
                    <Award size={12} className={t.accent === 'red' ? 'text-brand-red' : 'text-brand-blue'} />
                    Focus: <span className="text-white font-extrabold">{focus}</span>
                  </span>
                  <span className="text-[9px] font-black text-muted uppercase tracking-widest bg-ink-900/40 px-2 py-0.5 rounded border border-line/10">
                    {frequency}
                  </span>
                </div>
              </Panel>
            );
          })}
        </div>
      </div>
    </section>
  );
}
