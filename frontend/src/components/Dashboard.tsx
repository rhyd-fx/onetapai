"use client";

import { useState, useEffect } from 'react';
import { Search, SlidersHorizontal, LogOut, User as UserIcon, Sparkles, Target, BrainCircuit, Activity, ChevronRight, Gamepad2 } from 'lucide-react';
import { analyzePlayer, AnalyzeResponse, fetchRecentSearches } from '@/lib/api';
import { buildViewModel, getSeasonName } from '@/lib/viewModel';
import { useAuth } from '@/context/AuthContext';
import AuthOverlay from './dashboard/AuthOverlay';
import ProfileCard from './dashboard/ProfileCard';
import HeroVisual from './dashboard/HeroVisual';
import MapsAndTelemetry from './dashboard/MapsAndTelemetry';
import TopWeapons from './dashboard/TopWeapons';
import CoachAnalysis from './dashboard/CoachAnalysis';
import CoachPanel from './dashboard/CoachPanel';
import ShareCard from './dashboard/ShareCard';
import { Panel, SectionTitle } from './dashboard/primitives';
import ACSTrajectoryChart from './ACSTrajectoryChart';
import MapHeatmap from './MapHeatmap';

const REGIONS = ['na', 'eu', 'ap', 'kr', 'br', 'latam'];

const AGENT_ICONS: Record<string, string> = {
  "gekko": "https://media.valorant-api.com/agents/e370fa57-4757-3604-3648-499e1f642d3f/displayicon.png",
  "fade": "https://media.valorant-api.com/agents/dade69b4-4f5a-8528-247b-219e5a1facd6/displayicon.png",
  "breach": "https://media.valorant-api.com/agents/5f8d3a7f-467b-97f3-062c-13acf203c006/displayicon.png",
  "deadlock": "https://media.valorant-api.com/agents/cc8b64c8-4b25-4ff9-6e7f-37b4da43d235/displayicon.png",
  "tejo": "https://media.valorant-api.com/agents/b444168c-4e35-8076-db47-ef9bf368f384/displayicon.png",
  "raze": "https://media.valorant-api.com/agents/f94c3b30-42be-e959-889c-5aa313dba261/displayicon.png",
  "chamber": "https://media.valorant-api.com/agents/22697a3d-45bf-8dd7-4fec-84a9e28c69d7/displayicon.png",
  "kay/o": "https://media.valorant-api.com/agents/601dbbe7-43ce-be57-2a40-4abd24953621/displayicon.png",
  "skye": "https://media.valorant-api.com/agents/6f2a04ca-43e0-be17-7f36-b3908627744d/displayicon.png",
  "cypher": "https://media.valorant-api.com/agents/117ed9e3-49f3-6512-3ccf-0cada7e3823b/displayicon.png",
  "sova": "https://media.valorant-api.com/agents/320b2a48-4d9b-a075-30f1-1f93a9b638fa/displayicon.png",
  "miks": "https://media.valorant-api.com/agents/7c8a4701-4de6-9355-b254-e09bc2a34b72/displayicon.png",
  "killjoy": "https://media.valorant-api.com/agents/1e58de9c-4950-5125-93e9-a0aee9f98746/displayicon.png",
  "harbor": "https://media.valorant-api.com/agents/95b78ed7-4637-86d9-7e41-71ba8c293152/displayicon.png",
  "vyse": "https://media.valorant-api.com/agents/efba5359-4016-a1e5-7626-b1ae76895940/displayicon.png",
  "viper": "https://media.valorant-api.com/agents/707eab51-4836-f488-046a-cda6bf494859/displayicon.png",
  "phoenix": "https://media.valorant-api.com/agents/eb93336a-449b-9c1b-0a54-a891f7921d69/displayicon.png",
  "veto": "https://media.valorant-api.com/agents/92eeef5d-43b5-1d4a-8d03-b3927a09034b/displayicon.png",
  "astra": "https://media.valorant-api.com/agents/41fb69c1-4189-7b37-f117-bcaf1e96f1bf/displayicon.png",
  "brimstone": "https://media.valorant-api.com/agents/9f0d8ba9-4140-b941-57d3-a7ad57c6b417/displayicon.png",
  "iso": "https://media.valorant-api.com/agents/0e38b510-41a8-5780-5e8f-568b2a4f2d6c/displayicon.png",
  "clove": "https://media.valorant-api.com/agents/1dbf2edd-4729-0984-3115-daa5eed44993/displayicon.png",
  "neon": "https://media.valorant-api.com/agents/bb2a4828-46eb-8cd1-e765-15848195d751/displayicon.png",
  "yoru": "https://media.valorant-api.com/agents/7f94d92c-4234-0a36-9646-3a87eb8b5c89/displayicon.png",
  "waylay": "https://media.valorant-api.com/agents/df1cb487-4902-002e-5c17-d28e83e78588/displayicon.png",
  "sage": "https://media.valorant-api.com/agents/569fdd95-4d10-43ab-ca70-79becc718b46/displayicon.png",
  "reyna": "https://media.valorant-api.com/agents/a3bfb853-43b2-7238-a4f1-ad90e9e46bcc/displayicon.png",
  "omen": "https://media.valorant-api.com/agents/8e253930-4c05-31dd-1b6c-968525494517/displayicon.png",
  "jett": "https://media.valorant-api.com/agents/add6443a-41bd-e414-f6ad-e58d267f4e95/displayicon.png",
  "kayo": "https://media.valorant-api.com/agents/601dbbe7-43ce-be57-2a40-4abd24953621/displayicon.png"
};

