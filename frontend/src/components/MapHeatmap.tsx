"use client";

import { useEffect, useState } from 'react';
import { getHeatmap, HeatmapResponse } from '@/lib/api';

interface Props {
  // When both are set, the heatmap fetches and plots real coordinates.
  riotId?: string;
  mapId?: string;
}

const DEATH = '#ff4655';
const KILL = '#22c55e';

export default function MapHeatmap({ riotId, mapId }: Props) {
  const [data, setData] = useState<HeatmapResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!riotId || !mapId) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getHeatmap(riotId, mapId)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : 'Failed to load heatmap'))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [riotId, mapId]);

  if (!riotId || !mapId) {
    return (
      <div className="grid min-h-[280px] place-items-center text-sm text-muted">
        Search a player to load their death/kill map.
      </div>
    );
  }

  const deaths = data?.deaths ?? [];
  const kills = data?.kills ?? [];
  const total = deaths.length + kills.length;
  const minimap = data?.minimap_url ?? null;

  return (
    <div>
      {/* Square plot — Valorant minimaps are square, so 0–100% x/y aligns to it. */}
      <div className="relative mx-auto aspect-square w-full max-w-md overflow-hidden rounded-xl border border-line/60 bg-ink-900/70">
        {minimap ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={minimap} alt={`${mapId} minimap`} className="absolute inset-0 h-full w-full object-contain opacity-70" />
        ) : (
          <div
            className="absolute inset-0 opacity-40"
            style={{
              backgroundImage:
                'linear-gradient(#ffffff12 1px, transparent 1px), linear-gradient(90deg, #ffffff12 1px, transparent 1px)',
              backgroundSize: '10% 10%',
            }}
          />
        )}

        {kills.map((p, i) => (
          <span
            key={`k${i}`}
            title="Kill"
            className="absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
            style={{ top: `${p.y}%`, left: `${p.x}%`, background: KILL, boxShadow: `0 0 6px ${KILL}` }}
          />
        ))}
        {deaths.map((p, i) => (
          <span
            key={`d${i}`}
            title="Death"
            className="absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-1 ring-white/30"
            style={{ top: `${p.y}%`, left: `${p.x}%`, background: DEATH, boxShadow: `0 0 6px ${DEATH}` }}
          />
        ))}

        {loading && (
          <div className="absolute inset-0 grid place-items-center text-sm text-muted">Loading…</div>
        )}
        {!loading && total === 0 && !error && (
          <div className="absolute inset-0 grid place-items-center px-4 text-center text-sm text-muted">
            No {mapId} engagements in this player&apos;s recent matches.
          </div>
        )}
      </div>

      {error && <div className="mt-2 text-sm text-brand-red">{error}</div>}

      <div className="mt-3 flex items-center gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: DEATH }} /> Deaths ({deaths.length})
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: KILL }} /> Kills ({kills.length})
        </span>
        <span className="ml-auto font-semibold text-white/70">{mapId}</span>
      </div>

      <p className="mt-1 text-[11px] text-muted">
        Where you fall (red) and frag (green), plotted on the real {mapId} minimap.
      </p>

      {data && !data.calibrated && (
        <div className="mt-1 text-[11px] text-[#e0a458]">
          ⚠️ Positions approximate — {mapId} has no official minimap mapping.
        </div>
      )}
    </div>
  );
}
