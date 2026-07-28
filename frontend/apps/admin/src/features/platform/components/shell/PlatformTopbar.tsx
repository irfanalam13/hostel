"use client";

import React, { useState } from "react";
import { useAuth } from "@hostel/auth";
import { useTheme } from "@hostel/ui";
import { displayName, initials } from "@/features/account/lib";
import { ChevronDown, LogOut, Monitor, Moon, ShieldPlus, Sun } from "lucide-react";

/**
 * The super-admin app's only chrome. Deliberately minimal — no tenant
 * switcher, no notifications inbox, no command palette: none of those are
 * meaningful for a platform operator who isn't a member of any hostel. Page
 * navigation lives in PlatformShell's section pills, not here.
 */
export function PlatformTopbar() {
  const { user, logout } = useAuth();
  const { theme, resolvedTheme, setTheme } = useTheme();
  const name = displayName(user);

  const [loggingOut, setLoggingOut] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  async function onLogout() {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <header className="sticky top-0 z-40 flex h-[64px] items-center justify-between border-b border-[var(--border)] bg-[color-mix(in_srgb,var(--card)_88%,transparent)] px-6 backdrop-blur-md">
      <div className="flex items-center gap-2.5 select-none">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-soft)] text-[var(--accent)]">
          <ShieldPlus className="h-4 w-4" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-semibold text-[var(--foreground)]">Platform</span>
          <span className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            Super Admin
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() =>
            setTheme(theme === "system" ? (resolvedTheme === "dark" ? "light" : "dark") : "system")
          }
          className="flex items-center justify-center p-2 rounded-xl text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--background-secondary)] transition"
          aria-label="Change theme"
        >
          {theme === "system" ? <Monitor className="w-5 h-5" /> : theme === "light" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        <div className="relative">
          <button
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            className="flex items-center gap-2 p-1 pl-2 border border-[var(--border)] hover:bg-[var(--background-secondary)] rounded-xl transition cursor-pointer"
          >
            <div className="flex items-center justify-center w-7 h-7 rounded-full bg-[var(--accent)] text-white font-bold text-xs select-none">
              {initials(user)}
            </div>
            <div className="text-left hidden sm:block pr-1 select-none">
              <div className="text-xs font-semibold text-[var(--foreground)] leading-tight max-w-[120px] truncate">
                {name}
              </div>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-[var(--muted)] hidden sm:block shrink-0" />
          </button>

          {isProfileOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setIsProfileOpen(false)} />
              <div className="absolute right-0 mt-2 w-44 bg-[var(--card-elevated)] border border-[var(--border)] rounded-2xl shadow-[var(--shadow-lg)] z-50 overflow-hidden py-1.5">
                <button
                  onClick={onLogout}
                  disabled={loggingOut}
                  className="w-full flex items-center gap-2.5 px-4 py-2 text-xs text-[var(--error)] hover:bg-[color-mix(in_srgb,var(--error)_10%,transparent)] text-left transition disabled:opacity-50"
                >
                  <LogOut className="w-4 h-4 shrink-0" />
                  <span>{loggingOut ? "Logging out..." : "Logout"}</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
