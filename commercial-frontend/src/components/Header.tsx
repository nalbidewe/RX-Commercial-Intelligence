import { useEffect, useRef, useState } from 'react';

interface HeaderProps {
  onLogout: () => void;
}

export default function Header({ onLogout }: HeaderProps) {
  const [user, setUser] = useState<string>('preview@vendor.riyadhair.com');
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    fetch('/api/commercial/me', { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data: { upn?: string } | null) => {
        if (cancelled || !data) return;
        if (data.upn) setUser(data.upn);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function handleLogout() {
    setMenuOpen(false);
    if (import.meta.env.DEV) {
      onLogout();
    } else {
      window.location.href = `/.auth/logout?post_logout_redirect_uri=${encodeURIComponent('/commercial/')}`;
    }
  }

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
            src={`${import.meta.env.BASE_URL}riyadh-air-logo.png`}
            alt="Riyadh Air"
            className="h-10 w-auto"
            onError={(e) => { (e.currentTarget as HTMLImageElement).onerror = null; }}
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

        {/* Right — Profile avatar with dropdown */}
        <div className="relative flex items-center justify-end" ref={menuRef}>
          <div className="hidden sm:flex flex-col items-end leading-tight mr-3">
            <span className="text-sm font-medium text-rx-ink capitalize">{displayName}</span>
            <span className="text-[11px] text-rx-subtle truncate max-w-[180px]">{user}</span>
          </div>

          {/* Avatar button */}
          <button
            type="button"
            onClick={() => setMenuOpen((prev) => !prev)}
            className="h-9 w-9 rounded-full bg-rx-purple text-rx-cream font-semibold flex items-center justify-center text-sm shadow-sm hover:bg-rx-purpleDark transition"
            title={user}
          >
            {initials || 'U'}
          </button>

          {/* Dropdown */}
          {menuOpen && (
            <div className="absolute top-full mt-2 right-0 w-56 bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden z-50">
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-xs text-rx-subtle truncate">{user}</p>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-4 py-3 text-sm text-rx-ink hover:bg-gray-50 transition text-left"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
