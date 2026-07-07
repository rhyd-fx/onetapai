import { AnalyzeResponse, Telemetry, MapStats, WeaponStats, DistanceAimStats, EconomyEfficiency, SideBias, HardwareCheck } from './api';

export const VALORANT_SEASONS: Record<string, string> = {
  // Episode 1
  "3f61c772-4560-cd3f-5d3f-a7ab5abda6b3": "E1: A1",
  "0530b9c4-4980-f2ee-df5d-09864cd00542": "E1: A2",
  "46ea6166-4573-1128-9cea-60a15640059b": "E1: A3",
  
  // Episode 2
  "97b6e739-44cc-ffa7-49ad-398ba502ceb0": "E2: A1",
  "ab57ef51-4e59-da91-cc8d-51a5a2b9b8ff": "E2: A2",
  "52e9749a-429b-7060-99fe-4595426a0cf7": "E2: A3",
  
  // Episode 3
  "2a27e5d2-4d30-c9e2-b15a-93b8909a442c": "E3: A1",
  "4cb622e1-4244-6da3-7276-8daaf1c01be2": "E3: A2",
  "a16955a5-4ad0-f761-5e9e-389df1c892fb": "E3: A3",
  
  // Episode 4
  "573f53ac-41a5-3a7d-d9ce-d6a6298e5704": "E4: A1",
  "d929bc38-4ab6-7da4-94f0-ee84f8ac141e": "E4: A2",
  "3e47230a-463c-a301-eb7d-67bb60357d4f": "E4: A3",
  
  // Episode 5
  "67e373c7-48f7-b422-641b-079ace30b427": "E5: A1",
  "7a85de9a-4032-61a9-61d8-f4aa2b4a84b6": "E5: A2",
  "aca29595-40e4-01f5-3f35-b1b3d304c96e": "E5: A3",
  
  // Episode 6
  "9c91a445-4f78-1baa-a3ea-8f8aadf4914d": "E6: A1",
  "34093c29-4306-43de-452f-3f944bde22be": "E6: A2",
  "2de5423b-4aad-02ad-8d9b-c0a931958861": "E6: A3",
  
  // Episode 7
  "0981a882-4e7d-371a-70c4-c3b4f46c504a": "E7: A1",
  "03dfd004-45d4-ebfd-ab0a-948ce780dac4": "E7: A2",
  "4401f9fd-4170-2e4c-4bc3-f3b4d7d150d1": "E7: A3",
  
  // Episode 8
  "ec876e6c-43e8-fa63-ffc1-2e8d4db25525": "E8: A1",
  "22d10d66-4d2a-a340-6c54-408c7bd53807": "E8: A2",
  "4539cac3-47ae-90e5-3d01-b3812ca3274e": "E8: A3",
  
  // Episode 9
  "52ca6698-41c1-e7de-4008-8994d2221209": "E9: A1",
  "292f58db-4c17-89a7-b1c0-ba988f0e9d98": "E9: A2",
  "dcde7346-4085-de4f-c463-2489ed47983b": "E9: A3",
  
  // V25
  "476b0893-4c2e-abd6-c5fe-708facff0772": "V25: A1",
  "16118998-4705-5813-86dd-0292a2439d90": "V25: A2",
  "aef237a0-494d-3a14-a1c8-ec8de84e309c": "V25: A3",
  "ac12e9b3-47e6-9599-8fa1-0bb473e5efc7": "V25: A4",
  "5adc33fa-4f30-2899-f131-6fba64c5dd3a": "V25: A5",
  "4c4b8cff-43eb-13d3-8f14-96b783c90cd2": "V25: A6",
  
  // V26
  "3ea2b318-423b-cf86-25da-7cbb0eefbe2d": "V26: A1",
  "9d85c932-4820-c060-09c3-668636d4df1b": "V26: A2",
  "ce2783e8-44fc-dd48-3da3-33b5ba6c4a22": "V26: A3",
  "4f0864e2-40af-28a4-de2c-0e9e64e75f23": "V26: A4",
  "8102cd81-43a0-d0d7-bd59-47b8fe9bed1b": "V26: A5",
  "d816f426-48ea-f052-117f-9697a155b319": "V26: A6"
};

export function getSeasonName(seasonId: string): string {
  if (VALORANT_SEASONS[seasonId]) {
    return VALORANT_SEASONS[seasonId];
  }
  const shortId = seasonId.substring(0, 8).toUpperCase();
  return `Act (${shortId})`;
}

