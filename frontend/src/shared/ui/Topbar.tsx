"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { getUnreadCount, listInbox, markAllRead as apiMarkAllRead, markRead } from "@/features/notifications/api";
import type { InboxNotification } from "@/features/notifications/types";
import { useAuth } from "@/shared/auth/AuthProvider";
import { useSidebar } from "@/shared/providers/SidebarContext";
import { useTheme } from "@/shared/providers/ThemeContext";
import { usePwa } from "@/shared/providers/PwaProvider";
import { useBackgroundRefresh } from "@/shared/pwa/useBackgroundRefresh";
import { CommandPalette } from "./CommandPalette";
import {
  Menu,
  Search,
  Sun,
  Moon,
  Monitor,
  Bell,
  User,
  LogOut,
  Settings,
  ChevronDown,
  Download,
} from "lucide-react";

export function Topbar({ title = "Dashboard" }: { title?: string }) {
  const { role, logout } = useAuth();
  const { toggleSidebar, toggleMobileSidebar } = useSidebar();
  const { theme, resolvedTheme, setTheme } = useTheme();
  const { isOnline, isInstallable, installApp } = usePwa();

  const [loggingOut, setLoggingOut] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const [notifs, setNotifs] = useState<InboxNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const loadNotifs = useCallback(async () => {
    try {
      // Authoritative unread count (not capped by the list page size) plus a
      // preview list for the dropdown.
      const [list, unread] = await Promise.all([listInbox(), getUnreadCount()]);
      setNotifs(list);
      setUnreadCount(unread);
    } catch {
      /* unauthenticated or offline — keep the bell quiet */
    }
  }, []);

  // Initial load; the background-task scheduler keeps the badge current
  // afterwards (foreground timer while open, Periodic Background Sync when away).
  useEffect(() => {
    loadNotifs();
  }, [loadNotifs]);
  useBackgroundRefresh("refresh-notifications", loadNotifs);

  // Handle Ctrl+K shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setIsPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  async function onLogout() {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      setLoggingOut(false);
    }
  }

  const markAllRead = async () => {
    setNotifs((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
    try {
      await apiMarkAllRead();
    } catch {
      loadNotifs();
    }
  };

  const openNotif = async (n: InboxNotification) => {
    if (!n.is_read) {
      setNotifs((prev) => prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)));
      setUnreadCount((c) => Math.max(0, c - 1));
      try {
        await markRead(n.recipient_id);
      } catch {
        /* best effort */
      }
    }
  };

  return (
    <header className="sticky top-0 z-40 h-[72px] flex items-center justify-between px-6 border-b border-[var(--border)] bg-[color-mix(in_srgb,var(--card)_88%,transparent)] backdrop-blur-md transition-colors duration-200">
      {/* Left: Collapse button and dynamic page title */}
      <div className="flex items-center gap-4">
        {/* Toggle Mobile Drawer Sidebar (only mobile/tablet) */}
        <button
          onClick={toggleMobileSidebar}
          className="lg:hidden flex items-center justify-center p-2 rounded-xl text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--background-secondary)] transition"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Toggle Desktop Sidebar (desktop only) */}
        <button
          onClick={toggleSidebar}
          className="hidden lg:flex items-center justify-center p-2 rounded-xl text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--background-secondary)] transition"
        >
          <Menu className="w-5 h-5" />
        </button>

        <h1 className="text-lg font-semibold text-[var(--foreground)] tracking-tight hidden sm:block">
          {title}
        </h1>
      </div>

      {/* Center: Large search input with keyboard shortcut tooltip */}
      <div className="flex-1 max-w-md mx-6 hidden md:block">
        <div
          onClick={() => setIsPaletteOpen(true)}
          className="flex items-center justify-between w-full px-3.5 py-2 text-sm border border-[var(--border)] rounded-xl bg-[var(--background-secondary)] hover:border-[var(--border-hover)] text-[var(--muted)] cursor-pointer transition select-none"
        >
          <div className="flex items-center gap-2.5">
            <Search className="w-4 h-4 text-[var(--muted)]" />
            <span>Search students, rooms, payments...</span>
          </div>
          <kbd className="flex items-center gap-0.5 px-1.5 py-0.5 border border-[var(--border)] rounded bg-[var(--card)] text-[10px] font-semibold text-[var(--muted)] shadow-sm">
            Ctrl+K
          </kbd>
        </div>
      </div>

      {/* Right: Quick actions, notifications, user settings */}
      <div className="flex items-center gap-3">
        {!isOnline && (
          <span className="px-2.5 py-1 rounded-full text-[9px] font-bold uppercase tracking-wider bg-red-500/10 text-red-500 border border-red-500/20 animate-pulse select-none">
            Offline
          </span>
        )}

        {isInstallable && (
          <button
            onClick={installApp}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white rounded-xl text-xs font-semibold shadow-sm transition"
          >
            <Download className="w-3.5 h-3.5 shrink-0" />
            <span className="hidden sm:inline">Install App</span>
          </button>
        )}

        {/* Search icon triggers CommandPalette on mobile */}
        <button
          onClick={() => setIsPaletteOpen(true)}
          className="md:hidden flex items-center justify-center p-2 rounded-xl text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--background-secondary)] transition"
        >
          <Search className="w-5 h-5" />
        </button>

        <div className="hidden sm:flex items-center rounded-xl border border-[var(--border)] bg-[var(--card)] p-1 shadow-sm">
          {[
            { value: "light", label: "Light", icon: Sun },
            { value: "dark", label: "Dark", icon: Moon },
            { value: "system", label: "System", icon: Monitor },
          ].map((item) => {
            const Icon = item.icon;
            const active = theme === item.value;
            return (
              <button
                key={item.value}
                type="button"
                onClick={() => setTheme(item.value as "light" | "dark" | "system")}
                className={`flex h-8 w-8 items-center justify-center rounded-lg transition ${
                  active
                    ? "bg-[var(--accent)] text-white"
                    : "text-[var(--muted)] hover:bg-[var(--background-secondary)] hover:text-[var(--foreground)]"
                }`}
                title={item.label}
                aria-label={`Use ${item.label} theme`}
              >
                <Icon className="h-4 w-4" />
              </button>
            );
          })}
        </div>

        <button
          onClick={() => setTheme(theme === "system" ? resolvedTheme === "dark" ? "light" : "dark" : "system")}
          className="sm:hidden flex items-center justify-center p-2 rounded-xl text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--background-secondary)] transition"
          aria-label="Change theme"
        >
          {theme === "system" ? <Monitor className="w-5 h-5" /> : theme === "light" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        {/* Notification bell and dropdown */}
        <div className="relative">
          <button
            onClick={() => setIsNotifOpen(!isNotifOpen)}
            className="flex items-center justify-center p-2 rounded-xl text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--background-secondary)] transition relative"
            aria-label="View Notifications"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold leading-none ring-2 ring-[var(--card)] tabular-nums">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </button>

          {isNotifOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setIsNotifOpen(false)} />
              <div className="absolute right-0 mt-2 w-80 bg-[var(--card-elevated)] border border-[var(--border)] rounded-3xl shadow-[var(--shadow-lg)] z-50 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
                  <h3 className="text-xs font-semibold text-[var(--foreground)] uppercase tracking-wide">Notifications</h3>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllRead}
                      className="text-[10px] font-semibold text-[var(--accent)] hover:underline"
                    >
                      Mark all read
                    </button>
                  )}
                </div>
                <div className="divide-y divide-[var(--border)] max-h-60 overflow-y-auto">
                  {notifs.length === 0 ? (
                    <div className="px-4 py-6 text-center text-xs text-[var(--muted)]">No notifications</div>
                  ) : (
                    notifs.slice(0, 8).map((n) => (
                      <div
                        key={n.id}
                        onClick={() => openNotif(n)}
                        className={`cursor-pointer px-4 py-3 text-xs leading-normal transition hover:bg-[var(--background-secondary)] ${
                          !n.is_read ? "bg-[var(--accent-soft)] font-medium" : "text-[var(--muted)]"
                        }`}
                      >
                        <p className="text-[var(--foreground)]">{n.title}</p>
                        {n.body ? <p className="mt-0.5 line-clamp-2 text-[var(--muted)]">{n.body}</p> : null}
                      </div>
                    ))
                  )}
                </div>
                <Link
                  href="/notifications"
                  onClick={() => setIsNotifOpen(false)}
                  className="block border-t border-[var(--border)] px-4 py-2.5 text-center text-[11px] font-semibold text-[var(--accent)] hover:bg-[var(--background-secondary)]"
                >
                  View all notifications
                </Link>
              </div>
            </>
          )}
        </div>

        {/* User avatar, role, and dropdown */}
        <div className="relative">
          <button
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            className="flex items-center gap-2 p-1 pl-2 border border-[var(--border)] hover:bg-[var(--background-secondary)] rounded-xl transition cursor-pointer"
          >
            <div className="flex items-center justify-center w-7 h-7 rounded-full bg-[var(--accent)] text-white font-bold text-xs select-none">
              {(role || "A").substring(0, 1).toUpperCase()}
            </div>
            <div className="text-left hidden lg:block pr-1 select-none">
              <div className="text-xs font-semibold text-[var(--foreground)] leading-tight">Admin Owner</div>
              <div className="text-[9px] text-[var(--muted)] font-semibold uppercase tracking-wider">
                {role || "OWNER"}
              </div>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-[var(--muted)] hidden lg:block shrink-0" />
          </button>

          {isProfileOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setIsProfileOpen(false)} />
              <div className="absolute right-0 mt-2 w-48 bg-[var(--card-elevated)] border border-[var(--border)] rounded-3xl shadow-[var(--shadow-lg)] z-50 overflow-hidden py-1.5">
                <div className="px-4 py-2 border-b border-[var(--border)] lg:hidden">
                  <div className="text-xs font-semibold text-[var(--foreground)]">Admin Owner</div>
                  <div className="text-[9px] text-[var(--muted)] font-bold uppercase tracking-wider">
                    {role || "OWNER"}
                  </div>
                </div>
                <button
                  onClick={() => setIsProfileOpen(false)}
                  className="w-full flex items-center gap-2.5 px-4 py-2 text-xs text-[var(--foreground-secondary)] hover:bg-[var(--background-secondary)] text-left transition"
                >
                  <User className="w-4 h-4 text-[var(--muted)]" />
                  <span>My Profile</span>
                </button>
                <button
                  onClick={() => setIsProfileOpen(false)}
                  className="w-full flex items-center gap-2.5 px-4 py-2 text-xs text-[var(--foreground-secondary)] hover:bg-[var(--background-secondary)] text-left transition"
                >
                  <Settings className="w-4 h-4 text-[var(--muted)]" />
                  <span>Settings</span>
                </button>
                <div className="h-px bg-[var(--border)] my-1" />
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

      {/* Global CommandPalette Dialog */}
      <CommandPalette isOpen={isPaletteOpen} onClose={() => setIsPaletteOpen(false)} />
    </header>
  );
}
