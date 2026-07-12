"use client";

import React, { useEffect, useState } from "react";
import { Button, EmptyState, Input, Modal, Select, Table, Textarea, useToast, useConfirm } from "@hostel/ui";
import { Plus, Trash2 } from "lucide-react";
import { tenantsApi } from "@/features/tenants/api/tenants.api";
import type { Hostel } from "@/features/tenants/types/tenants.types";
import { platformApi } from "../api/platform.api";
import type {
  Feature,
  FeatureOverride,
  LimitDefinition,
  LimitOverride,
} from "../types/platform.types";
import { Badge, Tabs, Toggle } from "./primitives";

export function OverridesPanel() {
  const toast = useToast();
  const confirm = useConfirm();
  const [tab, setTab] = useState("features");
  const [hostels, setHostels] = useState<Hostel[]>([]);
  const [features, setFeatures] = useState<Feature[]>([]);
  const [limits, setLimits] = useState<LimitDefinition[]>([]);
  const [fOverrides, setFOverrides] = useState<FeatureOverride[]>([]);
  const [lOverrides, setLOverrides] = useState<LimitOverride[]>([]);
  const [modal, setModal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState<Record<string, string | boolean>>({});

  const reload = async () => {
    const [fo, lo] = await Promise.all([
      platformApi.featureOverrides.list(),
      platformApi.limitOverrides.list(),
    ]);
    setFOverrides(fo);
    setLOverrides(lo);
  };

  useEffect(() => {
    Promise.all([
      tenantsApi.hostels.list().catch(() => [] as Hostel[]),
      platformApi.features.list(),
      platformApi.limits.list(),
      platformApi.featureOverrides.list(),
      platformApi.limitOverrides.list(),
    ])
      .then(([h, f, l, fo, lo]) => {
        setHostels(h);
        setFeatures(f);
        setLimits(l);
        setFOverrides(fo);
        setLOverrides(lo);
      })
      .catch((e) => toast.error((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openCreate = () => {
    setDraft(tab === "features" ? { is_enabled: true } : { is_unlimited: false, value: "0" });
    setModal(true);
  };

  const create = async () => {
    setBusy(true);
    try {
      if (tab === "features") {
        await platformApi.featureOverrides.create({
          hostel: String(draft.hostel || ""),
          feature: String(draft.feature || ""),
          is_enabled: Boolean(draft.is_enabled),
          reason: String(draft.reason || ""),
          expires_at: draft.expires_at ? String(draft.expires_at) : null,
        });
      } else {
        await platformApi.limitOverrides.create({
          hostel: String(draft.hostel || ""),
          limit: String(draft.limit || ""),
          value: Number(draft.value) || 0,
          is_unlimited: Boolean(draft.is_unlimited),
          reason: String(draft.reason || ""),
          expires_at: draft.expires_at ? String(draft.expires_at) : null,
        });
      }
      toast.success("Override created.");
      setModal(false);
      await reload();
    } catch (e) {
      toast.error((e as Error).message, "Create failed");
    } finally {
      setBusy(false);
    }
  };

  const removeOverride = async (kind: "feature" | "limit", id: string) => {
    const yes = await confirm({ message: "Remove this override?", danger: true, confirmText: "Remove" });
    if (!yes) return;
    try {
      if (kind === "feature") await platformApi.featureOverrides.remove(id);
      else await platformApi.limitOverrides.remove(id);
      await reload();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const hostelOptions = hostels.map((h) => ({ value: h.id, label: h.name }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Tabs
          tabs={[
            { id: "features", label: "Feature overrides", count: fOverrides.length },
            { id: "limits", label: "Limit overrides", count: lOverrides.length },
          ]}
          active={tab}
          onChange={setTab}
        />
        <Button size="sm" onClick={openCreate} disabled={hostels.length === 0}>
          <Plus className="h-4 w-4" /> New override
        </Button>
      </div>

      {hostels.length === 0 ? (
        <div className="text-xs text-[var(--muted)]">
          No workspaces exist yet — overrides target a specific hostel.
        </div>
      ) : null}

      {tab === "features" &&
        (fOverrides.length === 0 ? (
          <EmptyState title="No feature overrides" description="Grant or revoke a feature for one hostel." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                <th className="px-4 py-3 font-medium">Hostel</th>
                <th className="px-4 py-3 font-medium">Feature</th>
                <th className="px-4 py-3 font-medium">Effect</th>
                <th className="px-4 py-3 font-medium">Expires</th>
                <th className="px-4 py-3 font-medium text-right"></th>
              </tr>
            </thead>
            <tbody>
              {fOverrides.map((o) => (
                <tr key={o.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-4 py-2.5 text-[var(--foreground)]">{o.hostel_name}</td>
                  <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{o.feature_name}</td>
                  <td className="px-4 py-2.5">
                    <Badge color={o.is_enabled ? "var(--success)" : "var(--error)"}>
                      {o.is_enabled ? "Granted" : "Revoked"}
                    </Badge>
                    {!o.is_live ? <Badge>expired</Badge> : null}
                  </td>
                  <td className="px-4 py-2.5 text-[var(--muted)]">
                    {o.expires_at ? new Date(o.expires_at).toLocaleDateString() : "Never"}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <Button variant="ghost" size="sm" onClick={() => removeOverride("feature", o.id)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        ))}

      {tab === "limits" &&
        (lOverrides.length === 0 ? (
          <EmptyState title="No limit overrides" description="Bump or uncap a quota for one hostel." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                <th className="px-4 py-3 font-medium">Hostel</th>
                <th className="px-4 py-3 font-medium">Limit</th>
                <th className="px-4 py-3 font-medium">Value</th>
                <th className="px-4 py-3 font-medium">Expires</th>
                <th className="px-4 py-3 font-medium text-right"></th>
              </tr>
            </thead>
            <tbody>
              {lOverrides.map((o) => (
                <tr key={o.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-4 py-2.5 text-[var(--foreground)]">{o.hostel_name}</td>
                  <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{o.limit_name}</td>
                  <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">
                    {o.is_unlimited ? "∞" : o.value}
                  </td>
                  <td className="px-4 py-2.5 text-[var(--muted)]">
                    {o.expires_at ? new Date(o.expires_at).toLocaleDateString() : "Never"}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <Button variant="ghost" size="sm" onClick={() => removeOverride("limit", o.id)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        ))}

      <Modal
        open={modal}
        title={tab === "features" ? "New feature override" : "New limit override"}
        onClose={() => setModal(false)}
      >
        <div className="space-y-3">
          <Select
            label="Hostel"
            placeholder="Select a workspace"
            value={String(draft.hostel || "")}
            onChange={(e) => setDraft((d) => ({ ...d, hostel: e.target.value }))}
            options={hostelOptions}
          />

          {tab === "features" ? (
            <>
              <Select
                label="Feature"
                placeholder="Select a feature"
                value={String(draft.feature || "")}
                onChange={(e) => setDraft((d) => ({ ...d, feature: e.target.value }))}
                options={features.map((f) => ({ value: f.id, label: f.display_name || f.name }))}
              />
              <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
                <Toggle checked={Boolean(draft.is_enabled)} onChange={(v) => setDraft((d) => ({ ...d, is_enabled: v }))} />
                {draft.is_enabled ? "Grant feature" : "Revoke feature"}
              </label>
            </>
          ) : (
            <>
              <Select
                label="Limit"
                placeholder="Select a limit"
                value={String(draft.limit || "")}
                onChange={(e) => setDraft((d) => ({ ...d, limit: e.target.value }))}
                options={limits.map((l) => ({ value: l.id, label: l.name }))}
              />
              <div className="flex items-end gap-3">
                <div className="flex-1">
                  <Input
                    label="Value"
                    type="number"
                    disabled={Boolean(draft.is_unlimited)}
                    value={String(draft.value ?? "")}
                    onChange={(e) => setDraft((d) => ({ ...d, value: e.target.value }))}
                  />
                </div>
                <label className="flex items-center gap-2 pb-2 text-sm text-[var(--foreground-secondary)]">
                  <Toggle checked={Boolean(draft.is_unlimited)} onChange={(v) => setDraft((d) => ({ ...d, is_unlimited: v }))} /> Unlimited
                </label>
              </div>
            </>
          )}

          <Input
            label="Expires at (optional)"
            type="date"
            value={String(draft.expires_at || "")}
            onChange={(e) => setDraft((d) => ({ ...d, expires_at: e.target.value }))}
          />
          <Field_reason value={String(draft.reason || "")} onChange={(v) => setDraft((d) => ({ ...d, reason: v }))} />

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setModal(false)}>Cancel</Button>
            <Button loading={busy} onClick={create} disabled={!draft.hostel}>Create override</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function Field_reason({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <label className="block">
      <div className="mb-1 text-sm text-[var(--foreground-secondary)]">Reason (optional)</div>
      <Textarea value={value} onChange={(e) => onChange(e.target.value)} placeholder="Why this override exists…" />
    </label>
  );
}
