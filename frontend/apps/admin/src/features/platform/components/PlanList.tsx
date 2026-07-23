"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button, Input, Modal, Table, EmptyState, useToast, useConfirm } from "@hostel/ui";
import {
  Archive,
  ArchiveRestore,
  Copy,
  Download,
  Pencil,
  Plus,
  Power,
  Trash2,
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

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setPlans(await platformApi.plans.list(search));
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
        <Button onClick={() => setCreating(true)}>
          <Plus className="h-4 w-4" /> New plan
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : plans.length === 0 ? (
        <EmptyState title="No plans yet" description="Create your first subscription plan to get started." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Plan</th>
              <th className="px-4 py-3 font-medium">Price</th>
              <th className="px-4 py-3 font-medium">Visibility</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Features</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((plan) => (
              <tr key={plan.id} className="border-b border-[var(--border)] last:border-0">
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
    </div>
  );
}
