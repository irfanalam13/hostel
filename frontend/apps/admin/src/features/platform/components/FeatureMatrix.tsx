"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Button, useToast } from "@hostel/ui";
import { AlertTriangle } from "lucide-react";
import { platformApi } from "../api/platform.api";
import type { DependencyViolation, PlanFeatureRow } from "../types/platform.types";
import { Badge, Toggle } from "./primitives";

export function FeatureMatrix({ planId }: { planId: string }) {
  const toast = useToast();
  const [rows, setRows] = useState<PlanFeatureRow[]>([]);
  const [draft, setDraft] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [violations, setViolations] = useState<DependencyViolation[]>([]);

  useEffect(() => {
    platformApi.plans
      .features(planId)
      .then((r) => {
        setRows(r);
        setDraft(Object.fromEntries(r.map((x) => [x.key, x.enabled])));
      })
      .catch((e) => toast.error((e as Error).message))
      .finally(() => setLoading(false));
  }, [planId, toast]);

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
                  <Toggle
                    checked={!!draft[r.key]}
                    onChange={(v) => setDraft((d) => ({ ...d, [r.key]: v }))}
                    label={r.name}
                  />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
