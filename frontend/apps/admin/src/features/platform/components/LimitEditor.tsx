"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Button, useToast } from "@hostel/ui";
import { platformApi } from "../api/platform.api";
import type { PlanLimitRow } from "../types/platform.types";
import { Toggle } from "./primitives";

type Draft = Record<string, { value: number; is_unlimited: boolean }>;

export function LimitEditor({ planId }: { planId: string }) {
  const toast = useToast();
  const [rows, setRows] = useState<PlanLimitRow[]>([]);
  const [draft, setDraft] = useState<Draft>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    platformApi.plans
      .limits(planId)
      .then((r) => {
        setRows(r);
        setDraft(
          Object.fromEntries(
            r.map((x) => [x.key, { value: x.value ?? 0, is_unlimited: x.is_unlimited }]),
          ),
        );
      })
      .catch((e) => toast.error((e as Error).message))
      .finally(() => setLoading(false));
  }, [planId, toast]);

  const dirty = useMemo(
    () =>
      rows.some((r) => {
        const d = draft[r.key];
        if (!d) return false;
        return d.is_unlimited !== r.is_unlimited || (!d.is_unlimited && d.value !== (r.value ?? 0));
      }),
    [rows, draft],
  );

  const save = async () => {
    setSaving(true);
    try {
      const updated = await platformApi.plans.setLimits(planId, draft);
      setRows(updated);
      setDraft(
        Object.fromEntries(
          updated.map((x) => [x.key, { value: x.value ?? 0, is_unlimited: x.is_unlimited }]),
        ),
      );
      toast.success("Limits saved.");
    } catch (e) {
      toast.error((e as Error).message, "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading limits…</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-[var(--muted)]">
          Set each quota. Toggle “Unlimited” to remove the cap. Metered quotas (SMS/email/API) are
          resolved here but enforced by the usage meter.
        </p>
        <div className="flex items-center gap-2">
          {dirty ? <span className="text-xs text-[var(--warning)]">Unsaved changes</span> : null}
          <Button loading={saving} disabled={!dirty} onClick={save}>
            Save limits
          </Button>
        </div>
      </div>

      <div className="rounded-[20px] border border-[var(--border)] bg-[var(--card)] divide-y divide-[var(--border)]">
        {rows.map((r) => {
          const d = draft[r.key] ?? { value: 0, is_unlimited: false };
          return (
            <div key={r.key} className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5">
              <div className="min-w-0">
                <div className="text-sm font-medium text-[var(--foreground)]">{r.name}</div>
                <div className="text-xs text-[var(--muted)]">
                  {r.key}
                  {r.unit ? ` · ${r.unit}` : ""} · default {r.default_value}
                </div>
              </div>
              <div className="flex items-center gap-4">
                <input
                  type="number"
                  min={0}
                  disabled={d.is_unlimited}
                  value={d.is_unlimited ? "" : d.value}
                  placeholder={d.is_unlimited ? "∞" : ""}
                  onChange={(e) =>
                    setDraft((prev) => ({
                      ...prev,
                      [r.key]: { ...d, value: Number(e.target.value) || 0 },
                    }))
                  }
                  className="w-28 rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-1.5 text-sm text-[var(--foreground)] outline-none focus:border-[var(--accent)] disabled:opacity-50"
                />
                <label className="flex items-center gap-2 text-xs text-[var(--foreground-secondary)]">
                  Unlimited
                  <Toggle
                    checked={d.is_unlimited}
                    disabled={!r.allow_unlimited}
                    onChange={(v) =>
                      setDraft((prev) => ({ ...prev, [r.key]: { ...d, is_unlimited: v } }))
                    }
                    label={`${r.name} unlimited`}
                  />
                </label>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
