"use client";

import { useEffect, useRef, useState } from 'react';
import { Send, ThumbsUp, ThumbsDown, Cpu, BookOpen, Sparkles } from 'lucide-react';
import { askCoach, submitFeedback, CoachSource } from '@/lib/api';
import Markdown from './Markdown';

interface Msg {
  role: 'ai' | 'user';
  content: string;
  sources?: CoachSource[];
  question?: string;
  rated?: 1 | -1;
}

export default function CoachPanel({ riotId, region }: { riotId?: string; region?: string }) {
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: 'ai',
      content: riotId
        ? `I've loaded ${riotId}. Ask me about your aim, positioning, economy, or mental game.`
        : 'Search a player above, then ask me anything about their gameplay.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messages.length <= 1) return;
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [messages, loading]);

  const send = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: q }]);
    setLoading(true);
    try {
      const res = await askCoach(riotId ?? '', q, region ?? 'na');
      setMessages((m) => [...m, { role: 'ai', content: res.answer, sources: res.sources_used, question: q }]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Request failed';
      setMessages((m) => [
        ...m,
        { role: 'ai', content: `⚠️ ${msg}\n\nIs the backend running at ${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}?` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const rate = (i: number, r: 1 | -1) => {
    const msg = messages[i];
    if (!msg.question || msg.rated) return;
    submitFeedback({ question: msg.question, rating: r, riotId, answerExcerpt: msg.content.slice(0, 500), sources: msg.sources }).catch(() => {});
    setMessages((m) => m.map((mm, idx) => (idx === i ? { ...mm, rated: r } : mm)));
  };

  return (
    <div className="flex h-full flex-col">
      {/* Esports RAG Coach Status Header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-2.5 mb-3 flex-shrink-0 select-none">
        <div className="flex items-center gap-2">
          <Cpu size={14} className="text-brand-red animate-pulse" />
          <span className="text-[10px] font-black uppercase tracking-widest text-white">AI Coach Monitor</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
          </span>
          <span className="text-[8px] font-black uppercase tracking-widest text-emerald-400/90">RAG Ingestion Active</span>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1.5 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-track]:bg-white/[0.01] [&::-webkit-scrollbar-thumb]:bg-white/10 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-white/20">
        {messages.map((m, i) => (
          <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
            {/* Sender Badge */}
            <span className="text-[9px] font-bold text-muted/65 uppercase tracking-widest mb-1 px-1 select-none">
              {m.role === 'user' ? 'Player (You)' : 'OneTap Coach'}
            </span>
            
            {/* Message Bubble */}
            <div
              className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-lg ${
                m.role === 'user'
                  ? 'max-w-[85%] whitespace-pre-wrap bg-gradient-to-r from-brand-red to-brand-red-soft text-white rounded-tr-none font-medium'
                  : 'max-w-[92%] border border-white/5 bg-gradient-to-br from-white/[0.04] to-white/[0.01] text-white/90 rounded-tl-none backdrop-blur-md'
              }`}
            >
              {m.role === 'ai' ? <Markdown>{m.content}</Markdown> : m.content}
              
              {/* Citations / Sources */}
              {m.sources && m.sources.length > 0 && (
                <div className="mt-3 pt-2.5 border-t border-white/5 flex flex-wrap gap-1.5">
                  <div className="flex items-center gap-1 text-[9px] text-muted font-bold uppercase tracking-wider mr-1 select-none">
                    <BookOpen size={10} className="text-brand-blue" />
                    <span>Sources:</span>
                  </div>
                  {Array.from(new Set(m.sources.map((s) => s.source))).map((sourceName) => (
                    <span 
                      key={sourceName} 
                      className="inline-flex items-center px-2 py-0.5 rounded border border-brand-blue/20 bg-brand-blue/5 text-[8px] font-black text-brand-blue uppercase tracking-widest select-none"
                    >
                      {sourceName.replace('OneTap Coaching — ', '')}
                    </span>
                  ))}
                </div>
              )}
              
              {/* User Feedback Interface */}
              {m.question && (
                <div className="mt-2.5 pt-2 border-t border-white/5 flex items-center gap-3 select-none">
                  {m.rated ? (
                    <span className="text-[10px] text-muted/80 font-bold uppercase tracking-wider">
                      Feedback logged {m.rated === 1 ? '👍' : '👎'}
                    </span>
                  ) : (
                    <>
                      <span className="text-[9px] text-muted/50 uppercase tracking-widest font-bold">Was this helpful?</span>
                      <div className="flex items-center gap-2">
                        <button 
                          aria-label="Helpful" 
                          onClick={() => rate(i, 1)} 
                          className="p-1 rounded hover:bg-white/5 text-muted hover:text-brand-blue transition-colors cursor-pointer"
                        >
                          <ThumbsUp size={12} />
                        </button>
                        <button 
                          aria-label="Not helpful" 
                          onClick={() => rate(i, -1)} 
                          className="p-1 rounded hover:bg-white/5 text-muted hover:text-brand-red transition-colors cursor-pointer"
                        >
                          <ThumbsDown size={12} />
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Tactical Scanning Simulation Loader */}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-2xl border border-brand-red/20 bg-brand-red/5 px-4 py-3 text-sm text-brand-red animate-pulse flex items-center gap-3">
              <Sparkles size={14} className="text-brand-red animate-spin" />
              <div className="flex flex-col">
                <span className="font-extrabold text-[10px] tracking-wider uppercase">Querying Tactical Playbooks...</span>
                <span className="text-[9px] text-muted mt-0.5">Synthesizing telemetry data & metrics</span>
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input / Action Pill Bar */}
      <div className="mt-3.5 flex items-center gap-2 bg-ink-950/40 border border-white/5 focus-within:border-brand-red/30 rounded-xl p-1.5 transition-all duration-300">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask coach about aim drills, setups, or buy cycles..."
          disabled={loading}
          className="flex-1 bg-transparent px-3 py-2 text-sm text-white outline-none placeholder:text-muted/50 disabled:opacity-60"
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="grid h-9 w-9 place-items-center rounded-lg bg-brand-red text-white transition hover:bg-brand-red-soft active:scale-95 disabled:opacity-40 cursor-pointer flex-shrink-0 shadow-md"
          aria-label="Send"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
