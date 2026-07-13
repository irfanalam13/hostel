"use client";

import React from "react";
import {
  Button,
  DataTable,
  Input,
  Modal,
  Select,
  useConfirm,
  useToast,
  type Column,
} from "@hostel/ui";
import { useApi } from "@hostel/hooks";

import { opsGovApi } from "../api/opsgov.api";
import type { FeatureFlag, FeatureFlagOverride, LookupResult } from "../types/opsgov.types";
import { TargetCombobox } from "./TargetCombobox";

type TargetType = "hostel" | "user";

type FormState = {
  targetType: TargetType;
  target: LookupResult | null;
  enabled: boolean;
  reason: string;
  starts_at: string; // datetime-local
  expires_at: string; // datetime-local
};

const EMPTY_FORM: FormState = {
  targetType: "hostel",
  target: null,
  enabled: true,
  reason: "",
  starts_at: "",
  expires_at: "",
};

const STATE_STYLES: Record<string, string> = {
  active: "bg-[color-mix(in_srgb,var(--success)_16%,transparent)] text-[var(--success)]",
  scheduled: "bg-[color-mix(in_srgb,var(--info)_16%,transparent)] text-[var(--info)]",
  expired: "bg-[color-mix(in_srgb,var(--muted)_24%,transparent)] text-[var(--muted)]",
  revoked: "bg-[color-mix(in_srgb,var(--warning)_18%,transparent)] text-[var(--warning)]",
};