const RANK_ICONS: Record<string, string> = {
  unranked: "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/0/largeicon.png",
  "iron 1": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/3/largeicon.png",
  "iron 2": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/4/largeicon.png",
  "iron 3": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/5/largeicon.png",
  "bronze 1": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/6/largeicon.png",
  "bronze 2": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/7/largeicon.png",
  "bronze 3": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/8/largeicon.png",
  "silver 1": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/9/largeicon.png",
  "silver 2": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/10/largeicon.png",
  "silver 3": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/11/largeicon.png",
  "gold 1": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/12/largeicon.png",
  "gold 2": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/13/largeicon.png",
  "gold 3": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/14/largeicon.png",
  "platinum 1": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/15/largeicon.png",
  "platinum 2": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/16/largeicon.png",
  "platinum 3": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/17/largeicon.png",
  "diamond 1": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/18/largeicon.png",
  "diamond 2": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/19/largeicon.png",
  "diamond 3": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/20/largeicon.png",
  "ascendant 1": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/21/largeicon.png",
  "ascendant 2": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/22/largeicon.png",
  "ascendant 3": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/23/largeicon.png",
  "immortal 1": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/24/largeicon.png",
  "immortal 2": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/25/largeicon.png",
  "immortal 3": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/26/largeicon.png",
  "radiant": "https://media.valorant-api.com/competitivetiers/03621f52-342b-cf4e-4f86-9350a49c6d04/27/largeicon.png"
};

function formatTimeAgo(dateStr: string) {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  } catch {
    return '';
  }
}

function AgentAvatar({ agentName, iconUrl }: { agentName: string; iconUrl: string }) {
  const [error, setError] = useState(false);
  
  if (error || !iconUrl) {
    const name = (agentName || 'Jett').trim();
    const initials = name.substring(0, 2).toUpperCase();
    
    const roleColors: Record<string, string> = {
      jett: 'from-brand-red to-orange-500',
      raze: 'from-brand-red to-orange-500',
      neon: 'from-brand-red to-orange-500',
      reyna: 'from-brand-red to-orange-500',
      phoenix: 'from-brand-red to-orange-500',
      yoru: 'from-brand-red to-orange-500',
      iso: 'from-brand-red to-orange-500',
      sova: 'from-amber-500 to-yellow-400',
      fade: 'from-amber-500 to-yellow-400',
      breach: 'from-amber-500 to-yellow-400',
      skye: 'from-amber-500 to-yellow-400',
      kayo: 'from-amber-500 to-yellow-400',
      'kay/o': 'from-amber-500 to-yellow-400',
      gekko: 'from-amber-500 to-yellow-400',
      omen: 'from-purple-600 to-indigo-500',
      viper: 'from-purple-600 to-indigo-500',
      brimstone: 'from-purple-600 to-indigo-500',
      astra: 'from-purple-600 to-indigo-500',
      harbor: 'from-purple-600 to-indigo-500',
      clove: 'from-purple-600 to-indigo-500',
      sage: 'from-brand-blue to-teal-500',
      cypher: 'from-brand-blue to-teal-500',
      killjoy: 'from-brand-blue to-teal-500',
      chamber: 'from-brand-blue to-teal-500',
      deadlock: 'from-brand-blue to-teal-500',
    };
    
    const gradient = roleColors[name.toLowerCase()] || 'from-zinc-600 to-zinc-800';
    return (
      <div className={`w-full h-full bg-gradient-to-br ${gradient} flex items-center justify-center font-black text-white text-[11px] tracking-wider rounded-lg border border-white/10`}>
        {initials}
      </div>
    );
  }
  
  return (
    <img 
      src={iconUrl} 
      alt={agentName} 
      className="w-full h-full object-cover"
      onError={() => setError(true)}
    />
  );
}

