"use client";

import React, { useEffect, useState } from "react";
import { Button, EmptyState, Modal, Select, Table, Textarea, useToast } from "@hostel/ui";
import { History } from "lucide-react";
import { platformApi } from "../api/platform.api";
import type { HostelSubscription, Plan, SubscriptionEvent } from "../types/platform.types";
import { Badge } from "./primitives";

const STATUS_TONE: Record<string, string> = {
  active: "var(--success)",
  trial: "var(--info)",
  expired: "var(--warning)",
  suspended: "var(--error)",
  pending: "var(--muted)",
};

export function SubscriptionsPanel() {
  const toast = useToast();
  const [rows, setRows] = useState<HostelSubscription[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [assignFor, setAssignFor] = useState<HostelSubscription | null>(null);
  const [planId, setPlanId] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [historyFor, setHistoryFor] = useState<HostelSubscription | null>(null);
  const [history, setHistory] = useState<SubscriptionEvent[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      const [subs, planList] = await Promise.all([
        platformApi.subscriptions.list(),
        platformApi.plans.list(),
      ]);
      setRows(subs);
      setPlans(planList);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openAssign = (row: HostelSubscription) => {
    setAssignFor(row);
    setPlanId(row.plan || "");
    setReason("");
  };

  const assign = async () => {
    if (!assignFor || !planId) return;
    setBusy(true);
    try {
      await platformApi.subscriptions.assign(assignFor.id, planId, reason);
      toast.success(`Plan assigned to ${assignFor.name}.`);
      setAssignFor(null);
      await load();
    } catch (e) {
      toast.error((e as Error).message, "Assign failed");
    } finally {
      setBusy(false);
    }
  };

  const openHistory = async (row: HostelSubscription) => {
    setHistoryFor(row);
    setHistory([]);
    try {
      setHistory(await platformApi.subscriptions.history(row.id));
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading subscriptions…</div>;

  return (
    <div className="space-y-4">
      {rows.length === 0 ? (
        <EmptyState title="No workspaces yet" description="Hostels appear here once created; assign them a plan." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Hostel</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Plan</th>
              <th className="px-4 py-3 font-medium text-right">MRR</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium text-[var(--foreground)]">{r.name}</div>
                  <div className="text-xs text-[var(--muted)]">{r.code}</div>
                </td>
                <td className="px-4 py-3">
                  <Badge color={STATUS_TONE[r.status] || "var(--muted)"}>{r.status}</Badge>
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.plan_name || "—"}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">Rs. {r.mrr}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" onClick={() => openHistory(r)} title="History">
                      <History className="h-4 w-4" />
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => openAssign(r)}>
                      Change plan
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={!!assignFor} title={`Assign plan · ${assignFor?.name ?? ""}`} onClose={() => setAssignFor(null)}>
        <div className="space-y-3">
          <Select
            label="Plan"
            placeholder="Select a plan"
            value={planId}
            onChange={(e) => setPlanId(e.target.value)}
            options={plans.filter((p) => !p.is_archived).map((p) => ({ value: p.id, label: p.name }))}
          />
          <Textarea
            label="Reason (optional)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. upgraded to Enterprise for onboarding"
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setAssignFor(null)}>Cancel</Button>
            <Button loading={busy} disabled={!planId} onClick={assign}>Assign plan</Button>
          </div>
        </div>
      </Modal>

      <Modal open={!!historyFor} title={`History · ${historyFor?.name ?? ""}`} onClose={() => setHistoryFor(null)}>
        {history.length === 0 ? (
          <div className="text-sm text-[var(--muted)]">No subscription changes recorded.</div>
        ) : (
          <div className="space-y-2">
            {history.map((e) => (
              <div key={e.id} className="rounded-xl border border-[var(--border)] px-4 py-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium capitalize text-[var(--foreground)]">{e.kind}</span>
                  <span className="text-xs text-[var(--muted)]">{new Date(e.created_at).toLocaleString()}</span>
                </div>
                <div className="text-xs text-[var(--muted)]">
                  {e.from_plan_name ? `${e.from_plan_name} → ` : ""}
                  {e.to_plan_name || "—"} · Rs. {e.mrr_amount}/mo
                  {e.actor_name ? ` · by ${e.actor_name}` : ""}
                </div>
                {e.reason ? <div className="mt-1 text-xs text-[var(--foreground-secondary)]">{e.reason}</div> : null}
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
}
