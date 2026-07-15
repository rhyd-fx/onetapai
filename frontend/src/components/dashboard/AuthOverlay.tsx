"use client";

import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Shield, Lock, Mail, User, Eye, EyeOff, Sparkles, AlertCircle } from 'lucide-react';

export default function AuthOverlay() {
  const { login, register, verifyRegister, authError, clearError } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    clearError();
    
    if (!username.trim()) {
      setErrorMsg("Username is required.");
      return;
    }
    if (isRegister && !email.trim()) {
      setErrorMsg("Email is required.");
      return;
    }
    if (password.length < 12) {
      setErrorMsg("Password must be at least 12 characters.");
      return;
    }

    setLoading(true);
    try {
      if (isRegister) {
        await register(username.trim(), email.trim(), password);
        setIsVerifying(true);
      } else {
        await login(username.trim(), password);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "An authentication error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    clearError();

    if (!verificationCode.trim() || verificationCode.length !== 6) {
      setErrorMsg("Please enter a valid 6-digit verification code.");
      return;
    }

    setLoading(true);
    try {
      await verifyRegister(email.trim(), verificationCode.trim());
    } catch (err: any) {
      setErrorMsg(err.message || "Verification failed.");
    } finally {
      setLoading(false);
    }
  };

  if (isVerifying) {
    return (
      <div className="relative min-h-screen w-full flex items-center justify-center bg-ink-950 overflow-hidden px-4 select-none">
        {/* Abstract Background Esports Gradients */}
        <div className="absolute top-1/4 left-1/4 h-96 w-96 rounded-full bg-brand-red/10 blur-[100px] pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 h-96 w-96 rounded-full bg-brand-blue/10 blur-[100px] pointer-events-none" />
        
        {/* Blurred preview of the dashboard behind the glass auth box */}
        <div className="absolute inset-0 opacity-[0.03] bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:24px_24px] pointer-events-none" />

        {/* Verification Panel */}
        <div className="relative w-full max-w-md bg-ink-900/60 backdrop-blur-2xl border border-white/5 shadow-2xl p-8 rounded-3xl z-10 transition-all duration-300">
          
          {/* Header */}
          <div className="flex flex-col items-center mb-8">
            <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-brand-red to-brand-red-soft flex items-center justify-center shadow-lg shadow-brand-red/20 mb-3 border border-white/10">
              <Mail size={22} className="text-white" />
            </div>
            <h2 className="text-2xl font-black text-white tracking-wider uppercase">
              Verify <span className="text-brand-red">Email</span>
            </h2>
            <p className="text-xs text-muted/80 mt-2 text-center max-w-[280px]">
              We sent a 6-digit code to <strong className="text-white">{email}</strong>. Check your inbox or server logs.
            </p>
          </div>

          {/* Errors Container */}
          {(errorMsg || authError) && (
            <div className="mb-5 p-3.5 rounded-xl border border-brand-red/20 bg-brand-red/5 flex items-start gap-2.5 text-xs text-brand-red animate-shake">
              <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
              <div className="font-semibold">{errorMsg || authError}</div>
            </div>
          )}

          <form onSubmit={handleVerifySubmit} className="space-y-6">
            {/* Monospace Code Input */}
            <div className="space-y-2">
              <label className="text-[10px] font-black uppercase tracking-widest text-muted block text-center">
                Verification Code
              </label>
              <div className="relative flex items-center bg-ink-950/60 border border-white/5 focus-within:border-brand-red/30 rounded-xl px-3 transition-all duration-300">
                <input
                  type="text"
                  maxLength={6}
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="------"
                  disabled={loading}
                  className="w-full bg-transparent px-3 py-4 text-2xl font-black text-center text-white tracking-[12px] outline-none placeholder:text-muted/20 disabled:opacity-60 font-mono"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full glow-red flex items-center justify-center gap-2 rounded-xl bg-brand-red py-3.5 text-xs font-black uppercase tracking-widest text-white transition hover:bg-brand-red-soft active:scale-98 disabled:opacity-50 cursor-pointer shadow-lg"
            >
              {loading ? (
                <span className="inline-flex gap-1 items-center">
                  <Sparkles size={12} className="animate-spin" />
                  Activating...
                </span>
              ) : (
                <span>Activate Account</span>
              )}
            </button>
          </form>

          {/* Footer Back Link */}
          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setIsVerifying(false);
                setVerificationCode('');
                setErrorMsg(null);
                clearError();
              }}
              className="text-[11px] font-bold text-muted hover:text-white uppercase tracking-widest transition cursor-pointer"
            >
              &larr; Back to sign up
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen w-full flex items-center justify-center bg-ink-950 overflow-hidden px-4 select-none">
      {/* Abstract Background Esports Gradients */}
      <div className="absolute top-1/4 left-1/4 h-96 w-96 rounded-full bg-brand-red/10 blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 h-96 w-96 rounded-full bg-brand-blue/10 blur-[100px] pointer-events-none" />
      
      {/* Blurred preview of the dashboard behind the glass auth box */}
      <div className="absolute inset-0 opacity-[0.03] bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:24px_24px] pointer-events-none" />

      {/* Auth Panel */}
      <div className="relative w-full max-w-md bg-ink-900/60 backdrop-blur-2xl border border-white/5 shadow-2xl p-8 rounded-3xl z-10 transition-all duration-300">
        
        {/* Glow Header */}
        <div className="flex flex-col items-center mb-8">
          <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-brand-red to-brand-red-soft flex items-center justify-center shadow-lg shadow-brand-red/20 mb-3 border border-white/10">
            <Shield size={22} className="text-white" />
          </div>
          <h2 className="text-2xl font-black text-white tracking-wider flex items-center gap-1.5 uppercase">
            OneTap<span className="text-brand-red">AI</span>
          </h2>
          <p className="text-xs text-muted/80 mt-1 uppercase tracking-widest font-semibold text-center">
            {isRegister ? 'Create your tactical account' : 'Sign in to unlock analytics'}
          </p>
        </div>

        {/* Errors Container */}
        {(errorMsg || authError) && (
          <div className="mb-5 p-3.5 rounded-xl border border-brand-red/20 bg-brand-red/5 flex items-start gap-2.5 text-xs text-brand-red animate-shake">
            <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
            <div className="font-semibold">{errorMsg || authError}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Username / Email field */}
          <div className="space-y-1.5">
            <label className="text-[10px] font-black uppercase tracking-widest text-muted">
              {isRegister ? 'Username' : 'Username or Email'}
            </label>
            <div className="relative flex items-center bg-ink-950/60 border border-white/5 focus-within:border-brand-red/30 rounded-xl px-3 transition-all duration-300">
              <User size={16} className="text-muted/60" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={isRegister ? "Enter username..." : "Enter username or email..."}
                disabled={loading}
                className="w-full bg-transparent px-3 py-3 text-sm text-white outline-none placeholder:text-muted/40 disabled:opacity-60"
              />
            </div>
          </div>

          {/* Email field (Register Only) */}
          {isRegister && (
            <div className="space-y-1.5 animate-fade-in">
              <label className="text-[10px] font-black uppercase tracking-widest text-muted">Email Address</label>
              <div className="relative flex items-center bg-ink-950/60 border border-white/5 focus-within:border-brand-red/30 rounded-xl px-3 transition-all duration-300">
                <Mail size={16} className="text-muted/60" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter email..."
                  disabled={loading}
                  className="w-full bg-transparent px-3 py-3 text-sm text-white outline-none placeholder:text-muted/40 disabled:opacity-60"
                />
              </div>
            </div>
          )}

          {/* Password field */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label className="text-[10px] font-black uppercase tracking-widest text-muted">Password</label>
            </div>
            <div className="relative flex items-center bg-ink-950/60 border border-white/5 focus-within:border-brand-red/30 rounded-xl px-3 transition-all duration-300">
              <Lock size={16} className="text-muted/60" />
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password..."
                disabled={loading}
                className="w-full bg-transparent px-3 py-3 text-sm text-white outline-none placeholder:text-muted/40 disabled:opacity-60"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-muted/50 hover:text-white transition-colors cursor-pointer"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* CTA Action button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full glow-red flex items-center justify-center gap-2 rounded-xl bg-brand-red py-3.5 text-xs font-black uppercase tracking-widest text-white transition hover:bg-brand-red-soft active:scale-98 disabled:opacity-50 cursor-pointer shadow-lg mt-6"
          >
            {loading ? (
              <span className="inline-flex gap-1 items-center">
                <Sparkles size={12} className="animate-spin" />
                Processing...
              </span>
            ) : (
              <span>{isRegister ? 'Send Code' : 'Authenticate'}</span>
            )}
          </button>
        </form>

        {/* Footer Toggle links */}
        <div className="mt-6 text-center">
          <button
            onClick={() => {
              setIsRegister(!isRegister);
              setErrorMsg(null);
              clearError();
            }}
            className="text-[11px] font-bold text-brand-blue hover:text-brand-blue-soft uppercase tracking-widest transition cursor-pointer border border-brand-blue/20 bg-brand-blue/5 rounded-lg px-3 py-1.5"
          >
            {isRegister ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
          </button>
        </div>
      </div>
    </div>
  );
}
