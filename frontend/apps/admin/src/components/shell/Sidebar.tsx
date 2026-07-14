"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSidebar } from "@/components/shell/SidebarContext";
import { usePwa } from "@hostel/pwa";
import { permissionForPath, usePermissions } from "@hostel/permissions";
import {
  AlertTriangle,
  BarChart3,
  Bot,
  Boxes,
  Building2,
  Calculator,
  CalendarDays,
  CheckSquare,
  ChevronLeft,
  CreditCard,
  Database,
  Download,
  FileText,
  Home,
  Key,
  LayoutDashboard,
  LogOut,
  Bell,
  Megaphone,
  Receipt,
  RefreshCw,
  ScrollText,
  Settings,
  ShieldPlus,
  User,
  UserCheck,
  UserCog,
  UserPlus,
  UserRound,
  Users,
  Wallet,
} from "lucide-react";

const MODULES = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "AI Assistant", href: "/ai", icon: Bot },
  { name: "Admissions", href: "/admissions", icon: UserPlus },
  { name: "Students", href: "/students", icon: Users },
  { name: "Residents", href: "/residents", icon: UserCheck },
  { name: "Rooms & Beds", href: "/rooms", icon: Home },
  { name: "Finance", href: "/finance", icon: Wallet },
  { name: "Accounting", href: "/accounting", icon: Calculator },
  { name: "Inventory", href: "/inventory", icon: Boxes },
  { name: "Fees", href: "/fees", icon: Receipt },
  { name: "Payments", href: "/payments", icon: CreditCard },
  { name: "Billing", href: "/billing", icon: FileText },
  { name: "Attendance", href: "/attendance", icon: CheckSquare },
  { name: "Gate", href: "/gate", icon: Key },
  { name: "Leave", href: "/leave", icon: CalendarDays },
  { name: "Visitors", href: "/visitors", icon: UserRound },
  { name: "Staff", href: "/staff", icon: UserCog },
  { name: "Complaints", href: "/complaints", icon: AlertTriangle },
  { name: "Notices", href: "/notices", icon: Megaphone },
  { name: "Notifications", href: "/notifications", icon: Bell },
  { name: "Sync", href: "/sync", icon: RefreshCw },
  { name: "Vacate", href: "/vacate", icon: LogOut },
  { name: "Reports", href: "/reports", icon: BarChart3 },
  { name: "Exports", href: "/exports", icon: Download },
  { name: "Audit", href: "/audit", icon: ScrollText },
  { name: "Settings", href: "/settings", icon: Settings },
  { name: "Profile", href: "/profile", icon: User },
  { name: "Backup", href: "/backup", icon: Database },
  // Super-admin only: the route policy gates /platform on `platform:manage`,
  // which only SUPER_ADMIN holds, so this entry is hidden for everyone else.
  { name: "Platform", href: "/platform", icon: ShieldPlus },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { isCollapsed, toggleSidebar, isMobileOpen, setIsMobileOpen } = useSidebar();
  const { isInstallable, installApp } = usePwa();
  const { can } = usePermissions();
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  // The route policy is the single source of truth: a module shows up only
  // when the user's role holds the permission its route requires.
  const modules = MODULES.filter((item) => {
    const required = permissionForPath(item.href);
    return !required || can(required);
  });

  const sidebarWidth = isCollapsed ? 72 : 260;

  const handleLinkClick = () => {
    if (isMobileOpen) setIsMobileOpen(false);
  };

  const content = (
    <div className="flex h-full flex-col border-r border-[var(--border)] bg-[var(--card)] transition-colors duration-200 dark:bg-[#020617]">
      <div className="flex h-[72px] shrink-0 items-center justify-between border-b border-[var(--border)] px-5">
        <Link href="/dashboard" className="flex items-center gap-3 overflow-hidden select-none" onClick={handleLinkClick}>
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
            <Building2 className="h-5 w-5" />
          </div>
          {!isCollapsed && (
            <div className="anim-fade-in flex min-w-0 flex-col">
              <span className="text-sm font-semibold leading-tight text-[var(--foreground)]">Hostel</span>
              <span className="truncate text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">Management</span>
            </div>
          )}
        </Link>

        {!isCollapsed && (
          <button
            onClick={toggleSidebar}
            className="hidden h-6 w-6 shrink-0 items-center justify-center rounded-md text-[var(--muted)] transition hover:bg-[var(--background-secondary)] hover:text-[var(--foreground)] lg:flex"
            aria-label="Collapse sidebar"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="scrollbar-thin flex-1 space-y-1.5 overflow-y-auto px-3 py-4">
        {modules.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
          const Icon = item.icon;

          return (
            <div
              key={item.name}
              className="relative"
              onMouseEnter={() => setHoveredItem(item.name)}
              onMouseLeave={() => setHoveredItem(null)}
            >
              <Link
                href={item.href}
                onClick={handleLinkClick}
                // 23 always-in-viewport links would otherwise each prefetch their
                // route on every page load — wasteful on mobile/low-end devices.
                // Defer to hover/touch prefetch instead.
                prefetch={false}
                className={`relative flex select-none items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-[var(--accent)] text-white shadow-sm"
                    : "text-[var(--foreground-secondary)] hover:bg-[var(--background-secondary)] hover:text-[var(--foreground)]"
                }`}
              >
                <Icon className={`h-5 w-5 shrink-0 transition-transform duration-200 ${isActive ? "text-white" : "text-[var(--muted)]"}`} />
                {!isCollapsed && <span className="anim-fade-in truncate">{item.name}</span>}
              </Link>

              {isCollapsed && hoveredItem === item.name && (
                <div className="pointer-events-none absolute left-full top-1/2 z-50 ml-3 -translate-y-1/2 whitespace-nowrap rounded-lg border border-[var(--border)] bg-[var(--card-elevated)] px-2.5 py-1.5 text-[11px] font-semibold text-[var(--foreground)] shadow-[var(--shadow-lg)] select-none">
                  {item.name}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {isInstallable && (
        <div className="shrink-0 border-t border-[var(--border)] p-3">
          <button
            onClick={installApp}
            className={`flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--accent)] px-3 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-[var(--accent-hover)] ${
              isCollapsed ? "h-10 w-10 p-0" : ""
            }`}
            title="Install App"
          >
            <Download className="h-4 w-4 shrink-0" />
            {!isCollapsed && <span>Install App</span>}
          </button>
        </div>
      )}
    </div>
  );

  return (
    <>
      <aside
        className="sticky top-0 z-30 hidden h-screen shrink-0 transition-all duration-300 ease-in-out lg:block"
        style={{ width: `${sidebarWidth}px` }}
      >
        {content}
      </aside>

      {isMobileOpen && (
        <>
          <div
            onClick={() => setIsMobileOpen(false)}
            className="anim-fade-in fixed inset-0 z-40 bg-black/40 lg:hidden"
          />
          <div className="anim-slide-in-left fixed bottom-0 left-0 top-0 z-50 w-[260px] shadow-[var(--shadow-lg)] lg:hidden">
            {content}
          </div>
        </>
      )}
    </>
  );
}
