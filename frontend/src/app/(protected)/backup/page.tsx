"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { HostelPicker } from "@/features/backups/components/HostelPicker";
import { BackupCreateForm } from "@/features/backups/components/BackupCreateForm";
import { BackupRestoreForm } from "@/features/backups/components/BackupRestoreForm";
import { BackupList } from "@/features/backups/components/BackupList";
import { listBackups, downloadBackup, restoreBackup, createSnapshot } from "@/features/backups/api/backups.api";
import type { BackupSnapshot } from "@/features/backups/types/backups.types";
import { useToast } from "@/shared/ui/toast/ToastProvider";
import { useAuth } from "@/shared/auth/AuthProvider";

// --------------------
// Small UI helpers (SaaS-like)
// --------------------
function cn(...classes: Array<string | false | undefined | null>) {
  return classes.filter(Boolean).join(" ");
}

function TabLink({
  href,
  active,
  children,
}: {
  href: string;
  active?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex items-center rounded-full px-4 py-2 text-sm font-medium transition",
        active
          ? "bg-zinc-900 text-white shadow-sm"
          : "bg-white text-zinc-700 ring-1 ring-zinc-200 hover:bg-zinc-50"
      )}
    >
      {children}
    </Link>
  );
}

function Card({
  title,
  description,
  children,
  right,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  right?: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl bg-white shadow-sm ring-1 ring-zinc-200">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 p-5">
        <div>
          <h2 className="text-base font-semibold text-zinc-900">{title}</h2>
          {description ? <p className="mt-1 text-sm text-zinc-500">{description}</p> : null}
        </div>
        {right ? <div className="shrink-0">{right}</div> : null}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function Button({
  variant = "primary",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger";
}) {
  const styles =
    variant === "primary"
      ? "bg-zinc-900 text-white hover:bg-zinc-800"
      : variant === "danger"
      ? "bg-red-600 text-white hover:bg-red-500"
      : "bg-white text-zinc-800 ring-1 ring-zinc-200 hover:bg-zinc-50";

  return (
    <button
      {...props}
      className={cn(
        "inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition shadow-sm disabled:opacity-60 disabled:cursor-not-allowed",
        styles,
        className
      )}
    />
  );
}

function StatPill({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-2 rounded-xl bg-zinc-50 px-3 py-2 ring-1 ring-zinc-200">
      <span className="text-xs font-medium text-zinc-600">{label}</span>
      <span className="text-xs font-semibold text-zinc-900">{value}</span>
    </div>
  );
}

// --------------------
// Page
// --------------------
export default function BackupSettingsPage() {
  const toast = useToast();
  const { logout } = useAuth();
  const [hostelId, setHostelId] = useState<string | null>(null);

  const [items, setItems] = useState<BackupSnapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [quickMsg, setQuickMsg] = useState<string | null>(null);
  const [quickBusy, setQuickBusy] = useState(false);

  const stats = useMemo(() => {
    // NOTE: Your listBackups() returns only backups, not hostel stats.
    // This is a UI-only “status” area. Replace with real endpoint later.
    return {
      snapshots: items.length,
      manual: items.filter((x) => x.kind === "manual").length,
      scheduled: items.filter((x) => x.kind === "scheduled").length,
    };
  }, [items]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listBackups();
      setItems(data);
    } catch (e: any) {
      setError(e?.message || "Failed to load backups.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function exportLatestSnapshot() {
    // Professional SaaS behavior:
    // 1) Create snapshot (manual)
    // 2) Refresh list
    // 3) Download that snapshot
    if (!hostelId) {
      setQuickMsg("Please select a hostel first.");
      return;
    }
    setQuickBusy(true);
    setQuickMsg(null);
    try {
      const created = await createSnapshot(hostelId, "Manual export from settings page");
      await refresh();
      await downloadBackup(created.id);
      setQuickMsg("Backup exported successfully.");
    } catch (e: any) {
      setQuickMsg(e?.message || "Export failed.");
    } finally {
      setQuickBusy(false);
    }
  }

  async function importFromFile(file: File) {
    if (!hostelId) {
      setQuickMsg("Please select a hostel first.");
      return;
    }
    setQuickBusy(true);
    setQuickMsg(null);
    try {
      const text = await file.text();
      // basic check
      const t = text.trim();
      if (!t.startsWith("{") || !t.endsWith("}")) {
        throw new Error("This file does not look like valid JSON.");
      }
      // Safety confirmation:
      // You already have a full restore UI in BackupRestoreForm.
      // This import button will still restore immediately for convenience.
      // If you want, we can instead auto-fill the restore textarea.
      await restoreBackup(hostelId, text);
      await refresh();
      setQuickMsg("Backup imported and restored successfully.");
    } catch (e: any) {
      setQuickMsg(e?.message || "Import failed.");
    } finally {
      setQuickBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50">
      <div className="mx-auto w-full max-w-6xl px-4 py-8">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-zinc-900">Settings</h1>
            <p className="mt-1 text-sm text-zinc-500">
              Manage your hostel configuration and backups safely.
            </p>

            <div className="mt-4">
              <HostelPicker hostelId={hostelId} setHostelId={setHostelId} />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => toast.info("Help & documentation are coming soon.")}
            >
              Help
            </Button>
            <Button variant="secondary" onClick={() => void logout()}>
              Logout
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="mt-6 flex flex-wrap gap-2">
          <TabLink href="/dashboard">Dashboard</TabLink>
          <TabLink href="/settings/general">General</TabLink>
          <TabLink href="/settings/billing">Billing</TabLink>
          <TabLink href="/settings/users">Users</TabLink>
          <TabLink href="/settings/backups" active>
            Backups
          </TabLink>
        </div>

        {/* Top status + quick actions */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Card
              title="Backup center"
              description="Create snapshots, download backups, or restore safely when needed."
              right={
                <Button variant="secondary" onClick={refresh} disabled={loading}>
                  Refresh
                </Button>
              }
            >
              <div className="flex flex-wrap gap-2">
                <StatPill label="Total snapshots" value={stats.snapshots} />
                <StatPill label="Manual" value={stats.manual} />
                <StatPill label="Scheduled" value={stats.scheduled} />
              </div>

              <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-zinc-600">
                  {quickMsg ? <span className="text-zinc-800">{quickMsg}</span> : " "}
                </div>

                <div className="flex flex-col gap-2 sm:flex-row">
                  <Button onClick={exportLatestSnapshot} disabled={quickBusy || !hostelId}>
                    Export backup (JSON)
                  </Button>

                  <label className={cn(!hostelId && "opacity-60", "inline-flex")}>
                    <input
                      type="file"
                      accept="application/json"
                      className="hidden"
                      disabled={quickBusy || !hostelId}
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) importFromFile(f);
                        e.currentTarget.value = "";
                      }}
                    />
                    <span
                      className={cn(
                        "inline-flex cursor-pointer items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition shadow-sm",
                        "bg-white text-zinc-800 ring-1 ring-zinc-200 hover:bg-zinc-50",
                        (quickBusy || !hostelId) && "pointer-events-none"
                      )}
                    >
                      Import backup (JSON)
                    </span>
                  </label>
                </div>
              </div>

              <div className="mt-6">
                <BackupList items={items} loading={loading} error={error} onRefresh={refresh} />
              </div>
            </Card>
          </div>

          <div className="lg:col-span-1">
            <Card
              title="Safety notes"
              description="Good practices to keep your data safe."
            >
              <div className="space-y-3 text-sm text-zinc-700">
                <div className="rounded-xl bg-amber-50 p-4 ring-1 ring-amber-200">
                  <p className="font-semibold text-amber-900">Recommended</p>
                  <ul className="mt-2 list-disc pl-5 text-xs text-amber-900/80 space-y-1">
                    <li>Create a backup before month-end closing.</li>
                    <li>Backup before mass vacate / room changes.</li>
                    <li>Store JSON backups securely (don’t share publicly).</li>
                  </ul>
                </div>

                <div className="rounded-xl bg-zinc-50 p-4 ring-1 ring-zinc-200">
                  <p className="font-semibold text-zinc-900">Restore warning</p>
                  <p className="mt-1 text-xs text-zinc-600">
                    Restore wipes hostel-scoped data and replaces it with backup data. Always export first.
                  </p>
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* Advanced actions: create/restore UI */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card
            title="Create snapshot"
            description="Create a manual snapshot and store it in the system."
          >
            <BackupCreateForm hostelId={hostelId} onDone={refresh} />
          </Card>

          <Card
            title="Restore from JSON"
            description="Paste JSON backup to restore data. Use carefully."
          >
            <BackupRestoreForm hostelId={hostelId} onDone={refresh} />
          </Card>
        </div>

        <p className="mt-6 text-xs text-zinc-500">
          Backups contain sensitive data. Store exported files securely and avoid sharing them publicly.
        </p>
      </div>
    </div>
  );
}
