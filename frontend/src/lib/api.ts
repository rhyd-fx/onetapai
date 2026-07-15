// Thin client for the OneTap AI backend.
// Resolution order for the base URL:
//   1. NEXT_PUBLIC_API_URL if explicitly set (see .env.local.example)
//   2. In the browser: same host the app was loaded from, on port 8000
//      (so accessing the app via a LAN IP still reaches the backend)
//   3. SSR fallback: localhost:8000
function apiBase(): string {
  const env = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (env) return env;
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

const API_BASE = apiBase();

export function getHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("onetap_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
}


export interface PlayerProfile {
  game_name: string;
  tag_line: string;
  region: string;
  games: number;
  wins: number;
  win_rate: number | null;
  avg_acs: number;
  headshot_pct: number | null;
  bodyshot_pct: number | null;
  legshot_pct: number | null;
  kills: number;
  deaths: number;
  assists: number;
  main_agent: string | null;
  card_uuid?: string | null;
}

export interface AimProfile {
  available: boolean;
  reason?: string;
  headshot_pct?: number;
  bodyshot_pct?: number;
  legshot_pct?: number;
  deficiencies?: string[];
}

export interface AcsPoint {
  match_id: string;
  map: string;
  started_at: string;
  acs: number;
  won: boolean;
  headshot_pct: number | null;
  bodyshot_pct: number | null;
  agent?: string;
  kills?: number;
  deaths?: number;
  assists?: number;
  team_score?: number;
  enemy_score?: number;
  tier_id?: number;
  tier_name?: string;
}

export interface Telemetry {
  rounds: number;
  adr: number | null;                   // average damage per round
  movement_error_pct: number | null;    // % of death-rounds dealing 0 damage
  opening_duel_win_pct: number | null;
  first_kills: number | null;           // opening kills won
  first_deaths: number | null;          // opening deaths taken
  fk_fd_diff: number | null;            // first_kills - first_deaths
  avg_time_to_damage_s: number | null;
  multikill_pct: number | null;
}

export interface MapStats {
  map: string;
  games: number;
  wins: number;
  losses: number;
  win_rate: number;
}

export interface WeaponStats {
  weapon: string;
  kills: number;
  headshot_pct: number;
  bodyshot_pct: number;
  legshot_pct: number;
}

export interface DistanceAimStats {
  range: 'close' | 'medium' | 'long';
  kills: number;
  headshot_pct: number;
  bodyshot_pct: number;
  legshot_pct: number;
}

export interface EconomyStatsClass {
  rounds: number;
  wins: number;
  win_rate: number;
}

export interface EconomyEfficiency {
  by_class: Record<'eco' | 'half_buy' | 'force_buy' | 'full_buy', EconomyStatsClass>;
  eco_throws: number;
}

export interface SideBias {
  attack_win_pct: number;
  attack_rounds: number;
  defense_win_pct: number;
  defense_rounds: number;
  early_defense_death_pct: number;
  early_defense_deaths: number;
}

export interface HardwareCheck {
  mouse_dpi: number;
  in_game_sens: number;
  edpi: number;
  mouse_model: string;
  monitor_refresh_rate: number;
}

export interface AnalyzeResponse {
  player_profile: PlayerProfile;
  aim_profile: AimProfile;
  acs_trajectory: AcsPoint[];
  telemetry?: Telemetry;
  top_maps?: MapStats[];
  top_weapons?: WeaponStats[];
  aim_by_distance?: DistanceAimStats[];
  economy_efficiency?: EconomyEfficiency;
  side_bias?: SideBias;
  hardware_check?: HardwareCheck;
  seasons?: string[];
  matchup_diagnostics?: {
    killer_agents: { agent: string; deaths: number }[];
    killer_roles: Record<'Duelist' | 'Initiator' | 'Controller' | 'Sentinel' | 'Unknown', number>;
    utility_deaths: { ability: string; deaths: number }[];
    gun_deaths_count: number;
    utility_deaths_count: number;
  };
  economy_split?: Record<'eco' | 'half_buy' | 'force_buy' | 'full_buy', { rounds: number; avg_acs: number }>;
}

export interface AnalyzeRequestOptions {
  seasonId?: string | null;
  // Modes to include. undefined -> Ranked (Comp + Premier); [] -> all modes;
  // ["Unrated", ...] -> those modes only.
  gameModes?: string[];
  skipSync?: boolean;
}

export async function analyzePlayer(
  riotId: string,
  region = "na",
  options?: AnalyzeRequestOptions
): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/api/v1/analyze`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({
      riot_id: riotId,
      region,
      season_id: options?.seasonId,
      game_modes: options?.gameModes ?? ["Competitive", "Premier"],
      skip_sync: options?.skipSync ?? false,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

// Death/kill points normalized to 0–100% of the minimap (see backend
// analysis/spatial/coordinates.py).
export interface HeatPoint {
  x: number; // 0–100, % from left
  y: number; // 0–100, % from top
}

export interface HeatmapResponse {
  map_id: string;
  calibrated: boolean; // false → placeholder bounds, positions approximate
  minimap_url: string | null; // real Riot minimap image when officially calibrated
  deaths: HeatPoint[];
  kills: HeatPoint[];
}

export async function getHeatmap(
  riotId: string,
  mapId: string,
  lastN = 100
): Promise<HeatmapResponse> {
  const url =
    `${API_BASE}/api/v1/player/${encodeURIComponent(riotId)}/heatmap` +
    `?map_id=${encodeURIComponent(mapId)}&last_n=${lastN}`;
  const res = await fetch(url, { headers: getHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export interface CoachSource {
  source: string;
  score: number;
  concept_type?: string;
  [k: string]: unknown;
}

export interface CoachResponse {
  answer: string;
  sources_used: CoachSource[];
  player_stats_referenced: Record<string, unknown>;
  follow_up_suggestions: string[];
}

export async function askCoach(riotId: string, question: string): Promise<CoachResponse> {
  const res = await fetch(`${API_BASE}/api/v1/coach`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ riot_id: riotId, question }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export async function submitFeedback(params: {
  question: string;
  rating: 1 | -1;
  riotId?: string;
  answerExcerpt?: string;
  sources?: CoachSource[];
}): Promise<void> {
  await fetch(`${API_BASE}/api/v1/feedback`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({
      question: params.question,
      rating: params.rating,
      riot_id: params.riotId,
      answer_excerpt: params.answerExcerpt,
      sources: params.sources,
    }),
  });
}

export interface AuthResponse {
  token: string;
  username: string;
}

export async function loginUser(usernameOrEmail: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username_or_email: usernameOrEmail, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Login failed (${res.status})`);
  }
  return res.json();
}

export interface RegisterResponse {
  status: string;
  email: string;
  message: string;
}

export async function registerUser(username: string, email: string, password: string): Promise<RegisterResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Registration failed (${res.status})`);
  }
  return res.json();
}

export async function verifyRegisterUser(email: string, code: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/v1/auth/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Verification failed (${res.status})`);
  }
  return res.json();
}

export async function verifyUserSession(): Promise<{ user_id: number; username: string; email: string; linked_riot_id: string | null }> {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    method: "GET",
    headers: getHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Session invalid (${res.status})`);
  }
  return res.json();
}

export async function fetchRecentSearches(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/v1/auth/recent-searches`, {
    method: "GET",
    headers: getHeaders(),
  });
  if (!res.ok) {
    return [];
  }
  return res.json();
}

