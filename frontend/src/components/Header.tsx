import { useEffect, useState } from 'react';

interface AuthMe {
  clientPrincipal?: {
    userDetails?: string;
    userId?: string;
  };
}

/**
 * Header — RX-branded top bar.
 *
 * Layout (3-column grid):
 *   [logo, left]    [title, centered]    [user, right]
 *
 * The user is derived from the Easy Auth `/.auth/me` endpoint that
 * Container Apps exposes automatically. During local dev the fetch fails
 * silently and falls back to a preview UPN.
 */
export default function Header() {
  const [user, setUser] = useState<string>('preview@vendor.riyadhair.com');

  useEffect(() => {
    let cancelled = false;
    fetch('/.auth/me')
      .then((res) => (res.ok ? res.json() : null))
      .then((data: AuthMe | null) => {
        if (cancelled || !data) return;
        const upn = data.clientPrincipal?.userDetails;
        if (upn) setUser(upn);
      })
      .catch(() => {
        /* local dev — no Easy Auth in front of Vite, ignore */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const displayName = user.split('@')[0]?.replace(/\./g, ' ') ?? user;
  const initials = user
    .split(/[.@\s]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? '')
    .join('');

  return (
    <header className="sticky top-0 z-10 bg-white/95 backdrop-blur border-b border-rx-purple/10 shadow-sm">
      <div className="mx-auto max-w-6xl grid grid-cols-3 items-center px-6 py-3">
        {/* Left — Riyadh Air logo */}
        <div className="flex items-center justify-start">
          <img
            src="/riyadh-air-logo.png"
            alt="Riyadh Air"
            className="h-10 w-auto"
            onError={(e) => {
              // Fallback to the placeholder SVG if PNG hasn't been added yet
              (e.currentTarget as HTMLImageElement).src = '/riyadh-air-logo.svg';
            }}
          />
        </div>

        {/* Center — Title + tagline */}
        <div className="flex flex-col items-center text-center">
          <div className="text-rx-purple font-bold tracking-tight text-lg leading-tight">
            Commercial Intelligence
          </div>
          <div className="text-rx-subtle text-[11px] uppercase tracking-[0.18em] mt-0.5">
            Powered by ROAA
          </div>
        </div>

        {/* Right — User chip */}
        <div className="flex items-center justify-end gap-3">
          <div className="hidden sm:flex flex-col items-end leading-tight">
            <span className="text-sm font-medium text-rx-ink capitalize">
              {displayName}
            </span>
            <span className="text-[11px] text-rx-subtle truncate max-w-[180px]">
              {user}
            </span>
          </div>
          <div
            className="h-9 w-9 rounded-full bg-rx-purple text-rx-cream font-semibold flex items-center justify-center text-sm shadow-sm"
            title={user}
          >
            {initials || 'U'}
          </div>
        </div>
      </div>
    </header>
  );
}
