"use client";

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import ErrorBoundary from '../ErrorBoundary';

// r3f Canvas is client + WebGL only — never SSR it.
const AgentHero = dynamic(() => import('../three/AgentHero'), { ssr: false });

function Placeholder({ agent }: { agent: string }) {
  return (
    <div className="relative grid h-full min-h-[240px] w-full place-items-center overflow-hidden rounded-2xl">
      <div className="absolute h-40 w-40 animate-pulse rounded-full bg-gradient-to-br from-brand-red/50 to-brand-blue/30 blur-2xl" />
      <div className="relative text-center">
        <div className="text-[10px] font-semibold tracking-[0.2em] text-brand-blue/80">TOP AGENT</div>
        <div className="text-2xl font-bold text-white drop-shadow-[0_0_10px_rgba(255,70,85,0.6)]">{agent}</div>
      </div>
    </div>
  );
}

function webglSupported(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(
      window.WebGLRenderingContext &&
      (c.getContext('webgl') || c.getContext('experimental-webgl'))
    );
  } catch {
    return false;
  }
}

/**
 * Renders the 3D agent hero only when the browser actually supports WebGL,
 * and wraps it in an error boundary so any GL/runtime failure falls back to a
 * styled placeholder instead of tearing down the whole dashboard.
 */
export default function HeroVisual({ agent }: { agent: string }) {
  const [canRender3D, setCanRender3D] = useState(false);

  useEffect(() => {
    setCanRender3D(webglSupported());
  }, []);

  if (!canRender3D) return <Placeholder agent={agent} />;

  return (
    <ErrorBoundary label="AgentHero" fallback={<Placeholder agent={agent} />}>
      <AgentHero agent={agent} />
    </ErrorBoundary>
  );
}
