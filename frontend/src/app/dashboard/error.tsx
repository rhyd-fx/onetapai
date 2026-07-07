"use client";

// Route-level error boundary for /dashboard. Catches any render error so the
// user sees a recoverable message instead of a blank/broken page.
export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto grid min-h-[60vh] max-w-lg place-items-center px-6 text-center">
      <div>
        <h2 className="text-2xl font-bold text-white">Something went wrong rendering the dashboard</h2>
        <p className="mt-2 break-words text-sm text-muted">{error.message}</p>
        <button
          onClick={reset}
          className="glow-red mt-6 rounded-xl bg-brand-red px-5 py-3 text-sm font-bold uppercase tracking-widest text-white transition hover:bg-brand-red-soft"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
