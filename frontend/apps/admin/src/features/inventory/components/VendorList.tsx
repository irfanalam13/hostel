"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Button, EmptyState, Input, Modal, Table, useConfirm, useToast } from "@hostel/ui";
import { Pencil, Plus, Trash2 } from "lucide-react";

import { inventoryApi } from "../api/inventory.api";
import type { Vendor } from "../types/inventory.types";
import { Badge } from "./primitives";

type VendorForm = {
  company_name: string;
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  tax_number: string;
  payment_terms: string;
};

const empty: VendorForm = {
  company_name: "",
  contact_person: "",
  email: "",
  phone: "",
  address: "",
  tax_number: "",
  payment_terms: "",
};

export function VendorList() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Vendor | null>(null);
  const [form, setForm] = useState<VendorForm>(empty);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await inventoryApi.vendors.list({ search }));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [search, toast]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  const set = (patch: Partial<VendorForm>) => setForm((f) => ({ ...f, ...patch }));

  const startCreate = () => {
    setEditing(null);
    setForm(empty);
    setOpen(true);
  };
  const startEdit = (v: Vendor) => {
    setEditing(v);
    setForm({
      company_name: v.company_name,
      contact_person: v.contact_person,
      email: v.email,
      phone: v.phone,
      address: v.address,
      tax_number: v.tax_number,
      payment_terms: v.payment_terms,
    });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.company_name.trim()) return toast.error("Company name is required.");
    setBusy(true);
    try {
      if (editing) await inventoryApi.vendors.update(editing.id, form);
      else await inventoryApi.vendors.create(form);
      toast.success(editing ? "Vendor updated." : "Vendor created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (v: Vendor) => {
    const yes = await confirm({ title: "Archive vendor", message: `Archive "${v.company_name}"?`, danger: true, confirmText: "Archive" });
    if (!yes) return;
    try {
      await inventoryApi.vendors.remove(v.id);
      toast.success("Vendor archived.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex-1 min-w-[200px]">
          <Input label="Search" placeholder="Company, contact, email…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New vendor
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No vendors" description="Add suppliers to raise purchase orders." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Vendor</th>
              <th className="px-4 py-3 font-medium">Contact</th>
              <th className="px-4 py-3 font-medium">Phone</th>
              <th className="px-4 py-3 font-medium">Terms</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((v) => (
              <tr key={v.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium text-[var(--foreground)]">{v.company_name}</div>
                  <div className="font-mono text-xs text-[var(--muted)]">{v.vendor_code}</div>
                  {v.is_blacklisted ? <Badge color="var(--error)">Blacklisted</Badge> : null}
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{v.contact_person || "—"}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{v.phone || "—"}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{v.payment_terms || "—"}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" onClick={() => startEdit(v)}><Pencil className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="sm" onClick={() => remove(v)}><Trash2 className="h-4 w-4 text-[var(--error)]" /></Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title={editing ? "Edit vendor" : "New vendor"} onClose={() => setOpen(false)}>
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          <Input label="Company name" value={form.company_name} onChange={(e) => set({ company_name: e.target.value })} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Contact person" value={form.contact_person} onChange={(e) => set({ contact_person: e.target.value })} />
            <Input label="Phone" value={form.phone} onChange={(e) => set({ phone: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Email" value={form.email} onChange={(e) => set({ email: e.target.value })} />
            <Input label="Tax / PAN" value={form.tax_number} onChange={(e) => set({ tax_number: e.target.value })} />
          </div>
          <Input label="Address" value={form.address} onChange={(e) => set({ address: e.target.value })} />
          <Input label="Payment terms" value={form.payment_terms} onChange={(e) => set({ payment_terms: e.target.value })} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button loading={busy} onClick={submit}>{editing ? "Save" : "Create"}</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
