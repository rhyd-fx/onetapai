"use client";

import Link from 'next/link';
import { 
  Sparkles, 
  Target, 
  Map, 
  LineChart, 
  FileImage, 
  ChevronRight, 
  ShieldAlert, 
  User, 
  BrainCircuit, 
  Activity 
} from 'lucide-react';

export default function Home() {
  return (
    <main className="min-h-screen bg-ink-950 text-white font-sans relative overflow-hidden select-none">
      
      {/* Background Neon Glow Circles */}
      <div className="absolute top-[-10%] right-[-10%] h-[500px] w-[500px] rounded-full bg-brand-red/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[20%] left-[-10%] h-[600px] w-[600px] rounded-full bg-brand-blue/5 blur-[150px] pointer-events-none" />
      
      {/* Navbar Header */}
      <header className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between relative z-10">
        <div className="text-xl font-black tracking-tight select-none">
          ONETAP<span className="text-brand-red">AI</span>
        </div>
        
        {/* Navigation links & Single Unified Auth button */}
        <nav className="flex items-center gap-8">
          <a href="#features" className="hidden md:inline text-xs font-bold uppercase tracking-widest text-muted hover:text-white transition-colors">Features</a>
          <a href="#tools" className="hidden md:inline text-xs font-bold uppercase tracking-widest text-muted hover:text-white transition-colors">Tools</a>
          <a href="#coach" className="hidden md:inline text-xs font-bold uppercase tracking-widest text-muted hover:text-white transition-colors">AI Coach</a>
          
          <Link 
            href="/dashboard" 
            className="glow-red inline-flex items-center gap-2 rounded-xl bg-brand-red px-5 py-2.5 text-xs font-black uppercase tracking-widest text-white transition hover:bg-brand-red-soft"
          >
            <User size={12} />
            <span>Sign In / Sign Up</span>
          </Link>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-6 pt-12 pb-24 grid lg:grid-cols-2 gap-12 items-center relative z-10">
        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-brand-red/30 bg-brand-red/5 text-[10px] font-black uppercase tracking-widest text-brand-red animate-pulse">
            <Sparkles size={10} />
            <span>RAG Ingestion Engine Active</span>
          </div>
          <h1 className="text-4xl sm:text-6xl font-black tracking-tight leading-none uppercase">
            Radiant-Level <span className="text-brand-red">Tactics.</span><br />
            Machine <span className="text-brand-blue">Precision.</span>
          </h1>
          <p className="text-sm sm:text-base leading-relaxed text-muted max-w-lg">
            OneTap AI goes beyond simple K/D ratios. By analyzing your raw spatial match telemetry, weapon recoil patterns, and engagement coordinates, we deliver personalized training regimens to level up your gameplay.
          </p>
          
          <div className="flex flex-wrap gap-4 pt-4">
            <Link 
              href="/dashboard" 
              className="glow-red inline-flex items-center gap-2 rounded-xl bg-brand-red px-6 py-3.5 text-xs font-black uppercase tracking-widest text-white transition hover:bg-brand-red-soft"
            >
              <span>Get Started</span>
              <ChevronRight size={14} />
            </Link>
            <a 
              href="#tools" 
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.02] px-6 py-3.5 text-xs font-black uppercase tracking-widest text-white transition hover:bg-white/[0.06] hover:border-white/20"
            >
              Explore Tools
            </a>
          </div>
        </div>

        {/* Hero Visual Mockup */}
        <div className="relative w-full max-w-lg mx-auto lg:ml-auto group cursor-default">
          <div className="absolute inset-0 bg-gradient-to-tr from-brand-red/10 to-brand-blue/10 rounded-3xl blur-2xl group-hover:scale-105 transition-transform duration-700 pointer-events-none" />
          <div className="relative rounded-3xl border border-white/5 bg-ink-900/50 backdrop-blur-2xl p-6 shadow-2xl flex flex-col gap-6">
            <div className="flex items-center gap-2 pb-4 border-b border-white/5">
              <span className="w-2.5 h-2.5 rounded-full bg-brand-red" />
              <span className="w-2.5 h-2.5 rounded-full bg-brand-blue" />
              <span className="w-2.5 h-2.5 rounded-full bg-muted/30" />
              <span className="text-[9px] font-black uppercase tracking-widest text-muted/60 ml-2">coaching_dashboard_preview.sys</span>
            </div>
            
            {/* Mockup Card 1: Aim profile */}
            <div className="rounded-xl border border-white/5 bg-ink-950/40 p-4 flex justify-between items-center">
              <div>
                <span className="text-[8px] font-black text-brand-blue uppercase tracking-widest">Aim Diagnostics</span>
                <h4 className="text-sm font-bold text-white mt-1">Crosshair Placement Error</h4>
              </div>
              <span className="text-xs font-bold text-brand-red bg-brand-red/10 border border-brand-red/20 px-2 py-0.5 rounded uppercase">Too Low</span>
            </div>

            {/* Mockup Card 2: AI advice */}
            <div className="rounded-xl border border-white/5 bg-ink-950/40 p-4 space-y-2">
              <div className="flex items-center gap-1.5">
                <BrainCircuit size={12} className="text-brand-red" />
                <span className="text-[8px] font-black text-brand-red uppercase tracking-widest">Coach Recommendation</span>
              </div>
              <p className="text-xs leading-relaxed text-white/80 italic">
                "Your Headshot % drops by 14% at ranges exceeding 20m. Stop spraying; integrate A-D counter-strafing and fire 2-bullet taps."
              </p>
            </div>

            {/* Mockup Card 3: Consistency */}
            <div className="rounded-xl border border-white/5 bg-ink-950/40 p-4 flex justify-between items-center">
              <div>
                <span className="text-[8px] font-black text-brand-blue uppercase tracking-widest">Combat Stability</span>
                <h4 className="text-sm font-bold text-white mt-1">ACS Variance Coefficient</h4>
              </div>
              <span className="text-xs font-bold text-brand-blue bg-brand-blue/10 border border-brand-blue/20 px-2 py-0.5 rounded uppercase">0.42 (High)</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features Overview */}
      <section id="features" className="border-t border-white/5 bg-ink-950/40 py-24 relative z-10 scroll-mt-6">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-xl space-y-3 mb-16">
            <span className="text-[10px] font-black text-brand-blue uppercase tracking-widest">Performance Benefits</span>
            <h2 className="text-3xl sm:text-4xl font-black uppercase tracking-tight">How We Improve Your Rank</h2>
            <p className="text-sm leading-relaxed text-muted">
              Rather than generic gaming tips, we extract raw data logs from your recent matches, analyze them against competitive database bounds, and output actionable instructions.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {/* Benefit 1 */}
            <div className="rounded-2xl border border-white/5 bg-ink-900/40 p-6 space-y-4 hover:border-white/10 transition-colors">
              <div className="h-10 w-10 rounded-xl bg-brand-red/10 border border-brand-red/20 flex items-center justify-center text-brand-red">
                <Target size={18} />
              </div>
              <h3 className="text-lg font-black uppercase tracking-wide">Calibrate Mechanics</h3>
              <p className="text-xs leading-relaxed text-muted">
                Analyze your hit distribution (head, body, leg) across ranges and calibrate your in-game sensitivity (eDPI) to correct micro-adjustments and spray errors.
              </p>
            </div>

            {/* Benefit 2 */}
            <div className="rounded-2xl border border-white/5 bg-ink-900/40 p-6 space-y-4 hover:border-white/10 transition-colors">
              <div className="h-10 w-10 rounded-xl bg-brand-blue/10 border border-brand-blue/20 flex items-center justify-center text-brand-blue">
                <BrainCircuit size={18} />
              </div>
              <h3 className="text-lg font-black uppercase tracking-wide">Radiant Coaching</h3>
              <p className="text-xs leading-relaxed text-muted">
                Interact with an AI Coach powered by Retrieval-Augmented Generation (RAG) that references playbooks, map defaults, and agent guides to answer questions.
              </p>
            </div>

            {/* Benefit 3 */}
            <div className="rounded-2xl border border-white/5 bg-ink-900/40 p-6 space-y-4 hover:border-white/10 transition-colors">
              <div className="h-10 w-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-white">
                <Activity size={18} />
              </div>
              <h3 className="text-lg font-black uppercase tracking-wide">Eliminate Inconsistency</h3>
              <p className="text-xs leading-relaxed text-muted">
                Identify "feast-or-famine" scoring streaks. Measure your Average Combat Score variance to teach you secure, high-value trading instead of risky solo peeks.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Tools Detail Section */}
      <section id="tools" className="border-t border-white/5 py-24 relative z-10 scroll-mt-6">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-xl space-y-3 mb-16">
            <span className="text-[10px] font-black text-brand-red uppercase tracking-widest">Analytics Suite</span>
            <h2 className="text-3xl sm:text-4xl font-black uppercase tracking-tight">Our Analytical Toolkit</h2>
            <p className="text-sm leading-relaxed text-muted">
              Unlock a suite of diagnostic modules designed to evaluate every aspect of your performance.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            
            {/* Tool 1 */}
            <div className="rounded-2xl border border-white/5 bg-ink-900/20 p-5 flex flex-col justify-between h-56 hover:border-brand-red/30 transition-colors group">
              <div className="space-y-3">
                <span className="text-[8px] font-black text-brand-red uppercase tracking-widest">Module 01</span>
                <h4 className="text-base font-black uppercase tracking-wide text-white">3D Agent Hologram</h4>
                <p className="text-[11px] leading-relaxed text-muted">
                  A fully interactive 3D WebGL projection of your top agent. Drag to rotate 360° to inspect details while holographic scanning laser rings trace the model.
                </p>
              </div>
              <ChevronRight size={16} className="text-muted group-hover:text-brand-red group-hover:translate-x-1 transition-all" />
            </div>

            {/* Tool 2 */}
            <div className="rounded-2xl border border-white/5 bg-ink-900/20 p-5 flex flex-col justify-between h-56 hover:border-brand-red/30 transition-colors group">
              <div className="space-y-3">
                <span className="text-[8px] font-black text-brand-red uppercase tracking-widest">Module 02</span>
                <h4 className="text-base font-black uppercase tracking-wide text-white">RAG Live Coach</h4>
                <p className="text-[11px] leading-relaxed text-muted">
                  A live chat monitor utilizing semantic vector search to retrieve sections of detailed agent, map, and mechanical playbooks, grounding recommendations in your stats.
                </p>
              </div>
              <ChevronRight size={16} className="text-muted group-hover:text-brand-red group-hover:translate-x-1 transition-all" />
            </div>

            {/* Tool 3 */}
            <div className="rounded-2xl border border-white/5 bg-ink-900/20 p-5 flex flex-col justify-between h-56 hover:border-brand-red/30 transition-colors group">
              <div className="space-y-3">
                <span className="text-[8px] font-black text-brand-red uppercase tracking-widest">Module 03</span>
                <h4 className="text-base font-black uppercase tracking-wide text-white">Spatial Minimap Heatmaps</h4>
                <p className="text-[11px] leading-relaxed text-muted">
                  Plots your exact coordinates of death and kill events on calibrated top-down map layouts, helping you identify bad angles, spacing errors, and crossfire exposure.
                </p>
              </div>
              <ChevronRight size={16} className="text-muted group-hover:text-brand-red group-hover:translate-x-1 transition-all" />
            </div>

            {/* Tool 4 */}
            <div className="rounded-2xl border border-white/5 bg-ink-900/20 p-5 flex flex-col justify-between h-56 hover:border-brand-blue/30 transition-colors group">
              <div className="space-y-3">
                <span className="text-[8px] font-black text-brand-blue uppercase tracking-widest">Module 04</span>
                <h4 className="text-base font-black uppercase tracking-wide text-white">ACS Trajectory charts</h4>
                <p className="text-[11px] leading-relaxed text-muted">
                  Visualize your combat performance trend over matches. Identifies swings in form, match outcomes, and tracks average scoring slope.
                </p>
              </div>
              <ChevronRight size={16} className="text-muted group-hover:text-brand-blue group-hover:translate-x-1 transition-all" />
            </div>

            {/* Tool 5 */}
            <div className="rounded-2xl border border-white/5 bg-ink-900/20 p-5 flex flex-col justify-between h-56 hover:border-brand-blue/30 transition-colors group">
              <div className="space-y-3">
                <span className="text-[8px] font-black text-brand-blue uppercase tracking-widest">Module 05</span>
                <h4 className="text-base font-black uppercase tracking-wide text-white">Advanced Telemetry Matrix</h4>
                <p className="text-[11px] leading-relaxed text-muted">
                  Provides granular metrics like average Time-to-Damage, movement error percentages, first blood differentials, and economy round win rates.
                </p>
              </div>
              <ChevronRight size={16} className="text-muted group-hover:text-brand-blue group-hover:translate-x-1 transition-all" />
            </div>

            {/* Tool 6 */}
            <div className="rounded-2xl border border-white/5 bg-ink-900/20 p-5 flex flex-col justify-between h-56 hover:border-brand-blue/30 transition-colors group">
              <div className="space-y-3">
                <span className="text-[8px] font-black text-brand-blue uppercase tracking-widest">Module 06</span>
                <h4 className="text-base font-black uppercase tracking-wide text-white">Shareable Story Cards</h4>
                <p className="text-[11px] leading-relaxed text-muted">
                  Instantly exports a beautiful 1080×1920 portrait story card featuring your custom wideart banner, best maps, stats, and AI summary to share on social media.
                </p>
              </div>
              <ChevronRight size={16} className="text-muted group-hover:text-brand-blue group-hover:translate-x-1 transition-all" />
            </div>

          </div>
        </div>
      </section>

      {/* RAG Coach Deep-Dive Section */}
      <section id="coach" className="border-t border-white/5 bg-gradient-to-b from-ink-950 to-ink-900 py-24 relative z-10 scroll-mt-6">
        <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-12 items-center">
          
          <div className="space-y-6">
            <span className="text-[10px] font-black text-brand-red uppercase tracking-widest">Grounded Intelligence</span>
            <h2 className="text-3xl sm:text-4xl font-black uppercase tracking-tight leading-tight">
              An AI Coach that Knows the Game Inside Out
            </h2>
            <p className="text-sm leading-relaxed text-muted">
              Unlike chat assistants that give generic shooting advice, our Live Coach is grounded via a custom Retrieval-Augmented Generation (RAG) vector database containing comprehensive playbooks, site execution strategies, and mechanical diagnostics.
            </p>
            <div className="space-y-3">
              <div className="flex gap-3">
                <div className="h-5 w-5 rounded-full bg-brand-red/10 border border-brand-red/20 flex items-center justify-center text-brand-red text-xs font-bold">1</div>
                <p className="text-xs text-muted leading-relaxed"><strong className="text-white">Profile Extraction:</strong> Reads your stats, HS%, and movement errors directly from the MySQL database.</p>
              </div>
              <div className="flex gap-3">
                <div className="h-5 w-5 rounded-full bg-brand-red/10 border border-brand-red/20 flex items-center justify-center text-brand-red text-xs font-bold">2</div>
                <p className="text-xs text-muted leading-relaxed"><strong className="text-white">Vector Ingestion:</strong> Cross-references your query against 38 custom coaching chunks loaded into Qdrant.</p>
              </div>
              <div className="flex gap-3">
                <div className="h-5 w-5 rounded-full bg-brand-red/10 border border-brand-red/20 flex items-center justify-center text-brand-red text-xs font-bold">3</div>
                <p className="text-xs text-muted leading-relaxed"><strong className="text-white">Radiant Advice:</strong> Prescribes clear Aim Down Sight checks, counter-strafe practices, and site pathing advice.</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-white/5 bg-ink-950/60 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <span className="text-[9px] font-black text-brand-red uppercase tracking-widest">Coaching Query Sandbox</span>
              <span className="text-[8px] font-black text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 uppercase tracking-widest">Grounded</span>
            </div>
            <div className="space-y-3">
              <div className="p-3 bg-brand-red/10 border border-brand-red/20 rounded-xl rounded-tr-none text-xs text-right ml-12">
                "How do I fix my low headshot percentage on Jett?"
              </div>
              <div className="p-3 bg-white/[0.02] border border-white/5 rounded-xl rounded-tl-none text-xs text-left mr-12 space-y-2">
                <div className="text-[8px] font-bold text-brand-blue uppercase tracking-widest">OneTap AI Coach</div>
                <p className="leading-relaxed text-white/90">
                  "Based on your profile, your HS% is 11.2% while your wide-swing peeks sit at 68%. You are over-swinging into pre-aimed crosshairs. Clear angles one by one and use tight shoulder peeks. Practice the 15m recoil reset drill."
                </p>
                <div className="pt-2 border-t border-white/5 flex gap-1.5">
                  <span className="text-[8px] font-black text-brand-blue bg-brand-blue/5 border border-brand-blue/20 rounded px-1.5 py-0.5">AGENT PLAYBOOK</span>
                  <span className="text-[8px] font-black text-brand-blue bg-brand-blue/5 border border-brand-blue/20 rounded px-1.5 py-0.5">AIM CORRECTION</span>
                </div>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* CTA Footer Section */}
      <section className="border-t border-white/5 py-24 text-center relative z-10">
        <div className="max-w-2xl mx-auto px-6 space-y-6">
          <h2 className="text-3xl sm:text-5xl font-black uppercase tracking-tight">Ready to Lock In?</h2>
          <p className="text-sm leading-relaxed text-muted">
            Create your account today, sync your Riot ID, and unlock Radiant-level strategic coaching and aim profiles.
          </p>
          <div className="pt-4">
            <Link 
              href="/dashboard" 
              className="glow-red inline-flex items-center gap-2.5 rounded-xl bg-brand-red px-8 py-4 text-sm font-black uppercase tracking-widest text-white transition hover:bg-brand-red-soft"
            >
              <User size={14} />
              <span>Sign In / Sign Up</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer Branding */}
      <footer className="border-t border-white/5 py-12 relative z-10 text-center text-[10px] text-muted uppercase tracking-widest">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="font-black text-white">
            ONETAP<span className="text-brand-red">AI</span> © 2026
          </div>
          <div>
            AI-Powered Valorant Performance Insights
          </div>
        </div>
      </footer>

    </main>
  );
}
