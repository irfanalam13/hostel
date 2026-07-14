"use client";

import React from "react";
import {
  Button,
  DataTable,
  Input,
  Modal,
  Select,
  Textarea,
  useToast,
  type Column,
} from "@hostel/ui";
import { useApi } from "@hostel/hooks";

import { opsGovApi } from "../api/opsgov.api";
import type {
  Announcement,
  FeatureFlag,
  Incident,
  MaintenanceWindow,
} from "../types/opsgov.types";
import { OverridesManager } from "./OverridesManager";

type Tab = "announcements" | "maintenance" | "incidents" | "flags";

const TABS: { key: Tab; label: string }[] = [
  { key: "announcements", label: "Announcements" },
  { key: "maintenance", label: "Maintenance" },
  { key: "incidents", label: "Incidents" },
  { key: "flags", label: "Feature flags" },
];

export function OpsGovConsole() {
  const [tab, setTab] = React.useState<Tab>("announcements");
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-1 border-b border-[var(--border)]">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition ${
              tab === t.key
                ? "border-[var(--accent)] text-[var(--foreground)]"
                : "border-transparent text-[var(--foreground-secondary)] hover:text-[var(--foreground)]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "announcements" && <AnnouncementsPanel />}
      {tab === "maintenance" && <MaintenancePanel />}
      {tab === "incidents" && <IncidentsPanel />}
      {tab === "flags" && <FeatureFlagsPanel />}
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Announcements
// --------------------------------------------------------------------------- //

function AnnouncementsPanel() {
  const toast = useToast();
  const { data, loading, refetch } = useApi(() => opsGovApi.announcements.list());
  const [editing, setEditing] = React.useState<Partial<Announcement> | null>(null);

  const save = async () => {
    if (!editing?.title) return toast.error("Title is required.");
    try {
      if (editing.id) await opsGovApi.announcements.update(editing.id, editing);
      else await opsGovApi.announcements.create(editing);
      toast.success("Saved.");
      setEditing(null);
      refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Save failed.");
    }
  };

  const remove = async (id: string) => {
    try {
      await opsGovApi.announcements.remove(id);
      refetch();
    } catch {
      toast.error("Delete failed.");
    }
  };

  const columns: Column<Announcement>[] = [
    { key: "title", header: "Title", sortable: true },
    { key: "level", header: "Level", sortable: true },
    { key: "audience", header: "Audience" },
    { key: "live", header: "Live", render: (r) => (r.live ? "● live" : "—") },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (r) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="ghost" onClick={() => setEditing(r)}>
            Edit
          </Button>
          <Button size="sm" variant="danger" onClick={() => remove(r.id)}>
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-3">
      <PanelHeader
        title="System announcements"
        onNew={() => setEditing({ level: "info", audience: "all", is_active: true, dismissible: true })}
      />
      <DataTable columns={columns} rows={data ?? []} rowKey={(r) => r.id} loading={loading} searchable />

      <Modal open={!!editing} title={editing?.id ? "Edit announcement" : "New announcement"} onClose={() => setEditing(null)}>
        {editing && (
          <div className="space-y-3">
            <Input label="Title" value={editing.title ?? ""} onChange={(e) => setEditing({ ...editing, title: e.target.value })} />
            <Textarea label="Body" value={editing.body ?? ""} onChange={(e) => setEditing({ ...editing, body: e.target.value })} />
            <div className="grid grid-cols-2 gap-3">
              <Select label="Level" value={editing.level ?? "info"} onChange={(e) => setEditing({ ...editing, level: e.target.value as Announcement["level"] })}
                options={[{ value: "info", label: "Info" }, { value: "warning", label: "Warning" }, { value: "critical", label: "Critical" }]} />
              <Select label="Audience" value={editing.audience ?? "all"} onChange={(e) => setEditing({ ...editing, audience: e.target.value as Announcement["audience"] })}
                options={[{ value: "all", label: "Everyone" }, { value: "staff", label: "Staff & admins" }, { value: "admins", label: "Admins only" }]} />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={!!editing.is_active} onChange={(e) => setEditing({ ...editing, is_active: e.target.checked })} />
              Active
            </label>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setEditing(null)}>Cancel</Button>
              <Button onClick={save}>Save</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Maintenance
// --------------------------------------------------------------------------- //

function MaintenancePanel() {
  const toast = useToast();
  const { data, loading, refetch } = useApi(() => opsGovApi.maintenance.list());
  const [editing, setEditing] = React.useState<Partial<MaintenanceWindow> | null>(null);

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      toast.success(ok);
      refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Action failed.");
    }
  };

  const save = () => {
    if (!editing?.title || !editing.scheduled_start || !editing.scheduled_end)
      return toast.error("Title, start and end are required.");
    return act(() => opsGovApi.maintenance.create(editing), "Scheduled.").then(() => setEditing(null));
  };

  const columns: Column<MaintenanceWindow>[] = [
    { key: "title", header: "Title", sortable: true },
    { key: "status", header: "Status", sortable: true },
    { key: "scheduled_start", header: "Start", sortable: true, render: (r) => new Date(r.scheduled_start).toLocaleString() },
    { key: "enforce_read_only", header: "Read-only", render: (r) => (r.enforce_read_only ? "yes" : "no") },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (r) => (
        <div className="flex justify-end gap-2">
          {r.status === "scheduled" && (
            <Button size="sm" onClick={() => act(() => opsGovApi.maintenance.start(r.id), "Started.")}>Start</Button>
          )}
          {r.status === "in_progress" && (
            <Button size="sm" onClick={() => act(() => opsGovApi.maintenance.complete(r.id), "Completed.")}>Complete</Button>
          )}
          <Button size="sm" variant="danger" onClick={() => act(() => opsGovApi.maintenance.remove(r.id), "Deleted.")}>Delete</Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-3">
      <PanelHeader title="Scheduled maintenance" onNew={() => setEditing({ enforce_read_only: false })} />
      <DataTable columns={columns} rows={data ?? []} rowKey={(r) => r.id} loading={loading} searchable />

      <Modal open={!!editing} title="Schedule maintenance" onClose={() => setEditing(null)}>
        {editing && (
          <div className="space-y-3">
            <Input label="Title" value={editing.title ?? ""} onChange={(e) => setEditing({ ...editing, title: e.target.value })} />
            <Textarea label="Description" value={editing.description ?? ""} onChange={(e) => setEditing({ ...editing, description: e.target.value })} />
            <div className="grid grid-cols-2 gap-3">
              <Input label="Start" type="datetime-local" value={editing.scheduled_start ?? ""} onChange={(e) => setEditing({ ...editing, scheduled_start: e.target.value })} />
              <Input label="End" type="datetime-local" value={editing.scheduled_end ?? ""} onChange={(e) => setEditing({ ...editing, scheduled_end: e.target.value })} />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={!!editing.enforce_read_only} onChange={(e) => setEditing({ ...editing, enforce_read_only: e.target.checked })} />
              Enforce read-only mode while active
            </label>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setEditing(null)}>Cancel</Button>
              <Button onClick={save}>Schedule</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Incidents
// --------------------------------------------------------------------------- //

function IncidentsPanel() {
  const toast = useToast();
  const { data, loading, refetch } = useApi(() => opsGovApi.incidents.list());
  const [creating, setCreating] = React.useState<Partial<Incident> | null>(null);
  const [updating, setUpdating] = React.useState<Incident | null>(null);
  const [update, setUpdate] = React.useState({ status: "investigating", message: "" });

  const create = async () => {
    if (!creating?.title) return toast.error("Title is required.");
    try {
      await opsGovApi.incidents.create(creating);
      toast.success("Incident opened.");
      setCreating(null);
      refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed.");
    }
  };

  const postUpdate = async () => {
    if (!updating || !update.message) return toast.error("Message is required.");
    try {
      await opsGovApi.incidents.addUpdate(updating.id, update);
      toast.success("Update posted.");
      setUpdating(null);
      setUpdate({ status: "investigating", message: "" });
      refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed.");
    }
  };

  const columns: Column<Incident>[] = [
    { key: "title", header: "Title", sortable: true },
    { key: "severity", header: "Severity", sortable: true },
    { key: "status", header: "Status", sortable: true },
    { key: "is_public", header: "Public", render: (r) => (r.is_public ? "yes" : "no") },
    { key: "started_at", header: "Started", sortable: true, render: (r) => new Date(r.started_at).toLocaleString() },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (r) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" onClick={() => { setUpdating(r); setUpdate({ status: r.status, message: "" }); }}>
            Post update
          </Button>
          <Button size="sm" variant="danger" onClick={async () => { await opsGovApi.incidents.remove(r.id); refetch(); }}>
            Delete
          </Button>
        </div>
      ),
    },
  ];

  const statusOptions = [
    { value: "investigating", label: "Investigating" },
    { value: "identified", label: "Identified" },
    { value: "monitoring", label: "Monitoring" },
    { value: "resolved", label: "Resolved" },
  ];

  return (
    <div className="space-y-3">
      <PanelHeader title="Incidents" onNew={() => setCreating({ severity: "sev3", is_public: false })} />
      <DataTable columns={columns} rows={data ?? []} rowKey={(r) => r.id} loading={loading} searchable />

      <Modal open={!!creating} title="Open incident" onClose={() => setCreating(null)}>
        {creating && (
          <div className="space-y-3">
            <Input label="Title" value={creating.title ?? ""} onChange={(e) => setCreating({ ...creating, title: e.target.value })} />
            <Textarea label="Summary" value={creating.summary ?? ""} onChange={(e) => setCreating({ ...creating, summary: e.target.value })} />
            <Select label="Severity" value={creating.severity ?? "sev3"} onChange={(e) => setCreating({ ...creating, severity: e.target.value as Incident["severity"] })}
              options={[{ value: "sev1", label: "SEV1 — Critical" }, { value: "sev2", label: "SEV2 — Major" }, { value: "sev3", label: "SEV3 — Minor" }, { value: "sev4", label: "SEV4 — Low" }]} />
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={!!creating.is_public} onChange={(e) => setCreating({ ...creating, is_public: e.target.checked })} />
              Show on public status feed
            </label>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setCreating(null)}>Cancel</Button>
              <Button onClick={create}>Open</Button>
            </div>
          </div>
        )}
      </Modal>

      <Modal open={!!updating} title={`Update: ${updating?.title ?? ""}`} onClose={() => setUpdating(null)}>
        {updating && (
          <div className="space-y-3">
            <Select label="New status" value={update.status} onChange={(e) => setUpdate({ ...update, status: e.target.value })} options={statusOptions} />
            <Textarea label="Message" value={update.message} onChange={(e) => setUpdate({ ...update, message: e.target.value })} />
            <div className="mt-2 max-h-40 space-y-2 overflow-auto text-sm">
              {updating.updates.map((u) => (
                <div key={u.id} className="rounded-lg border border-[var(--border)] p-2">
                  <div className="text-xs text-[var(--foreground-secondary)]">
                    {new Date(u.created_at).toLocaleString()} · {u.status}
                  </div>
                  {u.message}
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setUpdating(null)}>Cancel</Button>
              <Button onClick={postUpdate}>Post update</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Feature flags
// --------------------------------------------------------------------------- //

function FeatureFlagsPanel() {
  const toast = useToast();
  const { data, loading, refetch } = useApi(() => opsGovApi.flags.list());
  const [editing, setEditing] = React.useState<Partial<FeatureFlag> | null>(null);
  const [managing, setManaging] = React.useState<FeatureFlag | null>(null);

  const save = async () => {
    if (!editing?.key) return toast.error("Key is required.");
    try {
      if (editing.id) await opsGovApi.flags.update(editing.id, editing);
      else await opsGovApi.flags.create(editing);
      toast.success("Saved.");
      setEditing(null);
      refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Save failed.");
    }
  };

  const toggleKill = async (flag: FeatureFlag) => {
    try {
      await opsGovApi.flags.kill(flag.id, !flag.kill);
      toast.success(flag.kill ? "Kill switch released." : "Flag killed.");
      refetch();
    } catch {
      toast.error("Failed.");
    }
  };

  const columns: Column<FeatureFlag>[] = [
    { key: "key", header: "Key", sortable: true },
    { key: "is_active", header: "Active", render: (r) => (r.is_active ? "on" : "off") },
    { key: "rollout_percentage", header: "Rollout %", sortable: true, align: "right" },
    { key: "kill", header: "Kill", render: (r) => (r.kill ? "⛔ killed" : "—") },
    {
      key: "overrides",
      header: "Overrides",
      align: "right",
      render: (r) => r.overrides?.length ?? 0,
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (r) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => setManaging(r)}>Overrides</Button>
          <Button size="sm" variant={r.kill ? "secondary" : "danger"} onClick={() => toggleKill(r)}>
            {r.kill ? "Release" : "Kill"}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setEditing(r)}>Edit</Button>
          <Button size="sm" variant="danger" onClick={async () => { await opsGovApi.flags.remove(r.id); refetch(); }}>Delete</Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-3">
      <PanelHeader title="Feature flags" onNew={() => setEditing({ is_active: false, rollout_percentage: 0 })} />
      <DataTable columns={columns} rows={data ?? []} rowKey={(r) => r.id} loading={loading} searchable />

      <Modal open={!!editing} title={editing?.id ? "Edit flag" : "New flag"} onClose={() => setEditing(null)}>
        {editing && (
          <div className="space-y-3">
            <Input label="Key" value={editing.key ?? ""} disabled={!!editing.id}
              onChange={(e) => setEditing({ ...editing, key: e.target.value })} />
            <Input label="Name" value={editing.name ?? ""} onChange={(e) => setEditing({ ...editing, name: e.target.value })} />
            <Textarea label="Description" value={editing.description ?? ""} onChange={(e) => setEditing({ ...editing, description: e.target.value })} />
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={!!editing.is_active} onChange={(e) => setEditing({ ...editing, is_active: e.target.checked })} />
              Active (master switch)
            </label>
            <Input label="Rollout %" type="number" min={0} max={100} value={editing.rollout_percentage ?? 0}
              onChange={(e) => setEditing({ ...editing, rollout_percentage: Number(e.target.value) })} />
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setEditing(null)}>Cancel</Button>
              <Button onClick={save}>Save</Button>
            </div>
          </div>
        )}
      </Modal>

      {managing && (
        <OverridesManager
          flag={managing}
          onClose={() => {
            setManaging(null);
            refetch(); // refresh override counts
          }}
        />
      )}
    </div>
  );
}

function PanelHeader({ title, onNew }: { title: string; onNew: () => void }) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="text-lg font-semibold">{title}</h2>
      <Button size="sm" onClick={onNew}>+ New</Button>
    </div>
  );
}
