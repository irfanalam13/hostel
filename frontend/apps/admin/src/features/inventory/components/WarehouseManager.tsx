"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Button, EmptyState, Input, Modal, Select, Table, useConfirm, useToast } from "@hostel/ui";
import { Plus, Trash2 } from "lucide-react";

import { inventoryApi } from "../api/inventory.api";
import { WAREHOUSE_TYPES } from "../constants";
import type { StorageLocation, Warehouse } from "../types/inventory.types";
import { Badge, cardClass } from "./primitives";

export function WarehouseManager() {
  const toast = useToast();
  const confirm = useConfirm();

  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [locations, setLocations] = useState<StorageLocation[]>([]);
  const [loading, setLoading] = useState(true);

  const [whOpen, setWhOpen] = useState(false);
  const [whForm, setWhForm] = useState({ name: "", warehouse_type: "main", capacity: "0" });
  const [locOpen, setLocOpen] = useState(false);
  const [locForm, setLocForm] = useState({ warehouse: "", name: "", zone: "", rack: "", shelf: "", bin: "" });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [w, l] = await Promise.all([inventoryApi.warehouses.list(), inventoryApi.locations.list()]);
      setWarehouses(w);
      setLocations(l);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const submitWh = async () => {
    if (!whForm.name.trim()) return toast.error("A name is required.");
    setBusy(true);
    try {
      await inventoryApi.warehouses.create({ ...whForm, capacity: Number(whForm.capacity) });
      toast.success("Warehouse created.");
      setWhOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const submitLoc = async () => {
    if (!locForm.warehouse || !locForm.name.trim()) return toast.error("Warehouse and name are required.");
    setBusy(true);
    try {
      await inventoryApi.locations.create(locForm);
      toast.success("Location created.");
      setLocOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const removeWh = async (w: Warehouse) => {
    const yes = await confirm({ title: "Delete warehouse", message: `Delete "${w.name}"?`, danger: true, confirmText: "Delete" });
    if (!yes) return;
    try {
      await inventoryApi.warehouses.remove(w.id);
      toast.success("Deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[var(--foreground-secondary)]">Warehouses</h3>
        <Button size="sm" onClick={() => { setWhForm({ name: "", warehouse_type: "main", capacity: "0" }); setWhOpen(true); }}>
          <Plus className="h-4 w-4" /> New warehouse
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : warehouses.length === 0 ? (
        <EmptyState title="No warehouses" description="Create a warehouse to store stock." />
      ) : (
        <div className={cardClass}>
          <Table>
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium text-right">Capacity</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {warehouses.map((w) => (
                <tr key={w.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-4 py-3 text-[var(--foreground)]">
                    {w.name} {w.is_default ? <Badge tone="accent">Default</Badge> : null}
                  </td>
                  <td className="px-4 py-3 text-[var(--foreground-secondary)]">{w.warehouse_type}</td>
                  <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{w.capacity || "—"}</td>
                  <td className="px-4 py-3 text-right">
                    {!w.is_default && (
                      <Button variant="ghost" size="sm" onClick={() => removeWh(w)}>
                        <Trash2 className="h-4 w-4 text-[var(--error)]" />
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}

      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[var(--foreground-secondary)]">Storage Locations</h3>
        <Button size="sm" variant="secondary" onClick={() => { setLocForm({ warehouse: warehouses[0]?.id ?? "", name: "", zone: "", rack: "", shelf: "", bin: "" }); setLocOpen(true); }}>
          <Plus className="h-4 w-4" /> New location
        </Button>
      </div>
      {locations.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">No storage locations yet.</p>
      ) : (
        <div className={cardClass}>
          <Table>
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                <th className="px-4 py-3 font-medium">Location</th>
                <th className="px-4 py-3 font-medium">Warehouse</th>
                <th className="px-4 py-3 font-medium">Bin path</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {locations.map((l) => (
                <tr key={l.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-4 py-3 text-[var(--foreground)]">{l.name}</td>
                  <td className="px-4 py-3 text-[var(--foreground-secondary)]">{l.warehouse_name}</td>
                  <td className="px-4 py-3 text-[var(--muted)] text-xs">
                    {[l.zone, l.rack, l.shelf, l.bin].filter(Boolean).join(" · ") || "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button variant="ghost" size="sm" onClick={async () => { await inventoryApi.locations.remove(l.id); load(); }}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}

      <Modal open={whOpen} title="New warehouse" onClose={() => setWhOpen(false)}>
        <div className="space-y-3">
          <Input label="Name" value={whForm.name} onChange={(e) => setWhForm((f) => ({ ...f, name: e.target.value }))} />
          <div className="grid grid-cols-2 gap-3">
            <Select label="Type" value={whForm.warehouse_type} onChange={(e) => setWhForm((f) => ({ ...f, warehouse_type: e.target.value }))} options={WAREHOUSE_TYPES} />
            <Input label="Capacity" type="number" value={whForm.capacity} onChange={(e) => setWhForm((f) => ({ ...f, capacity: e.target.value }))} />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setWhOpen(false)}>Cancel</Button>
            <Button loading={busy} onClick={submitWh}>Create</Button>
          </div>
        </div>
      </Modal>

      <Modal open={locOpen} title="New storage location" onClose={() => setLocOpen(false)}>
        <div className="space-y-3">
          <Select label="Warehouse" value={locForm.warehouse} onChange={(e) => setLocForm((f) => ({ ...f, warehouse: e.target.value }))}>
            {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </Select>
          <Input label="Name" value={locForm.name} onChange={(e) => setLocForm((f) => ({ ...f, name: e.target.value }))} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Zone" value={locForm.zone} onChange={(e) => setLocForm((f) => ({ ...f, zone: e.target.value }))} />
            <Input label="Rack" value={locForm.rack} onChange={(e) => setLocForm((f) => ({ ...f, rack: e.target.value }))} />
            <Input label="Shelf" value={locForm.shelf} onChange={(e) => setLocForm((f) => ({ ...f, shelf: e.target.value }))} />
            <Input label="Bin" value={locForm.bin} onChange={(e) => setLocForm((f) => ({ ...f, bin: e.target.value }))} />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setLocOpen(false)}>Cancel</Button>
            <Button loading={busy} onClick={submitLoc}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
