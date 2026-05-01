import { useEffect, useState } from 'react';

interface AuthMe {
  clientPrincipal?: {
    userDetails?: string;
    userId?: string;
  };
}

/**
 * Header — RX-branded top bar with logo, title, and signed-in user avatar.
 *
 * The user avatar is derived from the Easy Auth `/.auth/me` endpoint that
 * Container Apps exposes automatically. During local dev the fetch will
 * fail silently and the avatar falls back to "you".
 */
export default function Header() {
  const [user, setUser] = useState<string>('you');

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

  const initials = user
    .split(/[.@\s]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? '')
    .join('');

  return (
    <header className="sticky top-0 z-10 bg-rx-cream border-b border-rx-purple/10">
      <div className="mx-auto max-w-5xl flex items-center gap-3 px-6 py-3">
        <img src="/riyadh-air-logo.svg" alt="Riyadh Air" className="h-9 w-9" />
        <div className="flex-1">
          <div className="text-rx-ink font-semibold leading-tight">
            Commercial Agent
          </div>
          <div className="text-rx-subtle text-xs">RX Commercial Intelligence</div>
        </div>
        <div
          className="h-9 w-9 rounded-full bg-rx-purple text-rx-cream font-semibold flex items-center justify-center text-sm"
          title={user}
        >
          {initials || 'U'}
        </div>
      </div>
    </header>
  );
}
