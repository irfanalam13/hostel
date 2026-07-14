"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Modal, Select, Table, Textarea, useToast } from "@hostel/ui";
import { TrendingDown, Undo2, Wrench } from "lucide-react";

import { inventoryApi } from "../api/inventory.api";
import { ASSET_STATUSES } from "../constants";
import type { Asset, AssetLifecycleEvent } from "../types/inventory.types";
import { ReadField, StatusBadge, cardClass, formatMoney } from "./primitives";

export function AssetDetail({ assetId }: { assetId: string }) {
  const toast = useToast();
  const router = useRouter();

  const [asset, setAsset] = useState<Asset | null>(null);
  const [history, setHistory] = useState<AssetLifecycleEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const [statusOpen, setStatusOpen] = useState(false);
  const [statusForm, setStatusForm] = useState({ status: "in_maintenance", note: "", cost: "0" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, h] = await Promise.all([
        inventoryApi.assets.retrieve(assetId),
        inventoryApi.assets.history(assetId),
      ]);
      setAsset(a);
      setHistory(h);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [assetId, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true);
    try {
      await fn();
      toast.success(ok);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const submitStatus = async () => {
    if (!asset) return;
    await act(() => inventoryApi.assets.changeStatus(asset.id, statusForm), "Status updated.");
    setStatusOpen(false);
  };

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!asset) return <div className="text-sm text-[var(--muted)]">Asset not found.</div>;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">{asset.name}</h2>
          <span className="font-mono text-xs text-[var(--muted)]">{asset.asset_tag}</span>
          <StatusBadge status={asset.status} />
        </div>
        <div className="flex flex-wrap gap-2">
          {asset.status === "assigned" ? (
            <Button variant="secondary" size="sm" loading={busy} onClick={() => act(() => inventoryApi.assets.returnAsset(asset.id), "Asset returned.")}>
              <Undo2 className="h-4 w-4" /> Return
            </Button>
          ) : null}
          <Button variant="secondary" size="sm" onClick={() => { setStatusForm({ status: "in_maintenance", note: "", cost: "0" }); setStatusOpen(true); }}>
            <Wrench className="h-4 w-4" /> Change status
          </Button>
          {asset.accounting_asset ? (
            <Button variant="ghost" size="sm" loading={busy} onClick={() => act(() => inventoryApi.assets.depreciate(asset.id), "Depreciation posted.")}>
              <TrendingDown className="h-4 w-4" /> Depreciate
            </Button>
          ) : null}
        </div>
      </div>

      <div className={`${cardClass} grid grid-cols-2 gap-4 sm:grid-cols-4`}>
        <ReadField label="Category" value={asset.category_name} />
        <ReadField label="Vendor" value={asset.vendor_name} />
        <ReadField label="Serial" value={asset.serial_number} />
        <ReadField label="Condition" value={<StatusBadge status={asset.condition} />} />
        <ReadField label="Purchase cost" value={formatMoney(asset.purchase_cost)} />
        <ReadField label="Purchase date" value={asset.purchase_date} />
        <ReadField label="Warranty until" value={asset.warranty_until} />
        <ReadField label="Department" value={asset.department} />
      </div>

      <div className={cardClass}>
        <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">Lifecycle History</h3>
        {history.length === 0 ? (
          <p className="py-4 text-center text-sm text-[var(--muted)]">No lifecycle events yet.</p>
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                <th className="px-4 py-3 font-medium">Stage</th>
                <th className="px-4 py-3 font-medium">Note</th>
                <th className="px-4 py-3 font-medium text-right">Cost</th>
                <th className="px-4 py-3 font-medium text-right">When</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-4 py-3"><StatusBadge status={h.stage} /></td>
                  <td className="px-4 py-3 text-[var(--foreground-secondary)]">{h.note || "—"}</td>
                  <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatMoney(h.cost)}</td>
                  <td className="px-4 py-3 text-right text-[var(--muted)]">{new Date(h.occurred_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <Modal open={statusOpen} title="Change asset status" onClose={() => setStatusOpen(false)}>
        <div className="space-y-3">
          <Select label="Status" value={statusForm.status} onChange={(e) => setStatusForm((f) => ({ ...f, status: e.target.value }))} options={ASSET_STATUSES} />
          <Textarea label="Note" value={statusForm.note} onChange={(e) => setStatusForm((f) => ({ ...f, note: e.target.value }))} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setStatusOpen(false)}>Cancel</Button>
            <Button loading={busy} onClick={submitStatus}>Save</Button>
          </div>
        </div>
      </Modal>

      <div>
        <Button variant="ghost" size="sm" onClick={() => router.push("/inventory/assets")}>← Back to assets</Button>
      </div>
    </div>
  );
}