export default function Dashboard() {
  const { isLoggedIn, user, logout, authLoading, refreshSession } = useAuth();
  const [riotId, setRiotId] = useState('');
  const [region, setRegion] = useState('na');
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSeason, setSelectedSeason] = useState<string | null>(null);
  const [competitiveOnly, setCompetitiveOnly] = useState(true);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  useEffect(() => {
    if (isLoggedIn) {
      fetchRecentSearches().then(setRecentSearches).catch(console.error);
    }
  }, [isLoggedIn]);

  if (authLoading) {
    return (
      <div className="min-h-screen w-full flex flex-col items-center justify-center bg-ink-950 text-white select-none">
        <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-brand-red to-brand-red-soft flex items-center justify-center border border-white/10 animate-bounce mb-4 shadow-lg shadow-brand-red/20">
          <span className="h-2 w-2 rounded-full bg-white" />
        </div>
        <div className="text-[10px] font-black uppercase tracking-widest text-brand-blue/80 animate-pulse">Connecting to OneTap AI networks...</div>
      </div>
    );
  }

  if (!isLoggedIn) {
    return <AuthOverlay />;
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!riotId.includes('#')) {
      setError('Enter a Riot ID as Name#Tag');
      return;
    }
    setLoading(true);
    setError(null);
    setSelectedSeason(null);
    setCompetitiveOnly(true);
    try {
      setResult(await analyzePlayer(riotId.trim(), region));
      refreshSession();
      fetchRecentSearches().then(setRecentSearches).catch(console.error);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = async (newSeason: string | null, newComp: boolean) => {
    if (!result) return;
    setLoading(true);
    setError(null);
    try {
      const fullId = `${result.player_profile.game_name}#${result.player_profile.tag_line}`;
      const updated = await analyzePlayer(fullId, region, {
        seasonId: newSeason,
        competitiveOnly: newComp,
        skipSync: true,
      });
      setResult(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Filter failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDemoPlayer = async (id: string, playRegion = 'na') => {
    setRiotId(id);
    setRegion(playRegion);
    setLoading(true);
    setError(null);
    setSelectedSeason(null);
    setCompetitiveOnly(true);
    try {
      setResult(await analyzePlayer(id.trim(), playRegion));
      refreshSession();
      fetchRecentSearches().then(setRecentSearches).catch(console.error);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const vm = result ? buildViewModel(result) : null;
  const heatmapMap = vm?.bestMap?.map ?? result?.acs_trajectory[0]?.map;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 md:px-8">
      {/* Top bar + search */}
      <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="text-2xl font-black tracking-tight">
          ONETAP<span className="text-brand-red">AI</span>
        </div>
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto md:justify-end">
          {/* User Profile Badge & Logout button */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-white/5 bg-white/[0.02] text-xs font-bold text-white select-none">
            <UserIcon size={12} className="text-brand-blue" />
            <span>{user?.username}</span>
            <button 
              onClick={logout} 
              title="Log Out"
              className="ml-2 p-1 rounded hover:bg-white/5 text-muted hover:text-brand-red transition-colors cursor-pointer flex items-center justify-center"
            >
              <LogOut size={12} />
            </button>
          </div>

          <form onSubmit={submit} className="flex flex-1 items-center gap-2 md:flex-initial">
            <div className="relative flex-1 md:w-80">
              <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
              <input
                value={riotId}
                onChange={(e) => setRiotId(e.target.value)}
                placeholder="Riot ID  ·  Name#Tag"
                aria-label="Riot ID"
                className="w-full rounded-xl border border-line bg-ink-800/60 py-2.5 pl-9 pr-3 text-sm text-white outline-none placeholder:text-muted focus:border-brand-red/60"
              />
            </div>
            <select
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              aria-label="Region"
              className="rounded-xl border border-line bg-ink-800/60 px-2 py-2.5 text-sm text-white outline-none focus:border-brand-red/60"
            >
              {REGIONS.map((r) => (
                <option key={r} value={r}>{r.toUpperCase()}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={loading}
              className="glow-red rounded-xl bg-brand-red px-4 py-2.5 text-sm font-bold uppercase tracking-widest text-white transition hover:bg-brand-red-soft disabled:opacity-50"
            >
              {loading ? 'Analyzing…' : 'Analyze'}
            </button>
          </form>
        </div>
      </header>

      {error && (
        <div className="mb-6 rounded-xl border border-brand-red/40 bg-brand-red/10 px-4 py-3 text-sm text-brand-red-soft">
          {error}
        </div>
      )}

      {!vm ? (
        <EmptyState loading={loading} recentSearches={recentSearches} onSelectPlayer={handleSelectDemoPlayer} />
      ) : (
        <div className="space-y-8 animate-fade-in">
          {/* Diagnostic filters */}
          <div className="flex flex-col gap-4 rounded-2xl border border-line bg-ink-950/40 p-4 backdrop-blur-md sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-red/10 text-brand-red">
                <SlidersHorizontal size={18} />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Diagnostics Scope</h4>
                <p className="text-xs text-muted">Customize session focus and game filters</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              {/* Season Selection */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted">Season:</span>
                <select
                  value={selectedSeason || ''}
                  onChange={(e) => {
                    const val = e.target.value || null;
                    setSelectedSeason(val);
                    handleFilterChange(val, competitiveOnly);
                  }}
                  className="rounded-lg border border-line bg-ink-800/80 px-2.5 py-1.5 text-xs font-medium text-white outline-none focus:border-brand-red/60"
                >
                  <option value="">All Acts</option>
                  {(result?.seasons || []).map((s) => (
                    <option key={s} value={s}>
                      {getSeasonName(s)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Competitive toggle */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted">Mode:</span>
                <div className="flex rounded-lg border border-line bg-ink-800/80 p-0.5">
                  <button
                    type="button"
                    onClick={() => {
                      setCompetitiveOnly(true);
                      handleFilterChange(selectedSeason, true);
                    }}
                    className={`rounded-md px-3 py-1 text-xs font-medium transition ${
                      competitiveOnly
                        ? 'bg-brand-red text-white shadow-sm glow-red'
                        : 'text-muted hover:text-white'
                    }`}
                  >
                    Comp Only
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setCompetitiveOnly(false);
                      handleFilterChange(selectedSeason, false);
                    }}
                    className={`rounded-md px-3 py-1 text-xs font-medium transition ${
                      !competitiveOnly
                        ? 'bg-ink-700 text-white border border-line'
                        : 'text-muted hover:text-white'
                    }`}
                  >
                    All Modes
                  </button>
                </div>
              </div>
            </div>
          </div>
          {/* HERO BENTO */}
          <section className="grid gap-4 lg:grid-cols-3">
            <Panel glow="red" className="lg:col-span-2">
              <ProfileCard vm={vm} />
            </Panel>
            <Panel glow="blue" className="overflow-hidden p-2">
              <HeroVisual agent={vm.mainAgent} />
            </Panel>
          </section>

          <section className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <MapsAndTelemetry vm={vm} />
            </div>
            <div className="h-full flex flex-col min-h-0">
              <TopWeapons weapons={vm.topWeapons} />
            </div>
          </section>

          {/* TREND + HEATMAP */}
          <section className="grid gap-4 lg:grid-cols-2">
            <Panel className="p-5">
              <SectionTitle>ACS Trajectory · Session Tilt</SectionTitle>
              <ACSTrajectoryChart data={vm.acsChart} />
            </Panel>
            <Panel className="p-5">
              <SectionTitle accent="blue">Death / Kill Map{heatmapMap ? ` · ${heatmapMap}` : ''}</SectionTitle>
              <MapHeatmap riotId={vm.riotId} mapId={heatmapMap} />
            </Panel>
          </section>

          {/* Recent Match History Bento */}
          {result?.acs_trajectory && result.acs_trajectory.length > 0 && (
            <section>
              <Panel className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="w-1 h-6 rounded-full bg-gradient-to-b from-brand-blue to-brand-red" />
                    <SectionTitle>Recent Match History</SectionTitle>
                  </div>
                  <span className="text-[10px] uppercase tracking-widest text-muted/60 bg-white/[0.03] px-3 py-1 rounded-full border border-white/[0.06]">
                    Last {result.acs_trajectory.length} Matches
                  </span>
                </div>

                <div className="space-y-3">
                  {result.acs_trajectory.slice().reverse().map((m: any, i: number) => {
                    const win = m.won;
                    const kills = m.kills ?? 0;
                    const deaths = m.deaths ?? 0;
                    const assists = m.assists ?? 0;
                    const kdNum = deaths > 0 ? kills / deaths : kills;
                    const kdRatio = kdNum.toFixed(2);
                    const agentLower = (m.agent || 'Jett').toLowerCase().trim();
                    const iconUrl = AGENT_ICONS[agentLower] || 'https://media.valorant-api.com/agents/add6443a-41bd-e414-f6ad-e58d267f4e95/displayicon.png';

                    // KD color thresholds
                    const kdColor = kdNum >= 1 
                      ? 'text-emerald-400' 
                      : kdNum >= 0.75 
                        ? 'text-amber-400' 
                        : 'text-red-400';
                    const kdGlow = kdNum >= 1 
                      ? 'shadow-emerald-500/20 border-emerald-500/20 bg-emerald-500/[0.06]' 
                      : kdNum >= 0.75 
                        ? 'shadow-amber-500/20 border-amber-500/20 bg-amber-500/[0.06]' 
                        : 'shadow-red-500/20 border-red-500/20 bg-red-500/[0.06]';
                    
                    return (
                      <div 
                        key={m.match_id || i} 
                        className={`
                          group relative overflow-hidden rounded-2xl 
                          backdrop-blur-xl border transition-all duration-300 ease-out
                          hover:translate-x-1 hover:shadow-xl
                          ${win 
                            ? 'bg-gradient-to-r from-emerald-500/[0.05] via-emerald-500/[0.02] to-transparent border-emerald-500/[0.12] hover:border-emerald-500/[0.3] hover:shadow-emerald-500/10' 
                            : 'bg-gradient-to-r from-red-500/[0.05] via-red-500/[0.02] to-transparent border-red-500/[0.12] hover:border-red-500/[0.3] hover:shadow-red-500/10'
                          }
                        `}
                      >
                        {/* Left accent bar with glow */}
                        <div className={`absolute left-0 top-0 bottom-0 w-[3px] ${win ? 'bg-gradient-to-b from-emerald-300 via-emerald-500 to-emerald-700' : 'bg-gradient-to-b from-red-300 via-red-500 to-red-700'}`} />
                        <div className={`absolute left-0 top-0 bottom-0 w-2 blur-sm ${win ? 'bg-emerald-500/30' : 'bg-red-500/30'}`} />
                                            {/* Hover shimmer */}
                        <div className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none ${
                          win 
                            ? 'bg-gradient-to-r from-emerald-500/[0.06] via-transparent to-emerald-500/[0.02]' 
                            : 'bg-gradient-to-r from-red-500/[0.06] via-transparent to-red-500/[0.02]'
                        }`} />

                        <div className="relative flex items-center px-6 py-4 gap-6 justify-between flex-wrap md:flex-nowrap">
                          {/* Column 1: Agent Avatar + Map & Mode Details + Outcome/Time */}
                          <div className="flex items-center gap-4 min-w-[200px] flex-1 md:flex-initial">
                            {/* Avatar */}
                            <div className={`
                              relative w-14 h-14 rounded-2xl overflow-hidden flex-shrink-0
                              ring-1 shadow-lg transition-all duration-300 group-hover:scale-105
                              ${win ? 'ring-emerald-500/25 shadow-emerald-500/15 group-hover:ring-emerald-400/40' : 'ring-red-500/25 shadow-red-500/15 group-hover:ring-red-400/40'}
                            `}>
                              <div className="absolute inset-0 bg-ink-950/50 backdrop-blur-sm" />
                              <div className="relative w-full h-full flex items-center justify-center">
                                <AgentAvatar agentName={m.agent} iconUrl={iconUrl} />
                              </div>
                            </div>
                            
                            {/* Text description */}
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="font-extrabold text-white text-sm uppercase tracking-wider truncate">
                                  {m.agent || 'Jett'}
                                </span>
                                <span className="text-[10px] text-muted/40 font-bold">•</span>
                                <span className="text-muted/70 text-xs font-semibold truncate">
                                  {m.map}
                                </span>
                              </div>
                              
                              <div className="flex items-center gap-2 mt-1">
                                <span className={`text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded bg-white/[0.02] border border-white/[0.04] ${win ? 'text-emerald-400 border-emerald-500/20' : 'text-red-400 border-red-500/20'}`}>
                                  {win ? 'Victory' : 'Defeat'}
                                </span>
                                <span className="text-[10px] text-muted/50 tabular-nums">
                                  {formatTimeAgo(m.started_at)}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Column 2: Round Score */}
                          <div className="flex flex-col items-center justify-center px-4">
                            <span className="text-[9px] uppercase tracking-widest text-muted font-bold mb-0.5">Score</span>
                            <span className={`text-base font-black tracking-widest tabular-nums ${win ? 'text-emerald-400' : 'text-red-400'}`}>
                              {m.team_score ?? 13}<span className="text-muted/40 font-medium mx-1">:</span>{m.enemy_score ?? 10}
                            </span>
                          </div>

                          {/* Column 3: KD Ratio & Stats (ACS / HS%) */}
                          <div className="flex items-center gap-4">
                            {/* K/D Ratio Big Pill */}
                            <div className="flex flex-col items-center">
                              <span className="text-[9px] uppercase tracking-widest text-muted font-bold mb-1">K/D Ratio</span>
                              <div className={`inline-flex items-center justify-center px-3.5 py-1 rounded-xl border shadow-sm ${kdGlow}`}>
                                <span className={`font-black text-base tabular-nums ${kdColor}`}>{kdRatio}</span>
                              </div>
                            </div>

                            {/* KDA & Detail splits */}
                            <div className="flex flex-col justify-center min-w-[100px] hidden sm:flex">
                              <div className="tabular-nums text-xs">
                                <span className="text-white font-black">{kills}</span>
                                <span className="text-muted/30 mx-1">/</span>
                                <span className="text-white font-black">{deaths}</span>
                                <span className="text-muted/30 mx-1">/</span>
                                <span className="text-muted font-black">{assists}</span>
                              </div>
                              <div className="flex gap-2 mt-1 text-[10px] text-muted/60 font-semibold uppercase tracking-wider">
                                <span>{m.acs ? `${Math.round(m.acs)} ACS` : ''}</span>
                                {m.headshot_pct != null && (
                                  <>
                                    <span>•</span>
                                    <span>{Math.round(m.headshot_pct * 100)}% HS</span>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Column 4: Rank Badge (right corner) */}
                          <div className="flex-shrink-0 pl-4 border-l border-line/10 flex items-center justify-center h-12">
                            <div 
                              className="relative w-12 h-12 flex items-center justify-center cursor-help group/rank"
                              title={m.tier_name || 'Unranked'}
                            >
                              <div className="absolute inset-1 rounded-full bg-white/[0.02] border border-white/[0.04] opacity-0 group-hover/rank:opacity-100 transition-all duration-300 scale-90 group-hover/rank:scale-100" />
                              <img 
                                src={RANK_ICONS[(m.tier_name || 'unranked').toLowerCase()] || RANK_ICONS['unranked']} 
                                alt={m.tier_name || 'Unranked'} 
                                className="w-10 h-10 object-contain transition-all duration-300 group-hover/rank:scale-110 drop-shadow-lg group-hover/rank:drop-shadow-2xl"
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Panel>
            </section>
          )}

          <CoachAnalysis vm={vm} />

          {/* LIVE COACH + EXPORT */}
          <section className="grid gap-4 lg:grid-cols-3">
            <Panel glow="red" className="flex flex-col p-5 lg:col-span-2">
              <SectionTitle>Live Coach · RAG</SectionTitle>
              <div className="h-80">
                {/* key resets the chat (greeting + history) when the player changes */}
                <CoachPanel key={vm.riotId} riotId={vm.riotId} />
              </div>
            </Panel>
            <Panel glow="blue" className="flex flex-col p-5">
              <SectionTitle accent="blue">Share Your Card</SectionTitle>
              <p className="text-xs leading-relaxed text-muted mb-4">
                Export a 1080×1920 story card with your top stats, best &amp; worst maps, and the
                AI summary. Perfect for flexing your grind.
              </p>
              <div className="flex-1 flex flex-col justify-center">
                <ShareCard vm={vm} />
              </div>
            </Panel>
          </section>
        </div>
      )}
    </div>
  );
}

function EmptyState({ loading, recentSearches, onSelectPlayer }: { loading: boolean; recentSearches: string[]; onSelectPlayer: (riotId: string, region: string) => void }) {
  const { user } = useAuth();

  if (loading) {
    return (
      <div className="grid min-h-[55vh] place-items-center text-center select-none animate-pulse">
        <div>
          <div className="mx-auto mb-6 h-28 w-28 rounded-full bg-gradient-to-br from-brand-red/30 to-brand-blue/20 blur-2xl animate-bounce" />
          <h2 className="text-2xl font-black text-white tracking-wider uppercase">Analyzing matches...</h2>
          <p className="mt-2.5 text-xs text-muted max-w-sm mx-auto leading-relaxed">
            Running mechanical profiles, grounding agent playbooks, mapping spatial coordinates, and parsing Qdrant RAG knowledge base.
          </p>
        </div>
      </div>
    );
  }

  // Construct user's profile card if linked
  const userProfile = user?.linked_riot_id && user.linked_riot_id.includes('#') ? (() => {
    const [name, tag] = user.linked_riot_id.split('#');
    return {
      name,
      tag,
      role: 'Owner',
      rank: 'Your Profile',
      badgeColor: 'border-emerald-500/20 text-emerald-400 bg-emerald-500/5',
      region: 'na'
    };
  })() : null;

  // Filter out linked profile from history if it is already displayed on top
  const historyList = recentSearches
    .filter(riotId => riotId && riotId.includes('#') && riotId !== user?.linked_riot_id)
    .map(riotId => {
      const [name, tag] = riotId.split('#');
      return {
        name,
        tag,
        role: 'History',
        rank: 'Recent Analysis',
        badgeColor: 'border-white/10 text-muted bg-white/[0.01]',
        region: 'na'
      };
    });

  const cardsToShow = [];
  if (userProfile) cardsToShow.push(userProfile);
  cardsToShow.push(...historyList);

  return (
    <div className="w-full py-8 space-y-12 select-none">
      
      {/* Top Banner Welcome */}
      <div className="relative overflow-hidden rounded-3xl border border-white/5 bg-ink-900/40 p-8 flex flex-col md:flex-row justify-between items-center gap-6 shadow-xl">
        <div className="absolute top-[-50%] right-[-10%] h-96 w-96 rounded-full bg-brand-red/5 blur-[80px] pointer-events-none" />
        <div className="space-y-2 text-center md:text-left z-10">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md border border-brand-red/20 bg-brand-red/5 text-[9px] font-black text-brand-red uppercase tracking-widest">
            Tactical Node Active
          </div>
          <h2 className="text-xl sm:text-2xl font-black uppercase text-white tracking-wide">
            Analyze Your Gameplay
          </h2>
          <p className="text-xs text-muted max-w-xl leading-relaxed">
            Enter your Riot ID (Name#Tag) above and select your region to trigger a live telemetry harvest and compute aim statistics.
          </p>
        </div>
        <div className="flex-shrink-0 z-10 bg-white/[0.02] border border-white/5 rounded-2xl p-4 text-center min-w-[200px]">
          <span className="text-[9px] font-black text-muted uppercase tracking-widest block mb-1">Riot API Status</span>
          <span className="text-xs font-bold text-emerald-400 flex items-center justify-center gap-1.5 uppercase">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
            Online &amp; Operational
          </span>
        </div>
      </div>

      {/* Featured Profiles Selection */}
      <div className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-white/5">
          <h3 className="text-xs font-black uppercase text-white tracking-widest flex items-center gap-1.5">
            <Gamepad2 size={12} className="text-brand-red" />
            Your Saved Diagnostics
          </h3>
          <span className="text-[10px] text-muted font-medium">Click to instantly reload</span>
        </div>

        {cardsToShow.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/5 bg-ink-900/10 p-8 text-center">
            <p className="text-xs text-muted leading-relaxed">
              No recently analyzed accounts found. Enter a Riot ID in the search bar above to begin.
            </p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-4">
            {cardsToShow.map((player) => (
              <button
                key={`${player.name}#${player.tag}`}
                onClick={() => onSelectPlayer(`${player.name}#${player.tag}`, player.region)}
                className="group text-left p-5 rounded-2xl border border-white/5 bg-ink-900/30 hover:border-brand-red/30 hover:bg-brand-red/[0.02] transition-all duration-300 relative overflow-hidden flex items-center justify-between cursor-pointer"
              >
                <div className="space-y-2 z-10">
                  <span className={`inline-block border px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-widest ${player.badgeColor}`}>
                    {player.role}  ·  {player.rank}
                  </span>
                  <h4 className="text-lg font-black uppercase tracking-wide text-white group-hover:text-brand-red transition-colors">
                    {player.name}<span className="text-muted/60">#{player.tag}</span>
                  </h4>
                  <p className="text-[10px] text-muted uppercase font-semibold tracking-wider">
                    Region: {player.region.toUpperCase()}  ·  Click to run diagnostics
                  </p>
                </div>
                <ChevronRight size={16} className="text-muted group-hover:text-brand-red group-hover:translate-x-1.5 transition-all z-10" />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Toolkit Features Preview Grid */}
      <div className="space-y-4">
        <div className="flex items-center gap-1.5 pb-2 border-b border-white/5">
          <Sparkles size={12} className="text-brand-blue" />
          <h3 className="text-xs font-black uppercase text-white tracking-widest">Diagnostics Modules</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Box 1 */}
          <div className="p-5 rounded-2xl border border-white/5 bg-ink-900/10 space-y-3">
            <div className="h-8 w-8 rounded-lg bg-brand-red/10 border border-brand-red/20 flex items-center justify-center text-brand-red">
              <Target size={14} />
            </div>
            <h4 className="text-xs font-black uppercase tracking-wider text-white">Mechanical Aim Profiler</h4>
            <p className="text-[10px] leading-relaxed text-muted">
              Evaluates hit distributions, distance-based headshot ratios, and calculates sensitivity adjustments.
            </p>
          </div>
          
          {/* Box 2 */}
          <div className="p-5 rounded-2xl border border-white/5 bg-ink-900/10 space-y-3">
            <div className="h-8 w-8 rounded-lg bg-brand-blue/10 border border-brand-blue/20 flex items-center justify-center text-brand-blue">
              <BrainCircuit size={14} />
            </div>
            <h4 className="text-xs font-black uppercase tracking-wider text-white">Tactical RAG Live Coach</h4>
            <p className="text-[10px] leading-relaxed text-muted">
              A vector-grounded chat AI targeting map positioning errors, site default rules, and utility guidance.
            </p>
          </div>

          {/* Box 3 */}
          <div className="p-5 rounded-2xl border border-white/5 bg-ink-900/10 space-y-3">
            <div className="h-8 w-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-white">
              <Activity size={14} />
            </div>
            <h4 className="text-xs font-black uppercase tracking-wider text-white">ACS Stability Monitor</h4>
            <p className="text-[10px] leading-relaxed text-muted">
              Computes combat score standard deviation to identify feast-or-famine playing form.
            </p>
          </div>
        </div>
      </div>

    </div>
  );
}