export interface MapPerf {
  map: string;
  games: number;
  avgAcs: number;
  winRate: number;
}

export interface Tip {
  category: string;
  title: string;
  body: string;
  accent: 'red' | 'blue';
}

export interface DashboardVM {
  riotId: string;
  region: string;
  mainAgent: string;
  cardUrl?: string | null;
  tier: { label: string; hint: string };
  stats: {
    kd: string;
    hsPct: number;
    acs: number;
    winRate: number | null;
    kills: number;
    deaths: number;
    games: number;
  };
  bestMap?: MapPerf;
  worstMap?: MapPerf;
  consistency: { label: string; cv: number };
  deficiencies: string[];
  quote: string;
  summary: string[];
  tips: Tip[];
  acsChart: { match: string; acs: number }[];
  telemetry?: Telemetry;
  topMaps: MapStats[];
  topWeapons: WeaponStats[];
  aimByDistance: DistanceAimStats[];
  economyEfficiency?: EconomyEfficiency;
  economySplit?: AnalyzeResponse['economy_split'];
  economyImpactLabel?: string;
  sideBias?: SideBias;
  hardwareCheck?: HardwareCheck;
  roleStats: RolePerformance[];
  bestRole?: RolePerformance;
  matchupDiagnostics?: AnalyzeResponse['matchup_diagnostics'];
}

export interface RolePerformance {
  role: 'Duelist' | 'Initiator' | 'Controller' | 'Sentinel';
  games: number;
  wins: number;
  winRate: number;
  avgAcs: number;
}

function getBrutalQuote(
  hs: number,
  kd: number,
  cv: number,
  acs: number,
  winRate: number | null,
  edpi: number,
  earlyDeathPct: number,
  ecoThrows: number
): string {
  const pools: Record<string, string[]> = {
    low_hs: [
      `Your headshot rate is only ${hs.toFixed(0)}%. You're practically shooting their shoelaces. Raise your crosshair before you end up sweeping the floor.`,
      `With a ${hs.toFixed(0)}% headshot rate, you're aiming at the chest like it's a target circle. Settle the crosshair back to head level.`,
      `Chest-level aiming is for players who are afraid of heights. Settle your cursor higher; Valorant is a vertical game.`
    ],
    high_edpi: [
      `Your sensitivity is ${edpi.toFixed(0)} eDPI. Are you playing on a postage stamp? A single sneeze and your agent does a 720.`,
      `You're playing with ${edpi.toFixed(0)} eDPI. Even pro players wouldn't dare touch this. Bring that down unless you like drawing circles on screen.`,
      `Your mouse sensitivity is so high it looks like you have a caffeine addiction. Lower the DPI and start tracing your targets.`
    ],
    early_deaths: [
      `You die in the first 15 seconds of defense rounds in ${earlyDeathPct.toFixed(0)}% of matches. Are you defending or just playing entry fragger for the enemy team? Stop dry-peeking the barrier.`,
      `Your survival time on Defense is shorter than a Classic reload. Settle into site and hold an angle instead of ego-peeking.`,
      `Holding site doesn't mean offering yourself as first blood. Let them come to you; you're not Rambo.`
    ],
    eco_throws: [
      `You lost ${ecoThrows} rounds while fully loaded against saving pistols. Buying a Vandal just to donate it to a Sheriff user is not a charity model Riot supports.`,
      `Losing full-buys to enemy eco saves is a special talent. Stop dry-peeking close corners when you hold the range advantage.`,
      `Losing to eco saves means you're playing overconfident. Stop rushing close-range fights against cheap pistols.`
    ],
    low_kd: [
      `A ${kd.toFixed(2)} K/D ratio means you're basically a walking ultimate orb for the enemy team. Play with your teammates, don't feed.`,
      `Your K/D is ${kd.toFixed(2)}. The only thing you're carrying is the enemy team's morale.`,
      `You are dying more than you kill. Try trade-peeking or holding off angles instead of fighting 1v3s.`
    ],
    high_variance: [
      `Consistent? No, you're a slot machine. One match you're Radiant, the next you're Iron. Find some consistency before you queue again.`,
      `A consistency rating of 'Feast or Famine' means your team is playing Russian roulette every time you queue. Settle into a routine.`,
      `Your ACS swings wilder than a pendulum. Stop relying on lucky rounds and build a stable baseline.`
    ],
    low_winrate: [
      `With a ${winRate?.toFixed(0)}% win rate, you are doing a speedrun to the rank below you. Slow down and play with your team.`,
      `A ${winRate?.toFixed(0)}% win rate is tragic. Have you tried turning your monitor on?`,
      `You are losing most of your games. Stop blaming your teammates; look at your defense early deaths and eco throws.`
    ],
    high_acs: [
      `Nice individual ACS (${acs.toFixed(0)}), but you're still losing. Too bad Valorant is a team game. Try using your microphone next time.`,
      `You get a lot of combat points (${acs.toFixed(0)} ACS) but do you get round wins? Stop baiting your team for useless exit kills.`,
      `High ACS doesn't matter if your win rate is low. Play for the team, not for the scoreboard.`
    ],
    generic: [
      `${acs.toFixed(0)} ACS across ${winRate?.toFixed(0)}% wins. Your foundation is there, but your positioning needs major study.`,
      `You play like a solid development project. Settle down, trade your teammates, and stop taking dry duels.`
    ]
  };

  const triggered: string[] = [];
  if (hs < 15) triggered.push('low_hs');
  if (edpi > 400) triggered.push('high_edpi');
  if (earlyDeathPct > 20) triggered.push('early_deaths');
  if (ecoThrows > 0) triggered.push('eco_throws');
  if (kd < 0.95) triggered.push('low_kd');
  if (cv > 0.4) triggered.push('high_variance');
  if (winRate != null && winRate < 45) triggered.push('low_winrate');
  if (acs > 250) triggered.push('high_acs');

  if (triggered.length === 0) {
    triggered.push('generic');
  }

  const category = triggered[Math.floor(Math.random() * triggered.length)];
  const pool = pools[category] || pools['generic'];
  return pool[Math.floor(Math.random() * pool.length)];
}

