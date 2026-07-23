"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { permissionForPath, usePermissions } from "@hostel/permissions";
import { AlertCircle, BookOpen, Bot, Boxes, Calendar, Clipboard, Compass, DollarSign, LayoutDashboard, Package, Search, Settings, Truck, Users, X } from "lucide-react";

type CommandItem = {
  name: string;
  category: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
};

const COMMANDS: CommandItem[] = [
  { name: "Dashboard Overview", category: "Navigation", href: "/dashboard", icon: Compass },
  { name: "AI Assistant", category: "AI", href: "/ai", icon: Bot },
  { name: "AI Knowledge Base", category: "AI", href: "/ai/knowledge", icon: BookOpen },
  { name: "AI Dashboard", category: "AI", href: "/ai/dashboard", icon: LayoutDashboard },
  { name: "Admissions Queue", category: "Navigation", href: "/admissions", icon: BookOpen },
  { name: "Student Directory", category: "Navigation", href: "/students", icon: Users },
  { name: "Active Residents", category: "Navigation", href: "/residents", icon: Users },
  { name: "Rooms & Beds", category: "Navigation", href: "/rooms", icon: Compass },
  { name: "Fees Structure", category: "Finance", href: "/fees", icon: DollarSign },
  { name: "Payments Ledger", category: "Finance", href: "/payments", icon: DollarSign },
  { name: "Billing Invoices", category: "Finance", href: "/billing", icon: DollarSign },
  { name: "Inventory Overview", category: "Inventory", href: "/inventory", icon: Boxes },
  { name: "Inventory Items", category: "Inventory", href: "/inventory/items", icon: Package },
  { name: "Purchase Orders", category: "Inventory", href: "/inventory/purchase-orders", icon: Clipboard },
  { name: "Vendors", category: "Inventory", href: "/inventory/vendors", icon: Truck },
  { name: "Asset Register", category: "Inventory", href: "/inventory/assets", icon: Boxes },
  { name: "Attendance Log", category: "Operations", href: "/attendance", icon: Calendar },
  { name: "Gate Register", category: "Operations", href: "/gate", icon: Clipboard },
  { name: "Leave Requests", category: "Operations", href: "/leave", icon: Calendar },
  { name: "Visitors Log", category: "Operations", href: "/visitors", icon: Users },
  { name: "Complaints Portal", category: "Operations", href: "/complaints", icon: AlertCircle },
  { name: "Notices & Announcements", category: "Operations", href: "/notices", icon: Clipboard },
  { name: "Settings Home", category: "System", href: "/settings", icon: Settings },
  { name: "General Settings", category: "Settings", href: "/settings/general", icon: Settings },
  { name: "Appearance & Theme", category: "Settings", href: "/settings/appearance", icon: Settings },
  { name: "Users & Staff", category: "Settings", href: "/settings/users", icon: Users },
  { name: "Roles & Permissions", category: "Settings", href: "/settings/roles", icon: Settings },
  { name: "Security Settings", category: "Settings", href: "/settings/security", icon: Settings },
  { name: "Notification Settings", category: "Settings", href: "/settings/notifications", icon: AlertCircle },
  { name: "Plan & Billing", category: "Settings", href: "/settings/billing", icon: DollarSign },
  { name: "Audit Logs", category: "Settings", href: "/settings/audit", icon: Clipboard },
  { name: "System & Health", category: "Settings", href: "/settings/system", icon: Settings },
  { name: "My Profile", category: "System", href: "/profile", icon: Settings },
  { name: "Backup & Restore", category: "System", href: "/backup", icon: Settings },
];

export function CommandPalette({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    setQuery("");
    setSelectedIndex(0);
    setTimeout(() => inputRef.current?.focus(), 50);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) return;
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [isOpen, onClose]);

  const { can } = usePermissions();
  // Hide destinations the current role cannot open (same policy as routes/nav).
  const allowedCommands = COMMANDS.filter((cmd) => {
    const required = permissionForPath(cmd.href);
    return !required || can(required);
  });
  const filteredCommands = allowedCommands.filter(
    (cmd) =>
      cmd.name.toLowerCase().includes(query.toLowerCase()) ||
      cmd.category.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredCommands.length));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredCommands.length) % Math.max(1, filteredCommands.length));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filteredCommands[selectedIndex]) {
        router.push(filteredCommands[selectedIndex].href);
        onClose();
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/45 px-4 pt-[15vh] backdrop-blur-sm transition-opacity">
      <div
        ref={containerRef}
        className="w-full max-w-xl overflow-hidden rounded-3xl border border-[var(--border)] bg-[color-mix(in_srgb,var(--card-elevated)_92%,transparent)] shadow-[var(--shadow-lg)] transition-all"
        onKeyDown={handleKeyDown}
      >
        <div className="flex items-center gap-3 border-b border-[var(--border)] px-4">
          <Search className="h-5 w-5 shrink-0 text-[var(--muted)]" />
          <input
            ref={inputRef}
            type="text"
            className="w-full border-0 bg-transparent py-4 text-sm text-[var(--foreground)] outline-none placeholder:text-[var(--muted)] focus:ring-0"
            placeholder="Type a command or search modules..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
          />
          <button
            onClick={onClose}
            className="rounded-md p-1 text-[var(--muted)] transition hover:bg-[var(--background-secondary)] hover:text-[var(--foreground)]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="max-h-[300px] overflow-y-auto p-2">
          {filteredCommands.length === 0 ? (
            <div className="py-8 text-center text-sm text-[var(--muted)]">
              No results found for &ldquo;{query}&rdquo;
            </div>
          ) : (
            filteredCommands.map((cmd, idx) => {
              const Icon = cmd.icon;
              const isSelected = idx === selectedIndex;
              return (
                <button
                  key={cmd.name}
                  className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left transition ${
                    isSelected
                      ? "bg-[var(--accent)] text-white"
                      : "text-[var(--foreground-secondary)] hover:bg-[var(--background-secondary)]"
                  }`}
                  onClick={() => {
                    router.push(cmd.href);
                    onClose();
                  }}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`h-4 w-4 ${isSelected ? "text-white" : "text-[var(--muted)]"}`} />
                    <span className="text-sm font-medium">{cmd.name}</span>
                  </div>
                  <span className={`text-xs ${isSelected ? "text-blue-100" : "text-[var(--muted)]"}`}>
                    {cmd.category}
                  </span>
                </button>
              );
            })
          )}
        </div>

        <div className="flex items-center justify-between border-t border-[var(--border)] bg-[var(--background-secondary)] px-4 py-2.5 text-[10px] font-medium text-[var(--muted)]">
          <div className="flex items-center gap-2">
            <span>Up/Down Navigate</span>
            <span>&bull;</span>
            <span>Enter Select</span>
            <span>&bull;</span>
            <span>Esc Close</span>
          </div>
          <div>
            Keyboard Shortcut:{" "}
            <kbd className="rounded border border-[var(--border)] bg-[var(--card)] px-1 text-[9px] shadow-sm">
              Ctrl+K
            </kbd>
          </div>
        </div>
      </div>
    </div>
  );
}
