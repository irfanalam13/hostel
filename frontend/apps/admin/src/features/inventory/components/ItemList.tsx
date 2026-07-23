"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Button,
  EmptyState,
  Input,
  Modal,
  Select,
  Table,
  Textarea,
  useConfirm,
  useToast,
} from "@hostel/ui";
import { ArrowLeftRight, Eye, Pencil, Plus, Sliders, Trash2 } from "lucide-react";

import { inventoryApi } from "../api/inventory.api";
import { ITEM_TYPES } from "../constants";
import type { Item, ItemCategory, Warehouse } from "../types/inventory.types";
import { StatusBadge, formatMoney, formatQty } from "./primitives";

type ItemForm = {
  name: string;
  category: string;
  item_type: Item["item_type"];
  description: string;
  purchase_price: string;
  selling_price: string;
  reorder_level: string;
  min_stock: string;
  max_stock: string;
  track_batch: boolean;
  track_serial: boolean;
  track_expiry: boolean;
};

const emptyItem: ItemForm = {
  name: "",
  category: "",
  item_type: "consumable",
  description: "",
  purchase_price: "0",
  selling_price: "0",
  reorder_level: "0",
  min_stock: "0",
  max_stock: "0",
  track_batch: false,
  track_serial: false,
  track_expiry: false,
};

function stockTone(item: Item): string {
  const oh = parseFloat(item.on_hand || "0");
  const reorder = parseFloat(item.reorder_level || "0");
  if (oh <= 0) return "out_of_stock";
  if (reorder > 0 && oh <= reorder) return "low";
  return "available";
}