function tierFor(acs: number): { label: string; hint: string } {
  if (acs >= 300) return { label: 'RADIANT FORM', hint: 'Elite output' };
  if (acs >= 250) return { label: 'IMMORTAL PACE', hint: 'Carry threat' };
  if (acs >= 200) return { label: 'DIAMOND TIER', hint: 'Solid impact' };
  if (acs >= 150) return { label: 'GOLD TIER', hint: 'Developing' };
  return { label: 'CALIBRATING', hint: 'Building sample' };
}

function consistencyFor(cv: number): string {
  if (cv < 0.15) return 'Rock Solid';
  if (cv < 0.3) return 'Consistent';
  if (cv < 0.5) return 'Streaky';
  return 'Feast or Famine';
}

function mapPerf(traj: AnalyzeResponse['acs_trajectory']): { best?: MapPerf; worst?: MapPerf } {
  const byMap = new Map<string, { acs: number[]; wins: number }>();
  for (const p of traj) {
    const e = byMap.get(p.map) ?? { acs: [], wins: 0 };
    e.acs.push(p.acs);
    if (p.won) e.wins += 1;
    byMap.set(p.map, e);
  }

  const allAcs = traj.map((p) => p.acs);
  const overallAvgAcs = allAcs.length > 0 ? allAcs.reduce((a, b) => a + b, 0) / allAcs.length : 250;

  const perf = [...byMap.entries()].map(([map, e]) => {
    const games = e.acs.length;
    const avgAcs = e.acs.reduce((a, b) => a + b, 0) / games;
    const winRate = (e.wins / games) * 100;

    // 1. Bayesian Shrinkage (Prior Weight K = 2)
    const k = 2;
    const weightedAcs = (avgAcs * games + overallAvgAcs * k) / (games + k);

    // 2. Win Rate Nudge (+10% for 100% WR, -10% for 0% WR)
    const multiplier = 1.0 + (winRate / 100 - 0.5) * 0.2;
    const impactScore = weightedAcs * multiplier;

    return {
      map,
      games,
      avgAcs,
      winRate,
      impactScore,
    };
  });

  if (perf.length === 0) return {};
  const sorted = [...perf].sort((a, b) => b.impactScore - a.impactScore);
  return {
    best: sorted[0],
    worst: sorted.length > 1 ? sorted[sorted.length - 1] : undefined,
  };
}

