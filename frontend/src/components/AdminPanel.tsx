"use client";

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import AuthOverlay from './dashboard/AuthOverlay';
import {
  AdminOverview,
  AdminUser,
  AdminUserList,
  fetchAdminOverview,
  fetchAdminUsers,
  setUserDisabled,
} from '@/lib/api';
import {
  Users, UserPlus, Radio, Shield, ShieldOff, Search, ChevronLeft, ChevronRight,
  Database, MessageSquare, ThumbsUp, RefreshCw, ArrowLeft, Ban, CheckCircle2,
} from 'lucide-react';

function timeAgo(iso: string | null): string {
  if (!iso) return 'never';
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function StatTile({ icon, label, value, sub, accent = 'red' }: {
  icon: React.ReactNode; label: string; value: string | number; sub?: string; accent?: 'red' | 'blue';
}) {
  return (
    <div className="rounded-2xl bg-ink-700/60 border border-line/60 p-4 backdrop-blur">
      <div className="flex items-center gap-2 mb-2">
        <span className={accent === 'red' ? 'text-brand-red' : 'text-brand-blue'}>{icon}</span>
        <span className="text-[10px] font-black uppercase tracking-widest text-muted">{label}</span>
      </div>
      <div className="text-2xl font-black text-white">{value}</div>
      {sub && <div className="text-[11px] text-muted mt-1">{sub}</div>}
    </div>
  );
}

function SignupSpark({ data }: { data: { day: string; signups: number }[] }) {
  // Fill the last 30 calendar days so gaps render as zero bars.
  const byDay = new Map(data.map((d) => [d.day, d.signups]));
  const days: { day: string; signups: number }[] = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    days.push({ day: key, signups: byDay.get(key) ?? 0 });
  }
  const max = Math.max(1, ...days.map((d) => d.signups));
  return (
    <div className="flex items-end gap-[3px] h-16" title="Signups, last 30 days">
      {days.map((d) => (
        <div
          key={d.day}
          className="flex-1 rounded-t bg-brand-red/70 hover:bg-brand-red transition-colors min-h-[2px]"
          style={{ height: `${Math.max(3, (d.signups / max) * 100)}%` }}
          title={`${d.day}: ${d.signups} signup${d.signups === 1 ? '' : 's'}`}
        />
      ))}
    </div>
  );
}

