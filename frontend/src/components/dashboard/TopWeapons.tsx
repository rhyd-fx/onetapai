"use client";

import { useState, useEffect } from 'react';
import { X, ShieldAlert } from 'lucide-react';
import { WeaponStats } from '@/lib/api';
import { Panel, SectionTitle } from './primitives';

// Shared global cache of fetched weapon icons from valorant-api.com
const weaponIconCache: Record<string, string> = {};

export default function TopWeapons({ weapons }: { weapons: WeaponStats[] }) {
  const [icons, setIcons] = useState<Record<string, string>>(weaponIconCache);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (Object.keys(icons).length > 0) return;
    
    fetch('https://valorant-api.com/v1/weapons')
      .then((res) => res.json())
      .then((res) => {
        if (res?.data) {
          const map: Record<string, string> = {};
          res.data.forEach((w: any) => {
            map[w.displayName.toLowerCase()] = w.displayIcon;
          });
          // Cache the icons
          Object.assign(weaponIconCache, map);
          setIcons({ ...map });
        }
      })
      .catch((err) => console.error('Failed to fetch weapon icons:', err));
  }, []);

  const getIcon = (name: string) => {
    return icons[name.toLowerCase()] || '';
  };

  // Filter out empty weapon names if any exist (e.g. ability kills that mapped to empty strings)
  const filteredWeapons = weapons.filter(w => w.weapon.trim() !== "");
  const top5 = filteredWeapons.slice(0, 5);

  if (filteredWeapons.length === 0) {
    return (
      <Panel className="p-5 flex flex-col justify-center items-center text-center h-full">
        <ShieldAlert size={32} className="text-muted mb-2" />
        <SectionTitle>Top Weapons</SectionTitle>
        <p className="text-sm text-muted">No weapon analytics available for this player.</p>
      </Panel>
    );
  }

  return (
    <>
      {/* Header outside the panel container */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <SectionTitle>Top Weapons</SectionTitle>
        {filteredWeapons.length > 5 && (
          <button
            onClick={() => setIsOpen(true)}
            className="text-[10px] font-bold text-brand-blue hover:text-brand-blue-soft transition uppercase tracking-widest cursor-pointer border border-brand-blue/20 bg-brand-blue/5 rounded px-2 py-0.5"
          >
            View all ({filteredWeapons.length})
          </button>
        )}
      </div>

      {/* Panel container taking full remaining height */}
      <Panel className="p-5 flex-1 flex flex-col min-h-0">
        <div className="flex-1 flex flex-col min-h-0">
          {/* Static list container showing top 5 weapons with no scrollbar */}
          <div className="space-y-[15px]">
            {top5.map((w, index) => {
              const icon = getIcon(w.weapon);
              return (
                <div
                  key={w.weapon}
                  className="group relative flex flex-col gap-2 py-[15px] px-3.5 rounded-xl border border-white/5 bg-ink-950/20 transition-all duration-300 hover:bg-ink-950/40 hover:border-white/10"
                >
                  {/* Top Row: Rank, Icon, Name, Kills & HS% */}
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="text-[10px] font-black text-muted/50 w-3 flex-shrink-0">#{index + 1}</span>
                      {icon ? (
                        <div className="w-20 h-10 flex items-center justify-center bg-ink-950/80 rounded-lg border border-white/5 p-1 flex-shrink-0 group-hover:scale-105 transition-transform duration-300">
                          <img
                            src={icon}
                            alt={w.weapon}
                            className="max-w-full max-h-full object-contain filter drop-shadow-[0_2px_4px_rgba(0,0,0,0.6)]"
                          />
                        </div>
                      ) : (
                        <div className="w-20 h-10 bg-ink-950/80 rounded-lg border border-white/5 flex items-center justify-center text-[10px] font-bold text-muted uppercase flex-shrink-0">
                          {w.weapon}
                        </div>
                      )}
                      <div className="min-w-0 pl-0.5">
                        <div className="text-xs font-black text-white uppercase tracking-wider truncate" title={w.weapon}>
                          {w.weapon}
                        </div>
                        <div className="text-[10px] text-muted/70 font-semibold mt-0.5">
                          {w.kills} <span className="text-[8px] uppercase tracking-wider text-muted/50 font-bold">kills</span>
                        </div>
                      </div>
                    </div>

                    {/* Right-aligned HS% block */}
                    <div className="text-right flex-shrink-0">
                      <div className="text-[10px] font-black text-brand-red uppercase tracking-wider">
                        {w.headshot_pct}% HS
                      </div>
                      <div className="text-[8px] text-muted/60 uppercase tracking-widest font-bold mt-0.5">
                        BS: {w.bodyshot_pct}%
                      </div>
                    </div>
                  </div>

                  {/* Bottom Row: Sleek Segmented Accuracy Bar */}
                  <div className="w-full h-1 bg-ink-950 rounded-full flex overflow-hidden border border-white/[0.03]">
                    <div
                      className="h-full bg-brand-red transition-all"
                      style={{ width: `${w.headshot_pct}%` }}
                    />
                    <div
                      className="h-full bg-white/70 transition-all"
                      style={{ width: `${w.bodyshot_pct}%` }}
                    />
                    <div
                      className="h-full bg-brand-blue transition-all"
                      style={{ width: `${w.legshot_pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </Panel>

      {/* Modern Dialog/Overlay for View All Weapons */}
      {isOpen && (
        <div className="fixed inset-0 bg-ink-950/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="glass w-full max-w-4xl max-h-[85vh] rounded-2xl border border-white/10 bg-ink-950 p-6 overflow-y-auto shadow-2xl flex flex-col gap-6 animate-fade-in">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/5 pb-4">
              <div>
                <h3 className="text-xl font-extrabold text-white uppercase tracking-wider">
                  Complete Weapon Analytics
                </h3>
                <p className="text-xs text-muted mt-1 font-medium">
                  Full list of weapons sorted by kills with finishing shot distributions
                </p>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-lg border border-white/5 hover:bg-ink-900/50 text-muted hover:text-white transition cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Grid layout for list in modal */}
            <div className="grid gap-4 sm:grid-cols-2">
              {filteredWeapons.map((w, index) => {
                const icon = getIcon(w.weapon);
                return (
                  <div
                    key={w.weapon}
                    className="group relative flex flex-col gap-2 p-3.5 rounded-xl border border-white/5 bg-ink-900/30 transition-all duration-300 hover:bg-ink-900/50 hover:border-white/10"
                  >
                    {/* Top Row: Rank, Icon, Name, Kills & HS% */}
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="text-xs font-black text-muted/50 w-4 flex-shrink-0">#{index + 1}</span>
                        {icon ? (
                          <div className="w-20 h-10 flex items-center justify-center bg-ink-950/80 rounded-lg border border-white/5 p-1 flex-shrink-0 group-hover:scale-105 transition-transform duration-300">
                            <img
                              src={icon}
                              alt={w.weapon}
                              className="max-w-full max-h-full object-contain filter drop-shadow-[0_2px_4px_rgba(0,0,0,0.6)]"
                            />
                          </div>
                        ) : (
                          <div className="w-20 h-10 bg-ink-950/80 rounded-lg border border-white/5 flex items-center justify-center text-[10px] font-bold text-muted uppercase flex-shrink-0">
                            {w.weapon}
                          </div>
                        )}
                        <div className="min-w-0 pl-0.5">
                          <div className="text-sm font-black text-white uppercase tracking-wider truncate" title={w.weapon}>
                            {w.weapon}
                          </div>
                          <div className="text-xs text-muted/70 font-semibold mt-0.5">
                            {w.kills} <span className="text-[10px] uppercase tracking-wider text-muted/50 font-bold">kills</span>
                          </div>
                        </div>
                      </div>

                      {/* Right-aligned HS% block */}
                      <div className="text-right flex-shrink-0">
                        <div className="text-sm font-black text-brand-red uppercase tracking-wider">
                          {w.headshot_pct}% HS
                        </div>
                        <div className="text-[10px] text-muted/60 uppercase tracking-widest font-bold mt-0.5">
                          BS: {w.bodyshot_pct}% | LS: {w.legshot_pct}%
                        </div>
                      </div>
                    </div>

                    {/* Bottom Row: Sleek Segmented Accuracy Bar */}
                    <div className="w-full h-1.5 bg-ink-950 rounded-full flex overflow-hidden border border-white/[0.03]">
                      <div
                        className="h-full bg-brand-red transition-all"
                        style={{ width: `${w.headshot_pct}%` }}
                      />
                      <div
                        className="h-full bg-white/70 transition-all"
                        style={{ width: `${w.bodyshot_pct}%` }}
                      />
                      <div
                        className="h-full bg-brand-blue transition-all"
                        style={{ width: `${w.legshot_pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