function impactTip(tel?: Telemetry): Tip {
  if (tel?.movement_error_pct != null && tel.movement_error_pct > 25) {
    return {
      category: 'Round Impact',
      title: 'Cut the free deaths',
      body: `You die dealing zero damage in ${tel.movement_error_pct.toFixed(0)}% of your death rounds — usually peeking while moving. Counter-strafe and stop before the first bullet.`,
      accent: 'red',
    };
  }
  if (tel?.opening_duel_win_pct != null && tel.opening_duel_win_pct < 45) {
    return {
      category: 'Round Impact',
      title: 'Rethink your entries',
      body: `You win only ${tel.opening_duel_win_pct.toFixed(0)}% of opening duels. Take fights with a trade behind you, or hold for info instead of dry-peeking.`,
      accent: 'blue',
    };
  }
  if (tel?.multikill_pct != null) {
    return {
      category: 'Round Impact',
      title: 'Stack your rounds',
      body: `${tel.multikill_pct.toFixed(0)}% of your rounds are multi-kills. Reposition after a kill to catch the trade and turn singles into doubles.`,
      accent: 'blue',
    };
  }
  return {
    category: 'Round Impact',
    title: 'Play for impact',
    body: 'Trade your teammates and reposition after kills to compound round wins.',
    accent: 'blue',
  };
}

const AGENT_ROLES: Record<string, 'Duelist' | 'Initiator' | 'Controller' | 'Sentinel'> = {
  jett: 'Duelist', raze: 'Duelist', neon: 'Duelist', reyna: 'Duelist', phoenix: 'Duelist', yoru: 'Duelist', iso: 'Duelist', waylay: 'Duelist',
  sova: 'Initiator', fade: 'Initiator', breach: 'Initiator', skye: 'Initiator', 'kay/o': 'Initiator', gekko: 'Initiator', tejo: 'Initiator',
  omen: 'Controller', viper: 'Controller', brimstone: 'Controller', astra: 'Controller', harbor: 'Controller', clove: 'Controller', miks: 'Controller',
  sage: 'Sentinel', cypher: 'Sentinel', killjoy: 'Sentinel', chamber: 'Sentinel', deadlock: 'Sentinel', vyse: 'Sentinel', veto: 'Sentinel'
};

export function calculateRolePerformance(trajectory: AnalyzeResponse['acs_trajectory']): RolePerformance[] {
  const roleGroups: Record<string, { games: number; wins: number; totalAcs: number }> = {};
  
  for (const m of trajectory) {
    if (!m.agent) continue;
    const role = AGENT_ROLES[m.agent.toLowerCase()];
    if (!role) continue;
    
    if (!roleGroups[role]) {
      roleGroups[role] = { games: 0, wins: 0, totalAcs: 0 };
    }
    roleGroups[role].games += 1;
    if (m.won) roleGroups[role].wins += 1;
    roleGroups[role].totalAcs += m.acs;
  }
  
  return Object.entries(roleGroups).map(([role, stats]) => ({
    role: role as 'Duelist' | 'Initiator' | 'Controller' | 'Sentinel',
    games: stats.games,
    wins: stats.wins,
    winRate: Math.round((stats.wins / stats.games) * 100),
    avgAcs: Math.round(stats.totalAcs / stats.games),
  }));
}

