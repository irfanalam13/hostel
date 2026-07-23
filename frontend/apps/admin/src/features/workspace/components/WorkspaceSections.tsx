"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useToast } from "@hostel/ui";
import { WorkspaceUsernameField } from "@/features/tenants/components/WorkspaceUsernameField";
import type { AvailabilityState } from "@/features/tenants/hooks/useWorkspaceAvailability";
import {
  workspaceApi,
  type ActivityEntry,
  type TeamMember,
  type WorkspaceOverview,
} from "../api/workspace.api";
import { NamespaceForm } from "./NamespaceForm";

const card = "rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5";
const btn = "rounded-lg px-3 py-2 text-xs font-semibold transition disabled:opacity-50 ";
const btnPrimary = btn + "bg-[var(--accent)] text-white hover:opacity-90";
const btnGhost = btn + "border border-[var(--border)] text-[var(--foreground)] hover:border-[var(--accent)]";
const btnDanger = btn + "border border-red-400/60 text-red-500 hover:bg-red-500/10";
const inputCls =
  "w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm " +
  "text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]";

function formatBytes(bytes: number): string {
  if (!bytes) return "0 MB";
  const mb = bytes / (1024 * 1024);
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(1)} MB`;
}

/* ---------------------------------------------------------------- Overview */
export function WorkspaceOverviewSection() {
  const toast = useToast();
  const [data, setData] = useState<WorkspaceOverview | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    workspaceApi.overview().then(setData).catch((e) =>
      setError(e instanceof Error ? e.message : "Could not load the overview."));
  }, []);

  if (error) return <div className={card}><p className="text-sm text-red-500">{error}</p></div>;
  if (!data) return <div className={card}><p className="text-sm text-[var(--muted)]">Loading…</p></div>;

  const w = data.workspace;
  const rows: [string, React.ReactNode][] = [
    ["Workspace name", w.name],
    ["Workspace username", <span key="u" className="font-mono">{w.slug}</span>],
    ["Hostel ID", <span key="c" className="font-mono">{w.code}</span>],
    ["Status", w.status],
    ["Owner", data.owner || "—"],
    ["Plan", data.subscription.plan || "—"],
    ["Trial days left", data.subscription.trial_days_left ?? "—"],
    ["Storage used", formatBytes(data.storage_bytes)],
    ["Last member login", data.last_login ? new Date(data.last_login).toLocaleString() : "—"],
    ["Created", new Date(w.created_at).toLocaleDateString()],
  ];
  const counts: [string, number][] = [
    ["Members", data.counts.members],
    ["Staff", data.counts.staff],
    ["Students", data.counts.students],
    ["Parents", data.counts.parents],
    ["Residents", data.counts.residents],
    ["Active (30d)", data.counts.active_users_30d],
  ];

  return (
    <div className="space-y-4">
      <div className={`${card} flex flex-wrap items-center justify-between gap-3`}>
        <div>
          <div className="text-lg font-bold text-[var(--foreground)]">{w.name}</div>
          <a href={w.workspace_url} target="_blank" rel="noopener noreferrer"
             className="font-mono text-xs text-[var(--accent)] hover:underline">
            {w.workspace_url}
          </a>
        </div>
        <div className="flex flex-wrap gap-2">
          <a href={w.workspace_url} target="_blank" rel="noopener noreferrer" className={btnGhost}>
            Open public website ↗
          </a>
          <button
            className={btnGhost}
            onClick={() => {
              void navigator.clipboard?.writeText(w.workspace_url).then(
                () => toast.success("Workspace URL copied."));
            }}
          >
            Copy URL
          </button>
          <Link href="/settings/website" className={btnGhost}>Website builder</Link>
          <Link href="/settings/branding" className={btnGhost}>Branding</Link>
          <Link href="/settings/billing" className={btnGhost}>Subscription</Link>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className={card}>
          <h3 className="mb-3 text-sm font-bold text-[var(--foreground)]">Workspace</h3>
          <dl className="space-y-2">
            {rows.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3 text-sm">
                <dt className="text-[var(--muted)]">{k}</dt>
                <dd className="text-right font-medium text-[var(--foreground)]">{v}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div className={card}>
          <h3 className="mb-3 text-sm font-bold text-[var(--foreground)]">People & activity</h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {counts.map(([k, v]) => (
              <div key={k} className="rounded-xl border border-[var(--border)] p-3 text-center">
                <div className="text-xl font-extrabold text-[var(--foreground)]">{v}</div>
                <div className="text-xs text-[var(--muted)]">{k}</div>
              </div>
            ))}
          </div>
          <div className="mt-3 text-sm text-[var(--muted)]">
            Website inquiries: <span className="font-semibold text-[var(--foreground)]">{data.inquiries}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ Workspace URL */
export function WorkspaceUrlSection() {
  const toast = useToast();
  const [overview, setOverview] = useState<WorkspaceOverview | null>(null);
  const [renaming, setRenaming] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [availability, setAvailability] = useState<AvailabilityState | null>(null);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    workspaceApi.overview().then(setOverview).catch(() => setOverview(null));
  }, []);

  async function submitRename() {
    if (busy) return;
    if (!newUsername) return toast.warning("Enter the new workspace username.");
    if (availability?.status === "taken" || availability?.status === "invalid") {
      return toast.warning("Pick an available, valid workspace username first.");
    }
    if (!password) return toast.warning("Enter your account password to confirm.");
    setBusy(true);
    try {
      const res = await workspaceApi.rename(newUsername, password);
      toast.success(res.detail, "Workspace renamed");
      setRenaming(false);
      setPassword("");
      setNewUsername("");
      const fresh = await workspaceApi.overview();
      setOverview(fresh);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Rename failed", "Error");
    } finally {
      setBusy(false);
    }
  }

  if (!overview) return <div className={card}><p className="text-sm text-[var(--muted)]">Loading…</p></div>;
  const w = overview.workspace;

  return (
    <div className="space-y-4">
      <div className={card}>
        <h3 className="text-sm font-bold text-[var(--foreground)]">Workspace username & URL</h3>
        <p className="mt-0.5 text-xs text-[var(--muted)]">
          The workspace username is your permanent tenant identifier — it doubles as your web address.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <div className="rounded-xl border border-[var(--border)] px-4 py-3">
            <div className="text-xs text-[var(--muted)]">Workspace username</div>
            <div className="font-mono text-lg font-bold text-[var(--foreground)]">{w.slug}</div>
          </div>
          <div className="rounded-xl border border-[var(--border)] px-4 py-3">
            <div className="text-xs text-[var(--muted)]">Workspace URL</div>
            <a href={w.workspace_url} target="_blank" rel="noopener noreferrer"
               className="font-mono text-sm font-semibold text-[var(--accent)] hover:underline">
              {w.workspace_url}
            </a>
          </div>
          <button
            className={btnGhost}
            onClick={() => {
              void navigator.clipboard?.writeText(w.workspace_url).then(
                () => toast.success("Workspace URL copied."));
            }}
          >
            Copy URL
          </button>
        </div>
      </div>

      <div className={card}>
        <h3 className="text-sm font-bold text-[var(--foreground)]">Change workspace username</h3>
        <p className="mt-0.5 text-xs text-[var(--muted)]">
          Owner-only. Your old URL will permanently redirect (301) to the new one, and the old
          username stays reserved for this workspace — no one else can ever claim it.
        </p>
        {!renaming ? (
          <button className={`mt-3 ${btnGhost}`} onClick={() => setRenaming(true)}>
            Change username…
          </button>
        ) : (
          <div className="mt-4 max-w-md space-y-3">
            <WorkspaceUsernameField
              value={newUsername}
              onChange={setNewUsername}
              onStateChange={setAvailability}
              disabled={busy}
            />
            <div>
              <div className="mb-1 text-xs font-medium text-[var(--muted)]">
                Confirm with your account password
              </div>
              <input type="password" className={inputCls} value={password}
                     onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            </div>
            <div className="flex gap-2">
              <button className={btnPrimary} onClick={() => void submitRename()} disabled={busy}>
                {busy ? "Renaming…" : "Rename workspace"}
              </button>
              <button className={btnGhost} onClick={() => setRenaming(false)} disabled={busy}>
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------- Team */
const ROLE_OPTIONS = [
  "ADMIN", "MANAGER", "RECEPTIONIST", "ACCOUNTANT", "WARDEN", "STAFF",
  "READ_ONLY", "STUDENT", "PARENT",
];

export function TeamSection() {
  const toast = useToast();
  const [members, setMembers] = useState<TeamMember[] | null>(null);
  const [invite, setInvite] = useState({ username: "", email: "", role: "STAFF" });
  const [tempPassword, setTempPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setMembers(await workspaceApi.team());
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the team.");
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function submitInvite() {
    if (busy || !invite.username.trim()) return;
    setBusy(true);
    try {
      const res = await workspaceApi.invite({
        username: invite.username.trim(),
        email: invite.email.trim() || undefined,
        role: invite.role,
      });
      setTempPassword(res.temporary_password);
      setInvite({ username: "", email: "", role: "STAFF" });
      toast.success(`${res.username} invited as ${res.role}.`, "Team member added");
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Invite failed", "Error");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <div className={card}><p className="text-sm text-red-500">{error}</p></div>;
  if (!members) return <div className={card}><p className="text-sm text-[var(--muted)]">Loading…</p></div>;

  return (
    <div className="space-y-4">
      <div className={card}>
        <h3 className="mb-3 text-sm font-bold text-[var(--foreground)]">Invite a team member</h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <input className={inputCls} placeholder="Username *" value={invite.username}
                 onChange={(e) => setInvite({ ...invite, username: e.target.value })} />
          <input className={inputCls} placeholder="Email (credentials are sent here)" value={invite.email}
                 onChange={(e) => setInvite({ ...invite, email: e.target.value })} />
          <select className={inputCls} value={invite.role}
                  onChange={(e) => setInvite({ ...invite, role: e.target.value })}>
            {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <button className={`mt-3 ${btnPrimary}`} onClick={() => void submitInvite()} disabled={busy}>
          {busy ? "Inviting…" : "Invite member"}
        </button>
        {tempPassword && (
          <div className="mt-3 rounded-xl border border-amber-400/40 bg-amber-500/10 p-3 text-sm">
            <span className="text-[var(--muted)]">One-time temporary password (share it securely): </span>
            <span className="font-mono font-bold text-[var(--foreground)]">{tempPassword}</span>
          </div>
        )}
      </div>

      <div className={card}>
        <h3 className="mb-3 text-sm font-bold text-[var(--foreground)]">Team ({members.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wide text-[var(--muted)]">
                <th className="py-2 pr-3">Member</th>
                <th className="py-2 pr-3">Role</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2 pr-3">Last active</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {members.map((m) => (
                <tr key={m.user_id}>
                  <td className="py-2 pr-3">
                    <div className="font-medium text-[var(--foreground)]">
                      {m.name || m.username}
                      {m.is_owner && (
                        <span className="ml-2 rounded-full bg-[var(--accent)]/15 px-2 py-0.5 text-[10px] font-bold text-[var(--accent)]">
                          OWNER
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-[var(--muted)]">{m.email || m.username}</div>
                  </td>
                  <td className="py-2 pr-3">
                    {m.is_owner ? (
                      <span className="text-[var(--foreground)]">{m.role}</span>
                    ) : (
                      <select
                        className={inputCls + " max-w-[150px]"}
                        value={m.role}
                        onChange={(e) => {
                          void workspaceApi.changeRole(m.user_id, e.target.value)
                            .then(() => { toast.success("Role updated."); return load(); })
                            .catch((err) => toast.error(
                              err instanceof Error ? err.message : "Could not change role", "Error"));
                        }}
                      >
                        {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
                      </select>
                    )}
                  </td>
                  <td className="py-2 pr-3">
                    <span className={m.is_active ? "text-green-500" : "text-[var(--muted)]"}>
                      {m.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-xs text-[var(--muted)]">
                    {m.last_login ? new Date(m.last_login).toLocaleString() : "Never"}
                  </td>
                  <td className="py-2">
                    {!m.is_owner && (
                      <button
                        className={btnDanger}
                        onClick={() => {
                          void workspaceApi.removeMember(m.user_id)
                            .then(() => { toast.success("Member removed."); return load(); })
                            .catch((err) => toast.error(
                              err instanceof Error ? err.message : "Could not remove", "Error"));
                        }}
                      >
                        Remove
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* --------------------------------------------------------------- Activity */
export function WorkspaceActivitySection() {
  const [entries, setEntries] = useState<ActivityEntry[] | null>(null);
  const [query, setQuery] = useState("");

  const load = useCallback(async (q: string) => {
    try {
      setEntries(await workspaceApi.activity(q ? { q } : undefined));
    } catch {
      setEntries([]);
    }
  }, []);
  useEffect(() => { void load(""); }, [load]);

  return (
    <div className={card}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-bold text-[var(--foreground)]">Workspace activity</h3>
        <div className="flex gap-2">
          <input className={inputCls + " max-w-[220px]"} placeholder="Search activity…"
                 value={query} onChange={(e) => setQuery(e.target.value)}
                 onKeyDown={(e) => { if (e.key === "Enter") void load(query); }} />
          <button className={btnGhost} onClick={() => void load(query)}>Search</button>
        </div>
      </div>
      {!entries ? (
        <p className="text-sm text-[var(--muted)]">Loading…</p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">No activity recorded yet.</p>
      ) : (
        <ul className="divide-y divide-[var(--border)]">
          {entries.map((e) => (
            <li key={e.id} className="py-2.5 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-[var(--foreground)]">{e.message || e.action}</span>
                <span className="text-xs text-[var(--muted)]">
                  {new Date(e.created_at).toLocaleString()}
                </span>
              </div>
              <div className="text-xs text-[var(--muted)]">
                {[e.actor, e.action, e.ip_address].filter(Boolean).join(" · ")}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ------------------------------------------------------------- Danger zone */
export function DangerZoneSection() {
  const toast = useToast();
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const actions: { key: string; label: string; description: string }[] = [
    { key: "reset_branding", label: "Reset workspace branding",
      description: "Clears logos, backgrounds and banners back to defaults." },
    { key: "reset_theme", label: "Reset website theme",
      description: "Restores the public website's default colors (publish to apply)." },
    { key: "disable_website", label: "Disable public website",
      description: "Unpublishes the public site — visitors see it as offline." },
    { key: "archive", label: "Archive workspace",
      description: "Takes the entire workspace offline. Restorable by support." },
    { key: "request_deletion", label: "Request workspace deletion",
      description: "Soft-deletes the workspace. Data is preserved and recoverable." },
  ];

  async function run(action: string) {
    if (busy) return;
    if (!password) return toast.warning("Enter your account password first.");
    if (!window.confirm("Are you sure? This is a protected administrative action.")) return;
    setBusy(action);
    try {
      const res = await workspaceApi.danger(action, password);
      toast.success(res.detail, "Done");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Action failed", "Error");
    } finally {
      setBusy(null);
    }
  }

  async function exportSettings() {
    try {
      const data = await workspaceApi.exportSettings();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `workspace-settings-${data.workspace_username}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Export failed", "Error");
    }
  }

  return (
    <div className="space-y-4">
      <div className={card}>
        <h3 className="text-sm font-bold text-[var(--foreground)]">Export / import settings</h3>
        <p className="mt-0.5 text-xs text-[var(--muted)]">
          Download every workspace-settings namespace as JSON, or re-apply an exported file
          (import happens below with password confirmation via the API).
        </p>
        <button className={`mt-3 ${btnGhost}`} onClick={() => void exportSettings()}>
          Export settings (JSON)
        </button>
      </div>

      <div className={`${card} border-red-400/40`}>
        <h3 className="text-sm font-bold text-red-500">Danger zone</h3>
        <p className="mt-0.5 text-xs text-[var(--muted)]">
          Owner-only. Every action requires your account password and is recorded in the audit log.
          Nothing here permanently deletes tenant data.
        </p>
        <div className="mt-3 max-w-sm">
          <input type="password" className={inputCls} placeholder="Your account password"
                 value={password} onChange={(e) => setPassword(e.target.value)}
                 autoComplete="current-password" />
        </div>
        <ul className="mt-4 divide-y divide-[var(--border)]">
          {actions.map((a) => (
            <li key={a.key} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div>
                <div className="text-sm font-semibold text-[var(--foreground)]">{a.label}</div>
                <div className="text-xs text-[var(--muted)]">{a.description}</div>
              </div>
              <button className={btnDanger} disabled={busy !== null}
                      onClick={() => void run(a.key)}>
                {busy === a.key ? "Working…" : a.label}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ------------------------------------------ Namespace wrappers (thin) */
export function WorkspaceProfileSection() {
  return (
    <div className="space-y-4">
      <NamespaceForm namespace="profile" title="Workspace profile"
                     description="Public-facing identity: legal name, contacts and social links. Changing these never touches your workspace username or URL." />
      <NamespaceForm namespace="business" title="Business information"
                     description="Legal and registration details used on documents and (later) invoices." />
      <NamespaceForm namespace="regional" title="Regional settings"
                     description="Timezone, currency, language and formats applied across the workspace." />
    </div>
  );
}

export function WorkspaceBrandingSection() {
  return (
    <NamespaceForm namespace="branding" title="Workspace branding"
                   description="Logos, favicon and backgrounds. Applied automatically to login pages and portals; the public website's branding lives in the Website Builder." />
  );
}

export function WorkspaceNotificationsSection() {
  return (
    <NamespaceForm namespace="notifications" title="Notification settings"
                   description="Channels and per-module notification toggles. Email works today; SMS, push and WhatsApp are future-ready." />
  );
}

export function WorkspaceSecuritySection() {
  return (
    <NamespaceForm namespace="security" title="Security policy"
                   description="Workspace security preferences — password policy, session limits, login alerts and MFA preparation." />
  );
}

export function WorkspacePreferencesSection() {
  return (
    <NamespaceForm namespace="preferences" title="Workspace preferences"
                   description="Operational toggles. Public-website, gallery, events, notices and inquiry switches apply to your public site immediately." />
  );
}