export default function AdminPanel() {
  const { user, isLoggedIn, authLoading } = useAuth();
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [userList, setUserList] = useState<AdminUserList | null>(null);
  const [q, setQ] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [status, setStatus] = useState('all');
  const [sort, setSort] = useState('created');
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [confirming, setConfirming] = useState<AdminUser | null>(null);

  useEffect(() => {
    const t = setTimeout(() => { setDebouncedQ(q); setPage(1); }, 350);
    return () => clearTimeout(t);
  }, [q]);

  const loadOverview = useCallback(() => {
    fetchAdminOverview().then(setOverview).catch((e) => setError(e.message));
  }, []);

  const loadUsers = useCallback(() => {
    fetchAdminUsers({ q: debouncedQ, status, sort, page })
      .then(setUserList)
      .catch((e) => setError(e.message));
  }, [debouncedQ, status, sort, page]);

  useEffect(() => {
    if (!isLoggedIn || !user?.is_admin) return;
    setError(null);
    loadOverview();
  }, [isLoggedIn, user, loadOverview]);

  useEffect(() => {
    if (!isLoggedIn || !user?.is_admin) return;
    loadUsers();
  }, [isLoggedIn, user, loadUsers]);

  if (authLoading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-ink-950 text-white select-none">
        <div className="text-[10px] font-black uppercase tracking-widest text-brand-blue/80 animate-pulse">
          Loading admin console...
        </div>
      </div>
    );
  }
  if (!isLoggedIn) return <AuthOverlay />;
  if (!user?.is_admin) {
    return (
      <div className="min-h-screen w-full flex flex-col items-center justify-center bg-ink-950 text-white gap-4 select-none">
        <ShieldOff size={40} className="text-brand-red" />
        <div className="text-lg font-black uppercase tracking-widest">Access denied</div>
        <p className="text-xs text-muted max-w-xs text-center">
          This area is restricted to administrators.
        </p>
        <Link href="/dashboard" className="text-[11px] font-bold text-brand-blue hover:text-brand-blue-soft uppercase tracking-widest">
          ← Back to dashboard
        </Link>
      </div>
    );
  }

  const toggleUser = async (u: AdminUser) => {
    setBusy(u.id);
    setError(null);
    try {
      await setUserDisabled(u.id, !u.is_disabled);
      setUserList((prev) => prev && {
        ...prev,
        users: prev.users.map((x) => (x.id === u.id ? { ...x, is_disabled: !u.is_disabled } : x)),
      });
      loadOverview();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setBusy(null);
      setConfirming(null);
    }
  };

  const totalPages = userList ? Math.max(1, Math.ceil(userList.total / userList.per_page)) : 1;
  const uo = overview?.users;
  const po = overview?.platform;
  const fbPct = po && po.coach_feedback_total > 0
    ? Math.round((po.coach_feedback_positive / po.coach_feedback_total) * 100)
    : null;

  return (
    <div className="min-h-screen w-full bg-ink-950 text-white px-4 py-8 select-none">
      <div className="mx-auto max-w-6xl space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="text-muted hover:text-white transition" title="Back to dashboard">
              <ArrowLeft size={18} />
            </Link>
            <h1 className="text-xl font-black uppercase tracking-widest">
              Admin <span className="text-brand-red">Console</span>
            </h1>
          </div>
          <button
            onClick={() => { loadOverview(); loadUsers(); }}
            className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-muted hover:text-white transition cursor-pointer"
          >
            <RefreshCw size={12} /> Refresh
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-xl border border-brand-red/20 bg-brand-red/5 text-xs text-brand-red font-semibold">
            {error}
          </div>
        )}

        {/* Stat tiles */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatTile icon={<Users size={14} />} label="Total users" value={uo?.total ?? '—'}
            sub={uo ? `${uo.disabled} disabled · ${uo.admins} admin${uo.admins === 1 ? '' : 's'}` : undefined} />
          <StatTile icon={<UserPlus size={14} />} label="Signups" value={uo?.signups_24h ?? '—'}
            sub={uo ? `last 24h · ${uo.signups_7d} this week` : undefined} />
          <StatTile icon={<Radio size={14} />} label="Active now" value={uo?.active_now ?? '—'} accent="blue"
            sub={uo ? `15-min window · ${uo.active_24h} today · ${uo.active_7d} this week` : undefined} />
          <StatTile icon={<Shield size={14} />} label="Linked Riot IDs" value={uo?.linked_riot ?? '—'} accent="blue"
            sub={uo && uo.total > 0 ? `${Math.round((uo.linked_riot / uo.total) * 100)}% of users` : undefined} />
        </div>

        {/* Signup trend + platform stats */}
        <div className="grid md:grid-cols-3 gap-3">
          <div className="md:col-span-2 rounded-2xl bg-ink-700/60 border border-line/60 p-4">
            <div className="text-[10px] font-black uppercase tracking-widest text-muted mb-3">
              Signups · Last 30 days
            </div>
            {overview ? <SignupSpark data={overview.signups_by_day} /> : <div className="h-16 animate-pulse bg-ink-600/40 rounded" />}
          </div>
          <div className="rounded-2xl bg-ink-700/60 border border-line/60 p-4 space-y-2.5">
            <div className="text-[10px] font-black uppercase tracking-widest text-muted mb-1">Platform</div>
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-muted"><Database size={12} /> Matches ingested</span>
              <span className="font-bold">{po?.matches_ingested ?? '—'}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-muted"><Users size={12} /> Players tracked</span>
              <span className="font-bold">{po?.players_tracked ?? '—'}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-muted"><Search size={12} /> Searches (24h)</span>
              <span className="font-bold">{po?.searches_24h ?? '—'}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-muted"><MessageSquare size={12} /> Coach feedback</span>
              <span className="font-bold">{po?.coach_feedback_total ?? '—'}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-muted"><ThumbsUp size={12} /> Positive rate</span>
              <span className="font-bold">{fbPct === null ? '—' : `${fbPct}%`}</span>
            </div>
          </div>
        </div>

        {/* User table */}
        <div className="rounded-2xl bg-ink-700/60 border border-line/60 overflow-hidden">
          <div className="p-4 flex flex-wrap items-center gap-3 border-b border-line/60">
            <div className="relative flex-1 min-w-[220px]">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search username, email, or Riot ID..."
                className="w-full bg-ink-950/60 border border-line/60 focus:border-brand-red/40 rounded-xl pl-8 pr-3 py-2 text-xs outline-none placeholder:text-muted/50 transition"
              />
            </div>
            <select
              value={status}
              onChange={(e) => { setStatus(e.target.value); setPage(1); }}
              className="bg-ink-950/60 border border-line/60 rounded-xl px-3 py-2 text-xs outline-none cursor-pointer"
            >
              <option value="all">All users</option>
              <option value="active">Active</option>
              <option value="disabled">Disabled</option>
              <option value="admins">Admins</option>
            </select>
            <select
              value={sort}
              onChange={(e) => { setSort(e.target.value); setPage(1); }}
              className="bg-ink-950/60 border border-line/60 rounded-xl px-3 py-2 text-xs outline-none cursor-pointer"
            >
              <option value="created">Newest first</option>
              <option value="last_seen">Recently active</option>
              <option value="username">Username A–Z</option>
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-[10px] font-black uppercase tracking-widest text-muted border-b border-line/60">
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">Riot ID</th>
                  <th className="px-4 py-3">Joined</th>
                  <th className="px-4 py-3">Last seen</th>
                  <th className="px-4 py-3 text-right">Searches</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {userList?.users.map((u) => (
                  <tr key={u.id} className="border-b border-line/30 hover:bg-ink-600/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-bold text-white flex items-center gap-1.5">
                        {u.username}
                        {u.is_admin && <Shield size={11} className="text-brand-blue" />}
                      </div>
                      <div className="text-muted">{u.email}</div>
                    </td>
                    <td className="px-4 py-3 text-muted">{u.linked_riot_id ?? '—'}</td>
                    <td className="px-4 py-3 text-muted" title={u.created_at ?? ''}>{timeAgo(u.created_at)}</td>
                    <td className="px-4 py-3 text-muted" title={u.last_seen_at ?? ''}>{timeAgo(u.last_seen_at)}</td>
                    <td className="px-4 py-3 text-right text-muted">{u.searches}</td>
                    <td className="px-4 py-3">
                      {u.is_disabled ? (
                        <span className="inline-flex items-center gap-1 text-brand-red font-bold"><Ban size={11} /> Disabled</span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-bold"><CheckCircle2 size={11} /> Active</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {u.is_admin ? (
                        <span className="text-muted/50 text-[10px] uppercase tracking-wider">Protected</span>
                      ) : confirming?.id === u.id ? (
                        <span className="inline-flex items-center gap-2">
                          <button
                            onClick={() => toggleUser(u)}
                            disabled={busy === u.id}
                            className="text-[10px] font-black uppercase tracking-wider text-brand-red hover:text-brand-red-soft disabled:opacity-50 cursor-pointer"
                          >
                            {busy === u.id ? '...' : 'Confirm'}
                          </button>
                          <button
                            onClick={() => setConfirming(null)}
                            className="text-[10px] font-black uppercase tracking-wider text-muted hover:text-white cursor-pointer"
                          >
                            Cancel
                          </button>
                        </span>
                      ) : (
                        <button
                          onClick={() => (u.is_disabled ? toggleUser(u) : setConfirming(u))}
                          disabled={busy === u.id}
                          className={`text-[10px] font-black uppercase tracking-wider cursor-pointer disabled:opacity-50 ${
                            u.is_disabled
                              ? 'text-emerald-400 hover:text-emerald-300'
                              : 'text-brand-red hover:text-brand-red-soft'
                          }`}
                        >
                          {busy === u.id ? '...' : u.is_disabled ? 'Enable' : 'Disable'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {userList && userList.users.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-muted">No users match this filter.</td>
                  </tr>
                )}
                {!userList && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-muted animate-pulse">Loading users...</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="p-3 flex items-center justify-between border-t border-line/60 text-[11px] text-muted">
            <span>
              {userList ? `${userList.total} user${userList.total === 1 ? '' : 's'}` : '—'}
            </span>
            <span className="inline-flex items-center gap-3">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="disabled:opacity-30 hover:text-white transition cursor-pointer"
              >
                <ChevronLeft size={14} />
              </button>
              <span className="font-bold text-white">{page} / {totalPages}</span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="disabled:opacity-30 hover:text-white transition cursor-pointer"
              >
                <ChevronRight size={14} />
              </button>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