export function buildViewModel(r: AnalyzeResponse): DashboardVM {
  const p = r.player_profile;
  const hs = (p.headshot_pct ?? 0) * 100;
  const bs = (p.bodyshot_pct ?? 0) * 100;
  const acsVals = r.acs_trajectory.map((t) => t.acs);
  const mean = acsVals.length ? acsVals.reduce((a, b) => a + b, 0) / acsVals.length : 0;
  const variance = acsVals.length
    ? acsVals.reduce((a, b) => a + (b - mean) ** 2, 0) / acsVals.length
    : 0;
  const cv = mean > 0 ? Math.sqrt(variance) / mean : 0;

  const { best, worst } = mapPerf(r.acs_trajectory);
  const deficiencies = r.aim_profile.available ? r.aim_profile.deficiencies ?? [] : [];

  const topDef = deficiencies[0];
  const edpi = r.hardware_check?.edpi ?? 280;
  const earlyDeathPct = r.side_bias?.early_defense_death_pct ?? 0;
  const ecoThrows = r.economy_efficiency?.eco_throws ?? 0;

  const roleStats = calculateRolePerformance(r.acs_trajectory);
  const bestRole = [...roleStats]
    .filter(rs => rs.games > 0)
    .sort((a, b) => b.winRate - a.winRate || b.avgAcs - a.avgAcs)[0];

  const quote = getBrutalQuote(
    hs,
    p.kills / Math.max(1, p.deaths),
    cv,
    p.avg_acs,
    p.win_rate,
    edpi,
    earlyDeathPct,
    ecoThrows
  );

  const summary: string[] = [
    `${p.avg_acs.toFixed(0)} avg ACS · ${hs.toFixed(0)}% headshots · ${(p.kills / Math.max(1, p.deaths)).toFixed(2)} K/D`,
    best ? `Best on ${best.map} (${best.avgAcs.toFixed(0)} ACS)` : `Playing ${p.main_agent ?? 'flex'}`,
    worst ? `Weakest on ${worst.map} — prioritize VOD review there` : `Consistency: ${consistencyFor(cv)}`,
  ];

  const tips: Tip[] = [
    {
      category: 'Mechanical',
      title: topDef === 'crosshair_too_low' ? 'Raise your crosshair'
        : topDef === 'moving_while_shooting' ? 'Counter-strafe drills'
        : 'Aim routine',
      body: topDef === 'crosshair_too_low'
        ? 'Pre-aim head height on every angle. 10 min head-level tracking in the Range before you queue.'
        : topDef === 'moving_while_shooting'
        ? 'ADAD counter-strafe: stop fully before the first bullet. Reward only first-shot heads.'
        : 'Warm up 15 min: static clicks, then dynamic tracking, then a DM.',
      accent: 'red',
    },
    {
      category: 'Macro / Map Control',
      title: worst ? `Fix your ${worst.map} defaults` : 'Trade discipline',
      body: worst
        ? `Your ${worst.map} ACS lags ${(best ? best.avgAcs - worst.avgAcs : 0).toFixed(0)} pts behind your best map. Study one pro default per side.`
        : 'Peek with a trade behind you. Don\'t take dry duels without info.',
      accent: 'blue',
    },
    impactTip(r.telemetry),
  ];

  let economyImpactLabel = "Balanced Economy";
  if (r.economy_split) {
    const eco = r.economy_split.eco?.avg_acs ?? 0;
    const half = r.economy_split.half_buy?.avg_acs ?? 0;
    const force = r.economy_split.force_buy?.avg_acs ?? 0;
    const full = r.economy_split.full_buy?.avg_acs ?? 0;
    
    if (full > 0 && half > 0 && full < half - 10) {
      economyImpactLabel = "Full-Buy Underperformer";
    } else if (eco > 160) {
      economyImpactLabel = "Eco Round Threat";
    } else if (full > 210) {
      economyImpactLabel = "Full-Buy Heavyweight";
    }
  }

  return {
    riotId: `${p.game_name}#${p.tag_line}`,
    region: p.region?.toUpperCase() ?? '',
    mainAgent: p.main_agent ?? 'Flex',
    cardUrl: p.card_uuid ? `https://media.valorant-api.com/playercards/${p.card_uuid}/wideart.png` : null,
    tier: tierFor(p.avg_acs),
    stats: {
      kd: (p.kills / Math.max(1, p.deaths)).toFixed(2),
      hsPct: hs,
      acs: p.avg_acs,
      winRate: p.win_rate,
      kills: p.kills,
      deaths: p.deaths,
      games: p.games,
    },
    bestMap: best,
    worstMap: worst,
    consistency: { label: consistencyFor(cv), cv },
    deficiencies,
    quote,
    summary,
    tips,
    acsChart: r.acs_trajectory.map((t, i) => ({
      match: String(i + 1),
      acs: t.acs,
      won: t.won,
      agent: t.agent,
      map: t.map,
      tier_name: t.tier_name
    })),
    telemetry: r.telemetry,
    topMaps: r.top_maps ?? [],
    topWeapons: r.top_weapons ?? [],
    aimByDistance: r.aim_by_distance ?? [],
    economyEfficiency: r.economy_efficiency,
    economySplit: r.economy_split,
    economyImpactLabel,
    sideBias: r.side_bias,
    hardwareCheck: r.hardware_check,
    roleStats,
    bestRole,
    matchupDiagnostics: r.matchup_diagnostics,
  };
}
