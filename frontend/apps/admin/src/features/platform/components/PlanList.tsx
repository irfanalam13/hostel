"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button, Input, Modal, Table, EmptyState, Textarea, useToast, useConfirm } from "@hostel/ui";
import {
  Archive,
  ArchiveRestore,
  ChevronDown,
  ChevronUp,
  Copy,
  Download,
  Pencil,
  Plus,
  Power,
  Trash2,
  Upload,
} from "lucide-react";
import { platformApi } from "../api/platform.api";
import type { Plan } from "../types/platform.types";
import { Badge } from "./primitives";

function money(p: Plan) {
  const cur = p.currency || "Rs.";
  if (p.billing_interval === "lifetime") return `${cur} ${p.price_lifetime}`;
  if (p.billing_interval === "yearly") return `${cur} ${p.price_yearly}/yr`;
  return `${cur} ${p.price_monthly}/mo`;
}

export function PlanList() {
  const toast = useToast();
  const confirm = useConfirm();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newPrice, setNewPrice] = useState("0");
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [importing, setImporting] = useState(false);
  const [importJson, setImportJson] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await platformApi.plans.list(search);
      setPlans([...data].sort((a, b) => a.sort_order - b.sort_order));
      setSelected(new Set());
    } catch (e) {
      toast.error((e as Error).message, "Couldn't load plans");
    } finally {
      setLoading(false);
    }
  }, [search, toast]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  const create = async () => {
    if (!newName.trim()) return;
    setBusy(true);
    try {
      const plan = await platformApi.plans.create({ name: newName.trim(), price_monthly: newPrice || "0" });
      toast.success(`Created “${plan.name}”.`);
      setCreating(false);
      setNewName("");
      setNewPrice("0");
      await load();
    } catch (e) {
      toast.error((e as Error).message, "Create failed");
    } finally {
      setBusy(false);
    }
  };

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      toast.success(ok);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const remove = async (plan: Plan) => {
    const yes = await confirm({
      title: "Delete plan",
      message: `Delete “${plan.name}”? This removes its feature and limit configuration. Hostels on this plan fall back to catalog defaults.`,
      danger: true,
      confirmText: "Delete",
    });
    if (yes) await act(() => platformApi.plans.remove(plan.id), "Plan deleted.");
  };

  const exportPlans = async () => {
    try {
      const { plans: data } = await platformApi.plans.export();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "plans-export.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error((e as Error).message, "Export failed");
    }
  };

  const runImport = async () => {
    let rows: unknown[];
    try {
      rows = JSON.parse(importJson);
      if (!Array.isArray(rows)) throw new Error("Expected a JSON array of plans.");
    } catch (e) {
      toast.error((e as Error).message, "Invalid JSON");
      return;
    }
    setBusy(true);
    try {
      const result = await platformApi.plans.import(rows);
      toast.success(`Imported: ${result.created} created, ${result.updated} updated.`);
      setImporting(false);
      setImportJson("");
      await load();
    } catch (e) {
      toast.error((e as Error).message, "Import failed");
    } finally {
      setBusy(false);
    }
  };

  const move = async (index: number, dir: -1 | 1) => {
    const otherIndex = index + dir;
    if (otherIndex < 0 || otherIndex >= plans.length) return;
    const reordered = [...plans];
    [reordered[index], reordered[otherIndex]] = [reordered[otherIndex], reordered[index]];
    setPlans(reordered);
    try {
      await platformApi.plans.reorder(reordered.map((p, i) => ({ id: p.id, sort_order: i })));
    } catch (e) {
      toast.error((e as Error).message, "Reorder failed");
      await load();
    }
  };

  const toggleSelected = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const bulkAction = async (action: "activate" | "deactivate" | "archive" | "unarchive" | "delete") => {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    if (action === "delete") {
      const yes = await confirm({
        title: "Delete plans",
        message: `Delete ${ids.length} plan(s)? This cannot be undone.`,
        danger: true,
        confirmText: "Delete",
      });
      if (!yes) return;
    }
    try {
      const result = await platformApi.plans.bulk(ids, action);
      toast.success(`${action}: ${result.count} plan(s) updated.`);
      await load();
    } catch (e) {
      toast.error((e as Error).message, "Bulk action failed");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex-1 min-w-[200px]">
          <Input
            placeholder="Search plans…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Button variant="secondary" onClick={exportPlans}>
          <Download className="h-4 w-4" /> Export
        </Button>
        <Button variant="secondary" onClick={() => setImporting(true)}>
          <Upload className="h-4 w-4" /> Import
        </Button>
        <Button onClick={() => setCreating(true)}>
          <Plus className="h-4 w-4" /> New plan
        </Button>
      </div>

      {selected.size > 0 ? (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm">
          <span className="text-[var(--foreground-secondary)]">{selected.size} selected</span>
          <Button variant="ghost" size="sm" onClick={() => bulkAction("activate")}>Activate</Button>
          <Button variant="ghost" size="sm" onClick={() => bulkAction("deactivate")}>Deactivate</Button>
          <Button variant="ghost" size="sm" onClick={() => bulkAction("archive")}>Archive</Button>
          <Button variant="ghost" size="sm" onClick={() => bulkAction("unarchive")}>Unarchive</Button>
          <Button variant="ghost" size="sm" onClick={() => bulkAction("delete")}>
            <Trash2 className="h-4 w-4 text-[var(--error)]" /> Delete
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setSelected(new Set())}>Clear</Button>
        </div>
      ) : null}

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : plans.length === 0 ? (
        <EmptyState title="No plans yet" description="Create your first subscription plan to get started." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="w-8 px-4 py-3"></th>
              <th className="w-14 px-4 py-3"></th>
              <th className="px-4 py-3 font-medium">Plan</th>
              <th className="px-4 py-3 font-medium">Price</th>
              <th className="px-4 py-3 font-medium">Visibility</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Features</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((plan, index) => (
              <tr key={plan.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selected.has(plan.id)}
                    onChange={() => toggleSelected(plan.id)}
                    aria-label={`Select ${plan.name}`}
                  />
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-col">
                    <button
                      type="button"
                      disabled={index === 0}
                      onClick={() => move(index, -1)}
                      className="text-[var(--muted)] hover:text-[var(--foreground)] disabled:opacity-30"
                      title="Move up"
                    >
                      <ChevronUp className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      disabled={index === plans.length - 1}
                      onClick={() => move(index, 1)}
                      className="text-[var(--muted)] hover:text-[var(--foreground)] disabled:opacity-30"
                      title="Move down"
                    >
                      <ChevronDown className="h-4 w-4" />
                    </button>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-[var(--foreground)]">{plan.name}</span>
                    {plan.is_recommended ? <Badge tone="accent">Recommended</Badge> : null}
                    {plan.is_featured ? <Badge color="#9333ea">Popular</Badge> : null}
                    {plan.badge ? <Badge>{plan.badge}</Badge> : null}
                  </div>
                  <div className="text-xs text-[var(--muted)]">{plan.slug}</div>
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{money(plan)}</td>
                <td className="px-4 py-3 capitalize text-[var(--foreground-secondary)]">{plan.visibility}</td>
                <td className="px-4 py-3">
                  {plan.is_archived ? (
                    <Badge color="var(--muted)">Archived</Badge>
                  ) : plan.is_active ? (
                    <Badge color="var(--success)">Active</Badge>
                  ) : (
                    <Badge color="var(--warning)">Inactive</Badge>
                  )}
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{plan.feature_count}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Link href={`/platform/plans/${plan.id}`}>
                      <Button variant="ghost" size="sm" title="Edit">
                        <Pencil className="h-4 w-4" />
                      </Button>
                    </Link>
                    <Button
                      variant="ghost"
                      size="sm"
                      title="Duplicate"
                      onClick={() => act(() => platformApi.plans.duplicate(plan.id), "Plan duplicated.")}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                    {plan.is_archived ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        title="Unarchive"
                        onClick={() => act(() => platformApi.plans.unarchive(plan.id), "Plan unarchived.")}
                      >
                        <ArchiveRestore className="h-4 w-4" />
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        title="Archive"
                        onClick={() => act(() => platformApi.plans.archive(plan.id), "Plan archived.")}
                      >
                        <Archive className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      title={plan.is_active ? "Deactivate" : "Activate"}
                      onClick={() =>
                        act(
                          () =>
                            plan.is_active
                              ? platformApi.plans.deactivate(plan.id)
                              : platformApi.plans.activate(plan.id),
                          plan.is_active ? "Plan deactivated." : "Plan activated.",
                        )
                      }
                    >
                      <Power className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(plan)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={creating} title="New plan" onClose={() => setCreating(false)}>
        <div className="space-y-3">
          <Input label="Plan name" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="e.g. Professional" />
          <Input
            label="Monthly price"
            type="number"
            value={newPrice}
            onChange={(e) => setNewPrice(e.target.value)}
          />
          <p className="text-xs text-[var(--muted)]">
            A slug is generated automatically. You can configure features, limits and pricing after creating.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={create}>
              Create plan
            </Button>
          </div>
        </div>
      </Modal>

      <Modal open={importing} title="Import plans" onClose={() => setImporting(false)}>
        <div className="space-y-3">
          <p className="text-xs text-[var(--muted)]">
            Paste a JSON array of plans (the same shape produced by Export). Matching slugs are updated in place;
            everything else is created.
          </p>
          <Textarea
            value={importJson}
            onChange={(e) => setImportJson(e.target.value)}
            placeholder={'[ { "name": "Professional", ... } ]'}
            className="min-h-[220px] font-mono text-xs"
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setImporting(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={runImport} disabled={!importJson.trim()}>
              Import
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
