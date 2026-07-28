"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Button, Modal, Select, useToast } from "@hostel/ui";
import { AlertTriangle, Settings2, X } from "lucide-react";
import { platformApi } from "../api/platform.api";
import type { DependencyViolation, FeatureDependency, PlanFeatureRow } from "../types/platform.types";
import { Badge, Toggle } from "./primitives";

export function FeatureMatrix({ planId }: { planId: string }) {
  const toast = useToast();
  const [rows, setRows] = useState<PlanFeatureRow[]>([]);
  const [draft, setDraft] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [violations, setViolations] = useState<DependencyViolation[]>([]);
  const [dependencies, setDependencies] = useState<FeatureDependency[]>([]);
  const [depFeature, setDepFeature] = useState<PlanFeatureRow | null>(null);
  const [newRequires, setNewRequires] = useState("");
  const [depBusy, setDepBusy] = useState(false);

  const loadDependencies = () => platformApi.featureDependencies.list().then(setDependencies);

  useEffect(() => {
    platformApi.plans
      .features(planId)
      .then((r) => {
        setRows(r);
        setDraft(Object.fromEntries(r.map((x) => [x.key, x.enabled])));
      })
      .catch((e) => toast.error((e as Error).message))
      .finally(() => setLoading(false));
    loadDependencies().catch((e) => toast.error((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId, toast]);

  const addDependency = async () => {
    if (!depFeature || !newRequires) return;
    setDepBusy(true);
    try {
      await platformApi.featureDependencies.create(depFeature.feature, newRequires);
      await loadDependencies();
      setNewRequires("");
    } catch (e) {
      toast.error((e as Error).message, "Couldn't add dependency");
    } finally {
      setDepBusy(false);
    }
  };

  const removeDependency = async (id: string) => {
    setDepBusy(true);
    try {
      await platformApi.featureDependencies.remove(id);
      await loadDependencies();
    } catch (e) {
      toast.error((e as Error).message, "Couldn't remove dependency");
    } finally {
      setDepBusy(false);
    }
  };

  const grouped = useMemo(() => {
    const map = new Map<string, { name: string; items: PlanFeatureRow[] }>();
    for (const r of rows) {
      if (!map.has(r.category_key)) map.set(r.category_key, { name: r.category_name, items: [] });
      map.get(r.category_key)!.items.push(r);
    }
    return [...map.values()];
  }, [rows]);

  const dirty = useMemo(
    () => rows.some((r) => draft[r.key] !== r.enabled),
    [rows, draft],
  );

  // Client-side hint: an enabled feature whose requirement is off.
  const localWarnings = useMemo(() => {
    const out: string[] = [];
    for (const r of rows) {
      if (draft[r.key]) {
        for (const req of r.requires) {
          if (draft[req] === false) out.push(`${r.name} needs ${req}`);
        }
      }
    }
    return out;
  }, [rows, draft]);

  const save = async (force = false) => {
    setSaving(true);
    setViolations([]);
    try {
      const updated = await platformApi.plans.setFeatures(planId, draft, force);
      setRows(updated);
      setDraft(Object.fromEntries(updated.map((x) => [x.key, x.enabled])));
      toast.success("Features saved.");
    } catch (e) {
      const err = e as Error & { data?: { code?: string; violations?: DependencyViolation[] } };
      if (err.data?.code === "dependency_violation" && err.data.violations) {
        setViolations(err.data.violations);
      } else {
        toast.error(err.message, "Save failed");
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading features…</div>;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-[var(--muted)]">
          Toggle which features this plan includes. Non-stable features are gated on early-access enrolment.
        </p>
        <div className="flex items-center gap-2">
          {dirty ? <span className="text-xs text-[var(--warning)]">Unsaved changes</span> : null}
          <Button loading={saving} disabled={!dirty} onClick={() => save(false)}>
            Save features
          </Button>
        </div>
      </div>

      {violations.length > 0 ? (
        <div className="rounded-xl border border-[var(--warning)] bg-[color-mix(in_srgb,var(--warning)_10%,transparent)] p-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-[var(--foreground)]">
            <AlertTriangle className="h-4 w-4 text-[var(--warning)]" /> Dependency issues
          </div>
          <ul className="mt-2 list-disc pl-6 text-sm text-[var(--foreground-secondary)]">
            {violations.map((v, i) => (
              <li key={i}>
                <strong>{v.feature_name}</strong> requires <strong>{v.requires_name}</strong> to be enabled.
              </li>
            ))}
          </ul>
          <div className="mt-3 flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => save(true)} loading={saving}>
              Save anyway
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setViolations([])}>
              Dismiss
            </Button>
          </div>
        </div>
      ) : localWarnings.length > 0 ? (
        <div className="text-xs text-[var(--warning)]">
          Heads up: {localWarnings.join(" · ")}
        </div>
      ) : null}

      <div className="space-y-5">
        {grouped.map((group) => (
          <div key={group.name} className="rounded-[20px] border border-[var(--border)] bg-[var(--card)]">
            <div className="border-b border-[var(--border)] px-4 py-2.5 text-sm font-semibold text-[var(--foreground)]">
              {group.name}
            </div>
            <div className="divide-y divide-[var(--border)]">
              {group.items.map((r) => (
                <div key={r.key} className="flex items-center justify-between gap-3 px-4 py-2.5">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[var(--foreground)]">{r.name}</span>
                      {r.is_enterprise_only ? <Badge color="#1d4ed8">Enterprise</Badge> : null}
                      {r.release_stage !== "stable" ? (
                        <Badge color="#9333ea">{r.release_stage}</Badge>
                      ) : null}
                    </div>
                    {r.requires.length > 0 ? (
                      <div className="text-xs text-[var(--muted)]">requires: {r.requires.join(", ")}</div>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      title="Manage dependencies"
                      onClick={() => setDepFeature(r)}
                      className="text-[var(--muted)] hover:text-[var(--foreground)]"
                    >
                      <Settings2 className="h-4 w-4" />
                    </button>
                    <Toggle
                      checked={!!draft[r.key]}
                      onChange={(v) => setDraft((d) => ({ ...d, [r.key]: v }))}
                      label={r.name}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <Modal
        open={!!depFeature}
        title={depFeature ? `Dependencies for ${depFeature.name}` : "Dependencies"}
        onClose={() => {
          setDepFeature(null);
          setNewRequires("");
        }}
      >
        {depFeature ? (
          <div className="space-y-3">
            <div className="space-y-1">
              {dependencies.filter((d) => d.feature === depFeature.feature).length === 0 ? (
                <div className="text-xs text-[var(--muted)]">No dependencies yet — this feature requires nothing.</div>
              ) : (
                dependencies
                  .filter((d) => d.feature === depFeature.feature)
                  .map((d) => (
                    <div
                      key={d.id}
                      className="flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm"
                    >
                      <span className="text-[var(--foreground-secondary)]">requires {d.requires_key}</span>
                      <button
                        type="button"
                        disabled={depBusy}
                        onClick={() => removeDependency(d.id)}
                        className="text-[var(--error)]"
                        title="Remove"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))
              )}
            </div>
            <div className="flex items-end gap-2">
              <Select
                label="Add requirement"
                placeholder="Select a feature"
                value={newRequires}
                onChange={(e) => setNewRequires(e.target.value)}
                options={rows
                  .filter((f) => f.feature !== depFeature.feature)
                  .map((f) => ({ value: f.feature, label: f.name }))}
              />
              <Button size="sm" loading={depBusy} disabled={!newRequires} onClick={addDependency}>
                Add
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
