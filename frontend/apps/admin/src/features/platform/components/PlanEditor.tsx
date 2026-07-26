"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Button, Input, Select, Textarea, useToast } from "@hostel/ui";
import { ArrowLeft } from "lucide-react";
import { platformApi } from "../api/platform.api";
import type { Plan } from "../types/platform.types";
import { FeatureMatrix } from "./FeatureMatrix";
import { LimitEditor } from "./LimitEditor";
import { Field, Tabs, Toggle } from "./primitives";

const BILLING = [
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "half_yearly", label: "Half yearly" },
  { value: "yearly", label: "Yearly" },
  { value: "lifetime", label: "Lifetime" },
];
const VISIBILITY = [
  { value: "public", label: "Public (listed on landing page)" },
  { value: "private", label: "Private (assignable, unlisted)" },
  { value: "hidden", label: "Hidden" },
];

function DetailsTab({ plan, onSaved }: { plan: Plan; onSaved: (p: Plan) => void }) {
  const toast = useToast();
  const [form, setForm] = useState(plan);
  const [saving, setSaving] = useState(false);
  const set = (patch: Partial<Plan>) => setForm((f) => ({ ...f, ...patch }));

  const save = async () => {
    setSaving(true);
    try {
      const updated = await platformApi.plans.update(plan.id, {
        name: form.name,
        description: form.description,
        notes: form.notes,
        price_monthly: form.price_monthly,
        price_yearly: form.price_yearly,
        price_lifetime: form.price_lifetime,
        currency: form.currency,
        period: form.period,
        billing_interval: form.billing_interval,
        trial_days: Number(form.trial_days) || 0,
        grace_period_days: Number(form.grace_period_days) || 0,
        tax_percent: form.tax_percent,
        badge: form.badge,
        theme_color: form.theme_color,
        visibility: form.visibility,
        is_active: form.is_active,
        is_recommended: form.is_recommended,
        is_featured: form.is_featured,
        is_public: form.is_public,
      });
      onSaved(updated);
      toast.success("Plan saved.");
    } catch (e) {
      toast.error((e as Error).message, "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5 space-y-4">
        <div className="text-sm font-semibold text-[var(--foreground)]">Basics</div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
          <Input label="Badge (optional)" value={form.badge} onChange={(e) => set({ badge: e.target.value })} />
        </div>
        <Field label="Description">
          <Textarea value={form.description} onChange={(e) => set({ description: e.target.value })} />
        </Field>
        <Field label="Internal notes (not shown to customers)">
          <Textarea value={form.notes} onChange={(e) => set({ notes: e.target.value })} />
        </Field>
      </div>

      <div className="rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5 space-y-4">
        <div className="text-sm font-semibold text-[var(--foreground)]">Pricing & billing</div>
        <div className="grid gap-4 sm:grid-cols-3">
          <Input label="Monthly" type="number" value={form.price_monthly} onChange={(e) => set({ price_monthly: e.target.value })} />
          <Input label="Yearly" type="number" value={form.price_yearly} onChange={(e) => set({ price_yearly: e.target.value })} />
          <Input label="Lifetime" type="number" value={form.price_lifetime} onChange={(e) => set({ price_lifetime: e.target.value })} />
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <Input label="Currency" value={form.currency} onChange={(e) => set({ currency: e.target.value })} />
          <Select label="Default billing interval" options={BILLING} value={form.billing_interval} onChange={(e) => set({ billing_interval: e.target.value })} />
          <Input label="Tax %" type="number" value={form.tax_percent} onChange={(e) => set({ tax_percent: e.target.value })} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Trial days" type="number" value={form.trial_days} onChange={(e) => set({ trial_days: Number(e.target.value) })} />
          <Input label="Grace period (days)" type="number" value={form.grace_period_days} onChange={(e) => set({ grace_period_days: Number(e.target.value) })} />
        </div>
      </div>

      <div className="rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5 space-y-4">
        <div className="text-sm font-semibold text-[var(--foreground)]">Presentation</div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Select label="Visibility" options={VISIBILITY} value={form.visibility} onChange={(e) => set({ visibility: e.target.value as Plan["visibility"] })} />
          <Input label="Theme color (hex)" value={form.theme_color} onChange={(e) => set({ theme_color: e.target.value })} />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            ["is_active", "Active"],
            ["is_recommended", "Recommended"],
            ["is_featured", "Popular (featured)"],
            ["is_public", "Show on landing page"],
          ].map(([key, label]) => (
            <label key={key} className="flex items-center justify-between rounded-xl border border-[var(--border)] px-3 py-2">
              <span className="text-sm text-[var(--foreground-secondary)]">{label}</span>
              <Toggle
                checked={Boolean(form[key as keyof Plan])}
                onChange={(v) => set({ [key]: v } as Partial<Plan>)}
                label={label}
              />
            </label>
          ))}
        </div>
      </div>

      <div className="flex justify-end">
        <Button loading={saving} onClick={save}>
          Save plan
        </Button>
      </div>
    </div>
  );
}

export function PlanEditor({ planId }: { planId: string }) {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [tab, setTab] = useState("details");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    platformApi.plans
      .retrieve(planId)
      .then(setPlan)
      .catch((e) => setError((e as Error).message));
  }, [planId]);

  if (error) return <div className="text-sm text-[var(--error)]">{error}</div>;
  if (!plan) return <div className="text-sm text-[var(--muted)]">Loading plan…</div>;

  return (
    <div className="space-y-4">
      <Link href="/platform/plans" className="inline-flex items-center gap-1 text-sm text-[var(--muted)] hover:text-[var(--foreground)]">
        <ArrowLeft className="h-4 w-4" /> All plans
      </Link>
      <div>
        <h2 className="text-lg font-semibold text-[var(--foreground)]">{plan.name}</h2>
        <p className="text-sm text-[var(--muted)]">{plan.slug}</p>
      </div>

      <Tabs
        tabs={[
          { id: "details", label: "Details" },
          { id: "features", label: "Features" },
          { id: "limits", label: "Limits" },
        ]}
        active={tab}
        onChange={setTab}
      />

      <div className="pt-2">
        {tab === "details" && <DetailsTab plan={plan} onSaved={setPlan} />}
        {tab === "features" && <FeatureMatrix planId={plan.id} />}
        {tab === "limits" && <LimitEditor planId={plan.id} />}
      </div>
    </div>
  );
}