// ISO <-> <input type="datetime-local"> value ("YYYY-MM-DDTHH:mm", local tz).
function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function fromLocalInput(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

export function OverridesManager({ flag, onClose }: { flag: FeatureFlag; onClose: () => void }) {
  const toast = useToast();
  const confirm = useConfirm();
  const { data, loading, refetch } = useApi(() => opsGovApi.overrides.list(flag.id), {
    deps: [flag.id],
  });

  const [builderOpen, setBuilderOpen] = React.useState(false);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [form, setForm] = React.useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = React.useState(false);

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setBuilderOpen(true);
  };

  const openEdit = (ov: FeatureFlagOverride) => {
    setEditingId(ov.id);
    setForm({
      targetType: ov.user ? "user" : "hostel",
      target: ov.user
        ? { id: ov.user, label: ov.user_label ?? String(ov.user) }
        : ov.hostel_id
          ? { id: ov.hostel_id, label: ov.hostel_label ?? ov.hostel_id }
          : null,
      enabled: ov.enabled,
      reason: ov.reason,
      starts_at: toLocalInput(ov.starts_at),
      expires_at: toLocalInput(ov.expires_at),
    });
    setBuilderOpen(true);
  };

  const save = async () => {
    if (!form.target) {
      toast.error("Select a target tenant or user.");
      return;
    }
    const payload: Partial<FeatureFlagOverride> & { flag?: string } = {
      enabled: form.enabled,
      reason: form.reason,
      starts_at: fromLocalInput(form.starts_at),
      expires_at: fromLocalInput(form.expires_at),
    };
    if (form.targetType === "hostel") payload.hostel_id = String(form.target.id);
    else payload.user = Number(form.target.id);

    setSaving(true);
    try {
      if (editingId) {
        await opsGovApi.overrides.update(editingId, payload);
      } else {
        await opsGovApi.overrides.create({ ...payload, flag: flag.id });
      }
      toast.success("Override saved.");
      setBuilderOpen(false);
      refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      toast.success(ok);
      refetch();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Action failed.");
    }
  };

  const columns: Column<FeatureFlagOverride>[] = [
    {
      key: "target",
      header: "Target",
      accessor: (r) => r.hostel_label ?? r.user_label ?? "",
      render: (r) => (
        <div>
          <div className="font-medium">{r.hostel_label ?? r.user_label ?? "—"}</div>
          <div className="text-xs text-[var(--muted)]">{r.hostel_id ? "Tenant" : "User"}</div>
        </div>
      ),
    },
    {
      key: "enabled",
      header: "Grants",
      render: (r) => (r.enabled ? "✓ enabled" : "✕ disabled"),
    },
    {
      key: "schedule_state",
      header: "State",
      sortable: true,
      render: (r) => (
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATE_STYLES[r.schedule_state] ?? ""}`}>
          {r.schedule_state}
        </span>
      ),
    },
    {
      key: "window",
      header: "Window",
      render: (r) => (
        <span className="text-xs text-[var(--foreground-secondary)]">
          {r.starts_at ? new Date(r.starts_at).toLocaleString() : "now"} →{" "}
          {r.expires_at ? new Date(r.expires_at).toLocaleString() : "∞"}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (r) => (
        <div className="flex justify-end gap-1.5">
          <Button size="sm" variant="ghost" onClick={() => openEdit(r)}>
            Edit
          </Button>
          {r.is_active ? (
            <Button size="sm" variant="secondary" onClick={() => act(() => opsGovApi.overrides.revoke(r.id), "Revoked.")}>
              Revoke
            </Button>
          ) : (
            <Button size="sm" variant="secondary" onClick={() => act(() => opsGovApi.overrides.reactivate(r.id), "Reactivated.")}>
              Reactivate
            </Button>
          )}
          <Button
            size="sm"
            variant="danger"
            onClick={async () => {
              if (await confirm({ title: "Delete override?", message: "This permanently removes the override.", confirmText: "Delete", danger: true })) {
                act(() => opsGovApi.overrides.remove(r.id), "Deleted.");
              }
            }}
          >
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <Modal open title={`Overrides · ${flag.key}`} onClose={onClose}>
      {builderOpen ? (
        <div className="space-y-3">
          <div className="flex rounded-lg bg-[var(--background-secondary)] p-0.5 text-sm">
            {(["hostel", "user"] as TargetType[]).map((t) => (
              <button
                key={t}
                disabled={!!editingId}
                onClick={() => setForm({ ...form, targetType: t, target: null })}
                className={`flex-1 rounded-md px-3 py-1.5 font-medium transition disabled:opacity-50 ${
                  form.targetType === t ? "bg-[var(--accent)] text-white" : "text-[var(--foreground-secondary)]"
                }`}
              >
                {t === "hostel" ? "Tenant" : "User"}
              </button>
            ))}
          </div>

          {form.targetType === "hostel" ? (
            <TargetCombobox
              label="Tenant"
              placeholder="Search tenants by name or code…"
              value={form.target}
              onChange={(v) => setForm({ ...form, target: v })}
              fetcher={opsGovApi.lookups.hostels}
              disabled={!!editingId}
            />
          ) : (
            <TargetCombobox
              label="User"
              placeholder="Search users by name or email…"
              value={form.target}
              onChange={(v) => setForm({ ...form, target: v })}
              fetcher={opsGovApi.lookups.users}
              disabled={!!editingId}
            />
          )}

          <Select
            label="Effect"
            value={form.enabled ? "on" : "off"}
            onChange={(e) => setForm({ ...form, enabled: e.target.value === "on" })}
            options={[
              { value: "on", label: "Enable feature for this target" },
              { value: "off", label: "Disable feature for this target" },
            ]}
          />

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Starts (optional)"
              type="datetime-local"
              value={form.starts_at}
              onChange={(e) => setForm({ ...form, starts_at: e.target.value })}
            />
            <Input
              label="Expires (optional)"
              type="datetime-local"
              value={form.expires_at}
              onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
            />
          </div>
          <p className="text-xs text-[var(--muted)]">
            Leave blank for an open-ended override. Scheduled overrides apply only within their window.
          </p>

          <Input
            label="Reason"
            value={form.reason}
            onChange={(e) => setForm({ ...form, reason: e.target.value })}
            placeholder="Why this override exists (audit note)"
          />

          <div className="flex justify-end gap-2 pt-1">
            <Button variant="secondary" onClick={() => setBuilderOpen(false)}>
              Cancel
            </Button>
            <Button onClick={save} loading={saving}>
              {editingId ? "Save changes" : "Create override"}
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-[var(--foreground-secondary)]">
              Per-tenant and per-user grants that override <code>{flag.key}</code>. Overrides win over
              rollout and the master switch (kill switch still wins over everything).
            </p>
            <Button size="sm" onClick={openCreate}>
              + New override
            </Button>
          </div>
          <DataTable
            columns={columns}
            rows={data ?? []}
            rowKey={(r) => r.id}
            loading={loading}
            emptyMessage="No overrides for this flag yet."
            pageSize={8}
            initialSort={{ key: "schedule_state", dir: "asc" }}
          />
        </div>
      )}
    </Modal>
  );
}
