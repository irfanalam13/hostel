"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Button, EmptyState, Input, Modal, Select, Table, useConfirm, useToast } from "@hostel/ui";
import { Pencil, Plus, Trash2 } from "lucide-react";

import { inventoryApi } from "../api/inventory.api";
import type { Brand, ItemCategory, UnitOfMeasure } from "../types/inventory.types";
import { Badge, cardClass } from "./primitives";

type Tab = "categories" | "brands" | "units";

export function CategoryManager() {
  const toast = useToast();
  const confirm = useConfirm();
  const [tab, setTab] = useState<Tab>("categories");

  const [categories, setCategories] = useState<ItemCategory[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [units, setUnits] = useState<UnitOfMeasure[]>([]);
  const [loading, setLoading] = useState(true);

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ItemCategory | Brand | null>(null);
  const [form, setForm] = useState({ name: "", parent: "", manufacturer: "", symbol: "" });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [c, b, u] = await Promise.all([
        inventoryApi.categories.list(),
        inventoryApi.brands.list(),
        inventoryApi.units.list(),
      ]);
      setCategories(c);
      setBrands(b);
      setUnits(u);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const startCreate = () => {
    setEditing(null);
    setForm({ name: "", parent: "", manufacturer: "", symbol: "" });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.name.trim()) {
      toast.error("A name is required.");
      return;
    }
    setBusy(true);
    try {
      if (tab === "categories") {
        await inventoryApi.categories.create({ name: form.name.trim(), parent: form.parent || null });
      } else if (tab === "brands") {
        await inventoryApi.brands.create({ name: form.name.trim(), manufacturer: form.manufacturer });
      } else {
        await inventoryApi.units.create({ name: form.name.trim(), symbol: form.symbol });
      }
      toast.success("Created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const removeRow = async (label: string, fn: () => Promise<unknown>) => {
    const yes = await confirm({ title: "Delete", message: `Delete "${label}"?`, danger: true, confirmText: "Delete" });
    if (!yes) return;
    try {
      await fn();
      toast.success("Deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "categories", label: "Categories" },
    { id: "brands", label: "Brands" },
    { id: "units", label: "Units" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-1.5">
          {tabs.map((tb) => (
            <button
              key={tb.id}
              onClick={() => setTab(tb.id)}
              className={`rounded-xl px-3 py-1.5 text-sm font-medium transition ${
                tab === tb.id
                  ? "bg-[var(--accent)] text-white"
                  : "text-[var(--foreground-secondary)] hover:bg-[var(--background-secondary)]"
              }`}
            >
              {tb.label}
            </button>
          ))}
        </div>
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : (
        <div className={cardClass}>
          {tab === "categories" && (
            categories.length === 0 ? (
              <EmptyState title="No categories" description="Group your items into categories." />
            ) : (
              <Table>
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                    <th className="px-4 py-3 font-medium">Name</th>
                    <th className="px-4 py-3 font-medium">Parent</th>
                    <th className="px-4 py-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {categories.map((c) => (
                    <tr key={c.id} className="border-b border-[var(--border)] last:border-0">
                      <td className="px-4 py-3 text-[var(--foreground)]">
                        {c.name} {c.is_system ? <Badge>System</Badge> : null}
                      </td>
                      <td className="px-4 py-3 text-[var(--foreground-secondary)]">{c.parent_name || "—"}</td>
                      <td className="px-4 py-3 text-right">
                        {!c.is_system && (
                          <Button variant="ghost" size="sm" onClick={() => removeRow(c.name, () => inventoryApi.categories.remove(c.id))}>
                            <Trash2 className="h-4 w-4 text-[var(--error)]" />
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )
          )}

          {tab === "brands" && (
            brands.length === 0 ? (
              <EmptyState title="No brands" description="Track manufacturers and brands." />
            ) : (
              <Table>
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                    <th className="px-4 py-3 font-medium">Name</th>
                    <th className="px-4 py-3 font-medium">Manufacturer</th>
                    <th className="px-4 py-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {brands.map((b) => (
                    <tr key={b.id} className="border-b border-[var(--border)] last:border-0">
                      <td className="px-4 py-3 text-[var(--foreground)]">{b.name}</td>
                      <td className="px-4 py-3 text-[var(--foreground-secondary)]">{b.manufacturer || "—"}</td>
                      <td className="px-4 py-3 text-right">
                        <Button variant="ghost" size="sm" onClick={() => removeRow(b.name, () => inventoryApi.brands.remove(b.id))}>
                          <Trash2 className="h-4 w-4 text-[var(--error)]" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )
          )}

          {tab === "units" && (
            <Table>
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Symbol</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {units.map((u) => (
                  <tr key={u.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-4 py-3 text-[var(--foreground)]">{u.name} {u.is_system ? <Badge>System</Badge> : null}</td>
                    <td className="px-4 py-3 text-[var(--foreground-secondary)]">{u.symbol || "—"}</td>
                    <td className="px-4 py-3 text-right">
                      {!u.is_system && (
                        <Button variant="ghost" size="sm" onClick={() => removeRow(u.name, () => inventoryApi.units.remove(u.id))}>
                          <Trash2 className="h-4 w-4 text-[var(--error)]" />
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </div>
      )}

      <Modal open={open} title={`New ${tab.slice(0, -1)}`} onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <Input label="Name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
          {tab === "categories" && (
            <Select label="Parent (optional)" value={form.parent} onChange={(e) => setForm((f) => ({ ...f, parent: e.target.value }))}>
              <option value="">Top level</option>
              {categories.filter((c) => !c.parent).map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </Select>
          )}
          {tab === "brands" && (
            <Input label="Manufacturer" value={form.manufacturer} onChange={(e) => setForm((f) => ({ ...f, manufacturer: e.target.value }))} />
          )}
          {tab === "units" && (
            <Input label="Symbol" value={form.symbol} onChange={(e) => setForm((f) => ({ ...f, symbol: e.target.value }))} />
          )}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button loading={busy} onClick={submit}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