export function ItemList() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<Item[]>([]);
  const [categories, setCategories] = useState<ItemCategory[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Item | null>(null);
  const [form, setForm] = useState<ItemForm>(emptyItem);
  const [busy, setBusy] = useState(false);

  // Stock adjust / transfer modals
  const [stockItem, setStockItem] = useState<Item | null>(null);
  const [stockMode, setStockMode] = useState<"adjust" | "transfer">("adjust");
  const [stockForm, setStockForm] = useState({ warehouse: "", to_warehouse: "", quantity: "0", reason: "" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await inventoryApi.items.list({ search, item_type: typeFilter || undefined }));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [search, typeFilter, toast]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  useEffect(() => {
    inventoryApi.categories.list().then(setCategories).catch(() => {});
    inventoryApi.warehouses.list().then(setWarehouses).catch(() => {});
  }, []);

  const set = (patch: Partial<ItemForm>) => setForm((f) => ({ ...f, ...patch }));

  const startCreate = () => {
    setEditing(null);
    setForm({ ...emptyItem, category: categories[0]?.id ?? "" });
    setOpen(true);
  };
  const startEdit = (x: Item) => {
    setEditing(x);
    setForm({
      name: x.name,
      category: x.category ?? "",
      item_type: x.item_type,
      description: x.description,
      purchase_price: x.purchase_price,
      selling_price: x.selling_price,
      reorder_level: x.reorder_level,
      min_stock: x.min_stock,
      max_stock: x.max_stock,
      track_batch: x.track_batch,
      track_serial: x.track_serial,
      track_expiry: x.track_expiry,
    });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.name.trim()) {
      toast.error("A name is required.");
      return;
    }
    setBusy(true);
    try {
      const body = { ...form, category: form.category || undefined };
      if (editing) await inventoryApi.items.update(editing.id, body);
      else await inventoryApi.items.create(body);
      toast.success(editing ? "Item updated." : "Item created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (x: Item) => {
    const yes = await confirm({
      title: "Archive item",
      message: `Archive "${x.name}"? Stock history is retained.`,
      danger: true,
      confirmText: "Archive",
    });
    if (!yes) return;
    try {
      await inventoryApi.items.remove(x.id);
      toast.success("Item archived.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const openStock = (x: Item, mode: "adjust" | "transfer") => {
    setStockItem(x);
    setStockMode(mode);
    setStockForm({ warehouse: warehouses[0]?.id ?? "", to_warehouse: "", quantity: "0", reason: "" });
  };

  const submitStock = async () => {
    if (!stockItem) return;
    setBusy(true);
    try {
      if (stockMode === "adjust") {
        await inventoryApi.items.adjustStock(stockItem.id, {
          warehouse: stockForm.warehouse,
          target_quantity: stockForm.quantity,
          reason: stockForm.reason,
        });
        toast.success("Stock adjusted.");
      } else {
        await inventoryApi.items.transfer(stockItem.id, {
          from_warehouse: stockForm.warehouse,
          to_warehouse: stockForm.to_warehouse,
          quantity: stockForm.quantity,
          note: stockForm.reason,
        });
        toast.success("Stock transferred.");
      }
      setStockItem(null);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex-1 min-w-[200px]">
          <Input
            label="Search"
            placeholder="Name, code, SKU or barcode…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select
          label="Type"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          options={[{ value: "", label: "All types" }, ...ITEM_TYPES]}
        />
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New item
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No items" description="Add items to your catalog to start tracking stock." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Item</th>
              <th className="px-4 py-3 font-medium">Category</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium text-right">On hand</th>
              <th className="px-4 py-3 font-medium text-right">Avg cost</th>
              <th className="px-4 py-3 font-medium">Stock</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((x) => (
              <tr key={x.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium text-[var(--foreground)]">{x.name}</div>
                  <div className="font-mono text-xs text-[var(--muted)]">{x.item_code}</div>
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{x.category_name || "—"}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{x.item_type.replace(/_/g, " ")}</td>
                <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">{formatQty(x.on_hand)}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatMoney(x.average_cost)}</td>
                <td className="px-4 py-3"><StatusBadge status={stockTone(x)} /></td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Adjust stock" onClick={() => openStock(x, "adjust")}>
                      <Sliders className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Transfer" onClick={() => openStock(x, "transfer")}>
                      <ArrowLeftRight className="h-4 w-4" />
                    </Button>
                    <Link href={`/inventory/items/${x.id}`} title="View">
                      <Button variant="ghost" size="sm"><Eye className="h-4 w-4" /></Button>
                    </Link>
                    <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(x)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Archive" onClick={() => remove(x)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {/* Create / edit modal */}
      <Modal open={open} title={editing ? "Edit item" : "New item"} onClose={() => setOpen(false)}>
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
            <Select label="Category" value={form.category} onChange={(e) => set({ category: e.target.value })} placeholder="Uncategorized">
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.parent_name ? `${c.parent_name} / ${c.name}` : c.name}
                </option>
              ))}
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Select label="Type" value={form.item_type} onChange={(e) => set({ item_type: e.target.value as Item["item_type"] })} options={ITEM_TYPES} />
            <Input label="Reorder level" type="number" value={form.reorder_level} onChange={(e) => set({ reorder_level: e.target.value })} />
          </div>
          <Textarea label="Description" value={form.description} onChange={(e) => set({ description: e.target.value })} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Purchase price" type="number" value={form.purchase_price} onChange={(e) => set({ purchase_price: e.target.value })} />
            <Input label="Selling price" type="number" value={form.selling_price} onChange={(e) => set({ selling_price: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Min stock" type="number" value={form.min_stock} onChange={(e) => set({ min_stock: e.target.value })} />
            <Input label="Max stock" type="number" value={form.max_stock} onChange={(e) => set({ max_stock: e.target.value })} />
          </div>
          <div className="flex flex-wrap gap-4 text-sm text-[var(--foreground-secondary)]">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={form.track_batch} onChange={(e) => set({ track_batch: e.target.checked })} /> Track batch
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={form.track_serial} onChange={(e) => set({ track_serial: e.target.checked })} /> Track serial
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={form.track_expiry} onChange={(e) => set({ track_expiry: e.target.checked })} /> Track expiry
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button loading={busy} onClick={submit}>{editing ? "Save" : "Create"}</Button>
          </div>
        </div>
      </Modal>

      {/* Stock adjust / transfer modal */}
      <Modal
        open={!!stockItem}
        title={stockMode === "adjust" ? `Adjust stock — ${stockItem?.name ?? ""}` : `Transfer stock — ${stockItem?.name ?? ""}`}
        onClose={() => setStockItem(null)}
      >
        <div className="space-y-3">
          <Select
            label={stockMode === "transfer" ? "From warehouse" : "Warehouse"}
            value={stockForm.warehouse}
            onChange={(e) => setStockForm((f) => ({ ...f, warehouse: e.target.value }))}
          >
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </Select>
          {stockMode === "transfer" ? (
            <Select
              label="To warehouse"
              value={stockForm.to_warehouse}
              onChange={(e) => setStockForm((f) => ({ ...f, to_warehouse: e.target.value }))}
            >
              <option value="">Select…</option>
              {warehouses.map((w) => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </Select>
          ) : null}
          <Input
            label={stockMode === "adjust" ? "Set on-hand to" : "Quantity to move"}
            type="number"
            value={stockForm.quantity}
            onChange={(e) => setStockForm((f) => ({ ...f, quantity: e.target.value }))}
          />
          <Input
            label="Reason / note"
            value={stockForm.reason}
            onChange={(e) => setStockForm((f) => ({ ...f, reason: e.target.value }))}
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setStockItem(null)}>Cancel</Button>
            <Button loading={busy} onClick={submitStock}>Confirm</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
