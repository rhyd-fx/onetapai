"use client";

import { useRef, useState, useEffect } from 'react';
import { Download, Sparkles, Image as ImageIcon } from 'lucide-react';
import { DashboardVM } from '@/lib/viewModel';

// NOTE: The hidden export card is styled with INLINE HEX colors (not Tailwind utilities),
// because Tailwind v4 emits oklch() colors that html2canvas cannot parse.
// It renders off-screen at true 1080x1920 and is captured on demand.

const RED = '#ff4655';
const BLUE = '#22d3ee';
const INK = '#05070b';
const PANEL = '#0b0f15';
const BORDER = '#1e293b';
const MUTED = '#94a3b8';

function Stat({ label, value, color = '#ffffff' }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ 
      flex: 1, 
      background: PANEL, 
      border: `1px solid ${BORDER}`, 
      borderRadius: 20, 
      padding: '24px 20px', 
      textAlign: 'center',
      boxShadow: '0 8px 32px rgba(0,0,0,0.2)'
    }}>
      <div style={{ color: MUTED, fontSize: 18, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase' }}>{label}</div>
      <div style={{ color, fontSize: 46, fontWeight: 900, marginTop: 8, fontFamily: 'monospace' }}>{value}</div>
    </div>
  );
}

export default function ShareCard({ vm }: { vm: DashboardVM }) {
  const ref = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);
  const [mapSplashes, setMapSplashes] = useState<Record<string, string>>({});
  const [name, tag] = vm.riotId.split('#');

  useEffect(() => {
    // Fetch map splashes from Valorant API to display map images in the export
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
          setMapSplashes(mapping);
        }
      })
      .catch((err) => console.error('Failed to fetch map splashes for share card:', err));
  }, []);

  const download = async () => {
    if (!ref.current || busy) return;
    setBusy(true);
    try {
      const html2canvas = (await import('html2canvas')).default;
      const canvas = await html2canvas(ref.current, { 
        backgroundColor: INK, 
        scale: 2, // 2x scale for ultra HD resolution
        logging: false, 
        useCORS: true,
        allowTaint: false
      });
      const a = document.createElement('a');
      a.download = `onetap-${name}-${tag}.png`;
      a.href = canvas.toDataURL('image/png');
      a.click();
    } catch (error) {
      console.error('Error generating card image:', error);
    } finally {
      setBusy(false);
    }
  };

  const bestMapSplash = mapSplashes[vm.bestMap?.map.toLowerCase() || ''];
  const worstMapSplash = mapSplashes[vm.worstMap?.map.toLowerCase() || ''];

  return (
    <div className="flex flex-col items-center gap-6 w-full">
      {/* Interactive Mockup/Preview of the Share Card */}
      <div className="relative w-full max-w-[260px] aspect-[9/16] bg-ink-950/40 rounded-2xl border border-white/5 overflow-hidden flex flex-col group transition-all duration-500 hover:border-brand-red/30 hover:shadow-[0_0_30px_rgba(255,70,85,0.15)] shadow-2xl select-none">
        
        {/* Banner with Player Card Wideart */}
        <div 
          className="relative h-[110px] bg-cover bg-center flex flex-col justify-end p-3 flex-shrink-0"
          style={{ backgroundImage: `url(${vm.cardUrl || 'https://media.valorant-api.com/playercards/9e73b22e-4b46-e41a-a9a3-5f8f84d6333f/wideart.png'})` }}
        >
          <div className="absolute inset-0 bg-gradient-to-t from-ink-950 via-ink-950/40 to-transparent pointer-events-none" />
          <div className="relative z-1">
            <div className="flex items-baseline gap-1 min-w-0">
              <span className="text-sm font-black text-white truncate max-w-[70%]">{name}</span>
              <span className="text-[10px] font-bold text-muted truncate">#{tag}</span>
            </div>
            <div className="text-[8px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded border border-brand-red/30 bg-brand-red/15 text-brand-red mt-1 inline-block">
              {vm.tier.label}
            </div>
          </div>
        </div>

        {/* Mini Stats Grid */}
        <div className="p-3 grid grid-cols-2 gap-2 flex-shrink-0 bg-ink-950/20">
          <div className="bg-ink-900/60 border border-white/5 rounded-lg p-2 text-center">
            <div className="text-[8px] font-bold text-muted uppercase tracking-wider">ACS</div>
            <div className="text-sm font-black text-brand-red mt-0.5">{vm.stats.acs.toFixed(0)}</div>
          </div>
          <div className="bg-ink-900/60 border border-white/5 rounded-lg p-2 text-center">
            <div className="text-[8px] font-bold text-muted uppercase tracking-wider">HS%</div>
            <div className="text-sm font-black text-brand-red mt-0.5">{vm.stats.hsPct.toFixed(0)}%</div>
          </div>
          <div className="bg-ink-900/60 border border-white/5 rounded-lg p-2 text-center">
            <div className="text-[8px] font-bold text-muted uppercase tracking-wider">K/D</div>
            <div className="text-sm font-black text-brand-blue mt-0.5">{vm.stats.kd}</div>
          </div>
          <div className="bg-ink-900/60 border border-white/5 rounded-lg p-2 text-center">
            <div className="text-[8px] font-bold text-muted uppercase tracking-wider">WIN RATE</div>
            <div className="text-sm font-black text-brand-blue mt-0.5">{vm.stats.winRate != null ? `${vm.stats.winRate.toFixed(0)}%` : '—'}</div>
          </div>
        </div>

        {/* Mini Maps Grid */}
        <div className="px-3 pb-3 grid grid-cols-2 gap-2 flex-shrink-0">
          <div 
            className="relative h-12 rounded-lg border border-brand-blue/10 overflow-hidden bg-cover bg-center flex flex-col justify-center p-1.5"
            style={{ backgroundImage: `url(${bestMapSplash || ''})` }}
          >
            <div className="absolute inset-0 bg-ink-950/80" />
            <div className="relative z-1 text-center">
              <div className="text-[6px] font-black text-brand-blue uppercase tracking-wider">Best Map</div>
              <div className="text-[9px] font-bold text-white truncate mt-0.5">{vm.bestMap?.map ?? '—'}</div>
            </div>
          </div>
          <div 
            className="relative h-12 rounded-lg border border-brand-red/10 overflow-hidden bg-cover bg-center flex flex-col justify-center p-1.5"
            style={{ backgroundImage: `url(${worstMapSplash || ''})` }}
          >
            <div className="absolute inset-0 bg-ink-950/80" />
            <div className="relative z-1 text-center">
              <div className="text-[6px] font-black text-brand-red uppercase tracking-wider">Worst Map</div>
              <div className="text-[9px] font-bold text-white truncate mt-0.5">{vm.worstMap?.map ?? '—'}</div>
            </div>
          </div>
        </div>

        {/* AI Insight Snippet */}
        <div className="px-3 flex-1 min-h-0 flex flex-col justify-center bg-ink-950/30 border-t border-white/5">
          <div className="flex items-center gap-1 mb-1">
            <Sparkles size={8} className="text-brand-red animate-pulse" />
            <span className="text-[7px] font-black text-brand-red uppercase tracking-wider">AI Insight Excerpt</span>
          </div>
          <p className="text-[9px] leading-tight text-white/80 line-clamp-2 italic">
            "{vm.summary[0] || 'Analyze matches to generate custom strategic playbooks.'}"
          </p>
        </div>

        {/* Decorative elements */}
        <div className="absolute right-2 top-2 p-1 rounded bg-black/60 border border-white/10 text-[6px] uppercase tracking-widest text-muted/80 font-bold pointer-events-none">
          STORY 1080×1920
        </div>
      </div>

      {/* Action Download Button */}
      <button
        onClick={download}
        disabled={busy}
        className="w-full max-w-[260px] glow-red flex items-center justify-center gap-2.5 rounded-xl bg-brand-red py-3.5 text-xs font-black uppercase tracking-widest text-white transition hover:bg-brand-red-soft active:scale-98 disabled:opacity-50 cursor-pointer shadow-lg"
      >
        <Download size={14} className={busy ? 'animate-bounce' : ''} />
        {busy ? 'Rendering HD Image…' : 'Generate HD Card'}
      </button>

      {/* Hidden 1080x1920 capture target */}
      <div style={{ position: 'fixed', left: -20000, top: 0, pointerEvents: 'none' }} aria-hidden>
        <div
          ref={ref}
          style={{
            width: 1080,
            height: 1920,
            background: `radial-gradient(1200px 900px at 20% 0%, rgba(255,70,85,0.15), transparent 70%), ${INK}`,
            color: '#ffffff',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            display: 'flex',
            flexDirection: 'column',
            boxSizing: 'border-box',
          }}
        >
          {/* Full-Bleed Top Header Banner using Wideart Player Card */}
          <div style={{
            width: 1080,
            height: 480,
            backgroundImage: `url(${vm.cardUrl || 'https://media.valorant-api.com/playercards/9e73b22e-4b46-e41a-a9a3-5f8f84d6333f/wideart.png'})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            position: 'relative',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-end',
            padding: '0 64px 44px 64px',
            boxSizing: 'border-box'
          }}>
            {/* Smooth transition from wideart to deep black background */}
            <div style={{
              position: 'absolute',
              inset: 0,
              background: 'linear-gradient(to bottom, rgba(5,7,11,0) 0%, rgba(5,7,11,0.5) 50%, rgba(5,7,11,1) 100%)',
              pointerEvents: 'none'
            }} />
            
            {/* Branding & Profile Overlay */}
            <div style={{ position: 'relative', zIndex: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'baseline' }}>
                  <span style={{ fontSize: 72, fontWeight: 900, color: '#ffffff', letterSpacing: -1 }}>{name}</span>
                  <span style={{ fontSize: 36, fontWeight: 700, color: MUTED, marginLeft: 16 }}>#{tag}</span>
                </div>
                <div style={{ display: 'inline-block', marginTop: 20, padding: '8px 20px', background: 'rgba(255, 70, 85, 0.12)', border: `2px solid ${RED}`, borderRadius: 14, color: RED, fontWeight: 900, fontSize: 22, letterSpacing: 4, textTransform: 'uppercase' }}>
                  {vm.tier.label}
                </div>
              </div>
              <div style={{ color: MUTED, fontSize: 24, letterSpacing: 4, fontWeight: 900, paddingBottom: 10 }}>{vm.region.toUpperCase()}</div>
            </div>
          </div>

          {/* Card Content Grid Area */}
          <div style={{ 
            padding: '0 64px 64px 64px', 
            display: 'flex', 
            flexDirection: 'column', 
            flex: 1, 
            gap: 48, 
            marginTop: 36, 
            boxSizing: 'border-box' 
          }}>
            
            {/* Stats Grid row */}
            <div style={{ display: 'flex', gap: 24 }}>
              <Stat label="ACS" value={vm.stats.acs.toFixed(0)} color={RED} />
              <Stat label="HS%" value={`${vm.stats.hsPct.toFixed(0)}%`} color={RED} />
              <Stat label="K/D" value={vm.stats.kd} color={BLUE} />
              <Stat label="Win Rate" value={vm.stats.winRate != null ? `${vm.stats.winRate.toFixed(0)}%` : '—'} color={BLUE} />
            </div>

            {/* Maps Showcase (Split grid with real widescreen map background graphics) */}
            <div style={{ display: 'flex', gap: 24 }}>
              {/* Best Map */}
              <div style={{
                flex: 1,
                height: 240,
                borderRadius: 24,
                position: 'relative',
                overflow: 'hidden',
                border: `1px solid ${BLUE}44`,
                boxShadow: '0 12px 32px rgba(0,0,0,0.3)'
              }}>
                <div style={{
                  position: 'absolute',
                  inset: 0,
                  backgroundImage: `url(${bestMapSplash || ''})`,
                  backgroundSize: 'cover',
                  backgroundPosition: 'center'
                }} />
                <div style={{
                  position: 'absolute',
                  inset: 0,
                  background: 'linear-gradient(to right, rgba(11,15,21,0.95) 45%, rgba(11,15,21,0.65) 100%)'
                }} />
                <div style={{ position: 'relative', zIndex: 1, padding: 28, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', boxSizing: 'border-box' }}>
                  <div>
                    <div style={{ color: BLUE, fontSize: 18, fontWeight: 900, letterSpacing: 2, textTransform: 'uppercase' }}>Best Map</div>
                    <div style={{ fontSize: 38, fontWeight: 900, marginTop: 4, color: '#ffffff' }}>{vm.bestMap?.map ?? '—'}</div>
                  </div>
                  <div style={{ color: MUTED, fontSize: 20, fontWeight: 700 }}>
                    Avg ACS: <span style={{ color: '#ffffff', fontFamily: 'monospace' }}>{vm.bestMap ? vm.bestMap.avgAcs.toFixed(0) : '—'}</span>
                  </div>
                </div>
              </div>

              {/* Worst Map */}
              <div style={{
                flex: 1,
                height: 240,
                borderRadius: 24,
                position: 'relative',
                overflow: 'hidden',
                border: `1px solid ${RED}44`,
                boxShadow: '0 12px 32px rgba(0,0,0,0.3)'
              }}>
                <div style={{
                  position: 'absolute',
                  inset: 0,
                  backgroundImage: `url(${worstMapSplash || ''})`,
                  backgroundSize: 'cover',
                  backgroundPosition: 'center'
                }} />
                <div style={{
                  position: 'absolute',
                  inset: 0,
                  background: 'linear-gradient(to right, rgba(11,15,21,0.95) 45%, rgba(11,15,21,0.65) 100%)'
                }} />
                <div style={{ position: 'relative', zIndex: 1, padding: 28, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', boxSizing: 'border-box' }}>
                  <div>
                    <div style={{ color: RED, fontSize: 18, fontWeight: 900, letterSpacing: 2, textTransform: 'uppercase' }}>Worst Map</div>
                    <div style={{ fontSize: 38, fontWeight: 900, marginTop: 4, color: '#ffffff' }}>{vm.worstMap?.map ?? '—'}</div>
                  </div>
                  <div style={{ color: MUTED, fontSize: 20, fontWeight: 700 }}>
                    Avg ACS: <span style={{ color: '#ffffff', fontFamily: 'monospace' }}>{vm.worstMap ? vm.worstMap.avgAcs.toFixed(0) : '—'}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* AI Summary Block */}
            <div style={{ 
              background: PANEL, 
              border: `1px solid ${BORDER}`, 
              borderRadius: 24, 
              padding: 40, 
              display: 'flex', 
              flexDirection: 'column', 
              gap: 24, 
              boxShadow: '0 12px 32px rgba(0,0,0,0.3)' 
            }}>
              <div style={{ color: RED, fontSize: 24, fontWeight: 900, letterSpacing: 2.5, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 10 }}>
                <span>AI Tactical Insights</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                {vm.summary.slice(0, 3).map((s, i) => (
                  <div key={i} style={{ display: 'flex', gap: 18, alignItems: 'flex-start' }}>
                    <div style={{ width: 12, height: 12, borderRadius: 6, background: RED, marginTop: 12, flex: '0 0 auto' }} />
                    <div style={{ fontSize: 28, lineHeight: 1.45, color: '#ffffff', opacity: 0.9 }}>{s}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Footer with branding */}
            <div style={{ 
              marginTop: 'auto', 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              borderTop: `1px solid ${BORDER}`, 
              paddingTop: 36, 
              color: MUTED, 
              fontSize: 22, 
              fontWeight: 800 
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span>ONETAP</span>
                <span style={{ color: RED }}>AI</span>
              </div>
              <span>{vm.mainAgent} · {vm.stats.games} games analyzed</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
