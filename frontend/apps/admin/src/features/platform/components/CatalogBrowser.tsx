"use client";

import React, { useEffect, useState } from "react";
import { Button, Input, Modal, Select, Table, useToast } from "@hostel/ui";
import { Plus } from "lucide-react";
import { platformApi } from "../api/platform.api";
import type { Feature, FeatureCategory, LimitDefinition } from "../types/platform.types";
import { Badge, Tabs, Toggle } from "./primitives";

const STAGES = [
  { value: "stable", label: "Stable" },
  { value: "beta", label: "Beta" },
  { value: "experimental", label: "Experimental" },
  { value: "internal", label: "Internal" },
  { value: "invite_only", label: "Invite only" },
];

export function CatalogBrowser() {
  const toast = useToast();
  const [tab, setTab] = useState("features");
  const [features, setFeatures] = useState<Feature[]>([]);
  const [categories, setCategories] = useState<FeatureCategory[]>([]);
  const [limits, setLimits] = useState<LimitDefinition[]>([]);
  const [modal, setModal] = useState<null | "feature" | "category" | "limit">(null);
  const [draft, setDraft] = useState<Record<string, string | boolean>>({});
  const [busy, setBusy] = useState(false);

  const reload = async () => {
    const [f, c, l] = await Promise.all([
      platformApi.features.list(),
      platformApi.categories.list(),
      platformApi.limits.list(),
    ]);
    setFeatures(f);
    setCategories(c);
    setLimits(l);
  };

  useEffect(() => {
    reload().catch((e) => toast.error((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleActive = async (
    kind: "feature" | "category" | "limit",
    id: string,
    is_active: boolean,
  ) => {
    try {
      if (kind === "feature") await platformApi.features.update(id, { is_active });
      if (kind === "category") await platformApi.categories.update(id, { is_active });
      if (kind === "limit") await platformApi.limits.update(id, { is_active });
      await reload();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const openCreate = (kind: "feature" | "category" | "limit") => {
    setDraft(kind === "feature" ? { release_stage: "stable" } : { allow_unlimited: true });
    setModal(kind);
  };

  const create = async () => {
    setBusy(true);
    try {
      if (modal === "feature") {
        await platformApi.features.create({
          key: String(draft.key || ""),
          name: String(draft.name || ""),
          category: String(draft.category || categories[0]?.id || ""),
          release_stage: String(draft.release_stage || "stable"),
          is_enterprise_only: Boolean(draft.is_enterprise_only),
          default_enabled: Boolean(draft.default_enabled),
        });
      } else if (modal === "category") {
        await platformApi.categories.create({
          key: String(draft.key || ""),
          name: String(draft.name || ""),
          icon: String(draft.icon || ""),
          color: String(draft.color || ""),
        });
      } else if (modal === "limit") {
        await platformApi.limits.create({
          key: String(draft.key || ""),
          name: String(draft.name || ""),
          unit: String(draft.unit || ""),
          default_value: Number(draft.default_value) || 0,
          allow_unlimited: Boolean(draft.allow_unlimited),
        });
      }
      toast.success("Created.");
      setModal(null);
      await reload();
    } catch (e) {
      toast.error((e as Error).message, "Create failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Tabs
          tabs={[
            { id: "features", label: "Features", count: features.length },
            { id: "categories", label: "Categories", count: categories.length },
            { id: "limits", label: "Limits", count: limits.length },
          ]}
          active={tab}
          onChange={setTab}
        />
        <Button
          size="sm"
          onClick={() => openCreate(tab === "categories" ? "category" : tab === "limits" ? "limit" : "feature")}
        >
          <Plus className="h-4 w-4" /> New
        </Button>
      </div>

      {tab === "features" && (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Feature</th>
              <th className="px-4 py-3 font-medium">Category</th>
              <th className="px-4 py-3 font-medium">Stage</th>
              <th className="px-4 py-3 font-medium text-right">Active</th>
            </tr>
          </thead>
          <tbody>
            {features.map((f) => (
              <tr key={f.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-[var(--foreground)]">{f.display_name || f.name}</span>
                    {f.is_enterprise_only ? <Badge color="#1d4ed8">Enterprise</Badge> : null}
                  </div>
                  <div className="text-xs text-[var(--muted)]">{f.key}</div>
                </td>
                <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{f.category_name}</td>
                <td className="px-4 py-2.5 capitalize text-[var(--foreground-secondary)]">{f.release_stage}</td>
                <td className="px-4 py-2.5">
                  <div className="flex justify-end">
                    <Toggle checked={f.is_active} onChange={(v) => toggleActive("feature", f.id, v)} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {tab === "categories" && (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Category</th>
              <th className="px-4 py-3 font-medium">Features</th>
              <th className="px-4 py-3 font-medium text-right">Active</th>
            </tr>
          </thead>
          <tbody>
            {categories.map((c) => (
              <tr key={c.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <span className="h-3 w-3 rounded-full" style={{ backgroundColor: c.color || "var(--muted)" }} />
                    <span className="font-medium text-[var(--foreground)]">{c.name}</span>
                  </div>
                  <div className="text-xs text-[var(--muted)]">{c.key}</div>
                </td>
                <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{c.feature_count}</td>
                <td className="px-4 py-2.5">
                  <div className="flex justify-end">
                    <Toggle checked={c.is_active} onChange={(v) => toggleActive("category", c.id, v)} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {tab === "limits" && (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Limit</th>
              <th className="px-4 py-3 font-medium">Default</th>
              <th className="px-4 py-3 font-medium">Unlimited?</th>
              <th className="px-4 py-3 font-medium text-right">Active</th>
            </tr>
          </thead>
          <tbody>
            {limits.map((l) => (
              <tr key={l.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-2.5">
                  <div className="font-medium text-[var(--foreground)]">{l.name}</div>
                  <div className="text-xs text-[var(--muted)]">{l.key}{l.unit ? ` · ${l.unit}` : ""}</div>
                </td>
                <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{l.default_value}</td>
                <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{l.allow_unlimited ? "Yes" : "No"}</td>
                <td className="px-4 py-2.5">
                  <div className="flex justify-end">
                    <Toggle checked={l.is_active} onChange={(v) => toggleActive("limit", l.id, v)} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal
        open={modal !== null}
        title={modal === "category" ? "New category" : modal === "limit" ? "New limit" : "New feature"}
        onClose={() => setModal(null)}
      >
        <div className="space-y-3">
          <Input label="Key (machine id)" value={String(draft.key || "")} onChange={(e) => setDraft((d) => ({ ...d, key: e.target.value }))} placeholder="e.g. ai_insights" />
          <Input label="Name" value={String(draft.name || "")} onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))} />

          {modal === "feature" && (
            <>
              <Select
                label="Category"
                value={String(draft.category || categories[0]?.id || "")}
                onChange={(e) => setDraft((d) => ({ ...d, category: e.target.value }))}
                options={categories.map((c) => ({ value: c.id, label: c.name }))}
              />
              <Select
                label="Release stage"
                value={String(draft.release_stage || "stable")}
                onChange={(e) => setDraft((d) => ({ ...d, release_stage: e.target.value }))}
                options={STAGES}
              />
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
                  <Toggle checked={Boolean(draft.default_enabled)} onChange={(v) => setDraft((d) => ({ ...d, default_enabled: v }))} /> Default on
                </label>
                <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
                  <Toggle checked={Boolean(draft.is_enterprise_only)} onChange={(v) => setDraft((d) => ({ ...d, is_enterprise_only: v }))} /> Enterprise only
                </label>
              </div>
            </>
          )}

          {modal === "category" && (
            <div className="grid grid-cols-2 gap-3">
              <Input label="Icon (lucide name)" value={String(draft.icon || "")} onChange={(e) => setDraft((d) => ({ ...d, icon: e.target.value }))} />
              <Input label="Color (hex)" value={String(draft.color || "")} onChange={(e) => setDraft((d) => ({ ...d, color: e.target.value }))} />
            </div>
          )}

          {modal === "limit" && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Input label="Unit" value={String(draft.unit || "")} onChange={(e) => setDraft((d) => ({ ...d, unit: e.target.value }))} />
                <Input label="Default value" type="number" value={String(draft.default_value ?? "")} onChange={(e) => setDraft((d) => ({ ...d, default_value: e.target.value }))} />
              </div>
              <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
                <Toggle checked={Boolean(draft.allow_unlimited)} onChange={(v) => setDraft((d) => ({ ...d, allow_unlimited: v }))} /> Allow unlimited
              </label>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setModal(null)}>Cancel</Button>
            <Button loading={busy} onClick={create}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
