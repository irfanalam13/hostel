"use client";

import React, { useCallback, useEffect, useState } from "react";
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
import { Lock, Pencil, Plus, Trash2, Users } from "lucide-react";

import { financeApi } from "../api/finance.api";
import { FEE_RECURRENCES, LATE_FINE_TYPES } from "../constants";
import type {
  FeeAssignment,
  FeeCategory,
  FeeStructure,
  ResidentOption,
} from "../types/finance.types";
import { Badge, StatusBadge, formatMoney } from "./primitives";
import { ResidentPicker } from "./ResidentPicker";

const TABS = [
  { id: "categories", label: "Categories" },
  { id: "structures", label: "Structures" },
  { id: "assignments", label: "Assignments" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export function FeeManager() {
  const [tab, setTab] = useState<TabId>("categories");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-1 border-b border-[var(--border)]">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition ${
              t.id === tab
                ? "border-[var(--accent)] text-[var(--foreground)]"
                : "border-transparent text-[var(--muted)] hover:text-[var(--foreground)]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "categories" && <CategoriesTab />}
      {tab === "structures" && <StructuresTab />}
      {tab === "assignments" && <AssignmentsTab />}
    </div>
  );
}

/* ------------------------------- Categories ------------------------------ */

type CategoryForm = { name: string; code: string; description: string; is_active: boolean };
const emptyCategory: CategoryForm = { name: "", code: "", description: "", is_active: true };

function CategoriesTab() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<FeeCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<FeeCategory | null>(null);
  const [form, setForm] = useState<CategoryForm>(emptyCategory);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await financeApi.feeCategories.list());
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (patch: Partial<CategoryForm>) => setForm((f) => ({ ...f, ...patch }));

  const startCreate = () => {
    setEditing(null);
    setForm(emptyCategory);
    setOpen(true);
  };
  const startEdit = (c: FeeCategory) => {
    setEditing(c);
    setForm({ name: c.name, code: c.code, description: c.description, is_active: c.is_active });
    setOpen(true);
  };

  const submit = async () => {
    setBusy(true);
    try {
      if (editing) await financeApi.feeCategories.update(editing.id, form);
      else await financeApi.feeCategories.create(form);
      toast.success(editing ? "Category updated." : "Category created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (c: FeeCategory) => {
    const yes = await confirm({
      title: "Delete category",
      message: `Delete "${c.name}"?`,
      danger: true,
      confirmText: "Delete",
    });
    if (!yes) return;
    try {
      await financeApi.feeCategories.remove(c.id);
      toast.success("Category deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New category
        </Button>
      </div>
      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No fee categories" description="Create categories to group fee structures." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Code</th>
              <th className="px-4 py-3 font-medium">Active</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-2 font-medium text-[var(--foreground)]">
                    {c.name}
                    {c.is_system ? (
                      <Badge tone="accent">
                        <Lock className="h-3 w-3" /> System
                      </Badge>
                    ) : null}
                  </span>
                  {c.description ? <div className="text-xs text-[var(--muted)]">{c.description}</div> : null}
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{c.code || "—"}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={c.is_active ? "active" : "ended"} label={c.is_active ? "Active" : "Inactive"} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(c)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    {!c.is_system ? (
                      <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(c)}>
                        <Trash2 className="h-4 w-4 text-[var(--error)]" />
                      </Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title={editing ? "Edit category" : "New category"} onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
            <Input label="Code" value={form.code} onChange={(e) => set({ code: e.target.value })} />
          </div>
          <Textarea label="Description" value={form.description} onChange={(e) => set({ description: e.target.value })} />
          <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
            <input type="checkbox" checked={form.is_active} onChange={(e) => set({ is_active: e.target.checked })} />
            Active
          </label>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={submit}>
              {editing ? "Save" : "Create"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

/* ------------------------------- Structures ------------------------------ */

type StructureForm = {
  name: string;
  category: string;
  description: string;
  amount: string;
  recurrence: FeeStructure["recurrence"];
  tax_rate: string;
  due_day: string;
  grace_period_days: string;
  late_fine_type: FeeStructure["late_fine_type"];
  late_fine_amount: string;
  allow_installments: boolean;
  is_active: boolean;
};

const emptyStructure: StructureForm = {
  name: "",
  category: "",
  description: "",
  amount: "0",
  recurrence: "monthly",
  tax_rate: "0",
  due_day: "1",
  grace_period_days: "0",
  late_fine_type: "none",
  late_fine_amount: "0",
  allow_installments: false,
  is_active: true,
};

function StructuresTab() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<FeeStructure[]>([]);
  const [categories, setCategories] = useState<FeeCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<FeeStructure | null>(null);
  const [form, setForm] = useState<StructureForm>(emptyStructure);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await financeApi.feeStructures.list());
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
    financeApi.feeCategories.list().then(setCategories).catch(() => {});
  }, [load]);

  const set = (patch: Partial<StructureForm>) => setForm((f) => ({ ...f, ...patch }));

  const startCreate = () => {
    setEditing(null);
    setForm({ ...emptyStructure, category: categories[0]?.id ?? "" });
    setOpen(true);
  };
  const startEdit = (s: FeeStructure) => {
    setEditing(s);
    setForm({
      name: s.name,
      category: s.category,
      description: s.description,
      amount: s.amount,
      recurrence: s.recurrence,
      tax_rate: s.tax_rate,
      due_day: String(s.due_day),
      grace_period_days: String(s.grace_period_days),
      late_fine_type: s.late_fine_type,
      late_fine_amount: s.late_fine_amount,
      allow_installments: s.allow_installments,
      is_active: s.is_active,
    });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.name.trim() || !form.category) {
      toast.error("Name and category are required.");
      return;
    }
    setBusy(true);
    try {
      const body: Partial<FeeStructure> = {
        name: form.name.trim(),
        category: form.category,
        description: form.description,
        amount: form.amount || "0",
        recurrence: form.recurrence,
        tax_rate: form.tax_rate || "0",
        due_day: Number(form.due_day) || 1,
        grace_period_days: Number(form.grace_period_days) || 0,
        late_fine_type: form.late_fine_type,
        late_fine_amount: form.late_fine_amount || "0",
        allow_installments: form.allow_installments,
        is_active: form.is_active,
      };
      if (editing) await financeApi.feeStructures.update(editing.id, body);
      else await financeApi.feeStructures.create(body);
      toast.success(editing ? "Structure updated." : "Structure created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (s: FeeStructure) => {
    const yes = await confirm({
      title: "Delete fee structure",
      message: `Delete "${s.name}"?`,
      danger: true,
      confirmText: "Delete",
    });
    if (!yes) return;
    try {
      await financeApi.feeStructures.remove(s.id);
      toast.success("Structure deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New structure
        </Button>
      </div>
      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No fee structures" description="Define recurring or one-time fees residents can be billed for." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Category</th>
              <th className="px-4 py-3 font-medium text-right">Amount</th>
              <th className="px-4 py-3 font-medium">Recurrence</th>
              <th className="px-4 py-3 font-medium">Active</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium text-[var(--foreground)]">{s.name}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{s.category_name}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground)]">{formatMoney(s.amount)}</td>
                <td className="px-4 py-3 capitalize text-[var(--foreground-secondary)]">{s.recurrence.replace(/_/g, " ")}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={s.is_active ? "active" : "ended"} label={s.is_active ? "Active" : "Inactive"} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(s)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(s)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title={editing ? "Edit structure" : "New structure"} onClose={() => setOpen(false)}>
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
            <Select label="Category" value={form.category} onChange={(e) => set({ category: e.target.value })} placeholder="Select category">
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </div>
          <Textarea label="Description" value={form.description} onChange={(e) => set({ description: e.target.value })} />
          <div className="grid grid-cols-3 gap-3">
            <Input label="Amount" type="number" value={form.amount} onChange={(e) => set({ amount: e.target.value })} />
            <Select label="Recurrence" value={form.recurrence} onChange={(e) => set({ recurrence: e.target.value as FeeStructure["recurrence"] })} options={FEE_RECURRENCES} />
            <Input label="Tax %" type="number" value={form.tax_rate} onChange={(e) => set({ tax_rate: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Due day" type="number" value={form.due_day} onChange={(e) => set({ due_day: e.target.value })} />
            <Input label="Grace period (days)" type="number" value={form.grace_period_days} onChange={(e) => set({ grace_period_days: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Select label="Late fine type" value={form.late_fine_type} onChange={(e) => set({ late_fine_type: e.target.value as FeeStructure["late_fine_type"] })} options={LATE_FINE_TYPES} />
            <Input label="Late fine amount" type="number" value={form.late_fine_amount} onChange={(e) => set({ late_fine_amount: e.target.value })} />
          </div>
          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
              <input type="checkbox" checked={form.allow_installments} onChange={(e) => set({ allow_installments: e.target.checked })} />
              Allow installments
            </label>
            <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
              <input type="checkbox" checked={form.is_active} onChange={(e) => set({ is_active: e.target.checked })} />
              Active
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={submit}>
              {editing ? "Save" : "Create"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

/* ------------------------------ Assignments ------------------------------ */

function AssignmentsTab() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<FeeAssignment[]>([]);
  const [structures, setStructures] = useState<FeeStructure[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  // Single assign form.
  const [assignOpen, setAssignOpen] = useState(false);
  const [feeStructure, setFeeStructure] = useState("");
  const [resident, setResident] = useState("");
  const [amountOverride, setAmountOverride] = useState("");
  const [startDate, setStartDate] = useState("");

  // Bulk assign form.
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkStructure, setBulkStructure] = useState("");
  const [bulkAmount, setBulkAmount] = useState("");
  const [bulkStart, setBulkStart] = useState("");
  const [bulkSearch, setBulkSearch] = useState("");
  const [bulkOptions, setBulkOptions] = useState<ResidentOption[]>([]);
  const [bulkSelected, setBulkSelected] = useState<Record<string, string>>({});

  // Waive form.
  const [waiving, setWaiving] = useState<FeeAssignment | null>(null);
  const [waiveReason, setWaiveReason] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await financeApi.feeAssignments.list());
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
    financeApi.feeStructures.list({ is_active: "true" }).then(setStructures).catch(() => {});
  }, [load]);

  useEffect(() => {
    if (!bulkOpen) return;
    let active = true;
    const t = setTimeout(() => {
      financeApi.residents
        .list(bulkSearch)
        .then((r) => {
          if (active) setBulkOptions(r);
        })
        .catch(() => {});
    }, 200);
    return () => {
      active = false;
      clearTimeout(t);
    };
  }, [bulkOpen, bulkSearch]);

  const submitAssign = async () => {
    if (!feeStructure || !resident) {
      toast.error("Pick a fee structure and a resident.");
      return;
    }
    setBusy(true);
    try {
      await financeApi.feeAssignments.create({
        fee_structure: feeStructure,
        resident,
        amount_override: amountOverride || undefined,
        start_date: startDate || undefined,
      });
      toast.success("Fee assigned.");
      setAssignOpen(false);
      setFeeStructure("");
      setResident("");
      setAmountOverride("");
      setStartDate("");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const toggleBulk = (r: ResidentOption) =>
    setBulkSelected((prev) => {
      const next = { ...prev };
      if (next[r.id]) delete next[r.id];
      else next[r.id] = r.full_name;
      return next;
    });

  const submitBulk = async () => {
    const ids = Object.keys(bulkSelected);
    if (!bulkStructure || ids.length === 0) {
      toast.error("Pick a fee structure and at least one resident.");
      return;
    }
    setBusy(true);
    try {
      const res = await financeApi.feeAssignments.bulkAssign({
        fee_structure: bulkStructure,
        resident_ids: ids,
        amount_override: bulkAmount || undefined,
        start_date: bulkStart || undefined,
      });
      toast.success(`${res.created} assignment(s) created.`);
      setBulkOpen(false);
      setBulkStructure("");
      setBulkAmount("");
      setBulkStart("");
      setBulkSelected({});
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const submitWaive = async () => {
    if (!waiving) return;
    setBusy(true);
    try {
      await financeApi.feeAssignments.waive(waiving.id, waiveReason);
      toast.success("Assignment waived.");
      setWaiving(null);
      setWaiveReason("");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (a: FeeAssignment) => {
    const yes = await confirm({
      title: "Remove assignment",
      message: `Remove ${a.fee_name} from ${a.resident_name}?`,
      danger: true,
      confirmText: "Remove",
    });
    if (!yes) return;
    try {
      await financeApi.feeAssignments.remove(a.id);
      toast.success("Assignment removed.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-end gap-2">
        <Button variant="secondary" onClick={() => setBulkOpen(true)}>
          <Users className="h-4 w-4" /> Bulk assign
        </Button>
        <Button onClick={() => setAssignOpen(true)}>
          <Plus className="h-4 w-4" /> Assign fee
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No fee assignments" description="Assign fee structures to residents individually or in bulk." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Fee</th>
              <th className="px-4 py-3 font-medium">Resident</th>
              <th className="px-4 py-3 font-medium text-right">Amount</th>
              <th className="px-4 py-3 font-medium">Start</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium text-[var(--foreground)]">{a.fee_name}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{a.resident_name}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground)]">{formatMoney(a.effective_amount)}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{a.start_date}</td>
                <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    {a.status !== "waived" ? (
                      <Button variant="ghost" size="sm" title="Waive" onClick={() => { setWaiving(a); setWaiveReason(""); }}>
                        Waive
                      </Button>
                    ) : null}
                    <Button variant="ghost" size="sm" title="Remove" onClick={() => remove(a)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {/* Single assign */}
      <Modal open={assignOpen} title="Assign fee" onClose={() => setAssignOpen(false)}>
        <div className="space-y-3">
          <Select label="Fee structure" value={feeStructure} onChange={(e) => setFeeStructure(e.target.value)} placeholder="Select structure">
            {structures.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({formatMoney(s.amount)})
              </option>
            ))}
          </Select>
          <ResidentPicker value={resident} onChange={setResident} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Amount override (optional)" type="number" value={amountOverride} onChange={(e) => setAmountOverride(e.target.value)} />
            <Input label="Start date (optional)" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setAssignOpen(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={submitAssign}>
              Assign
            </Button>
          </div>
        </div>
      </Modal>

      {/* Bulk assign */}
      <Modal open={bulkOpen} title="Bulk assign fee" onClose={() => setBulkOpen(false)}>
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          <Select label="Fee structure" value={bulkStructure} onChange={(e) => setBulkStructure(e.target.value)} placeholder="Select structure">
            {structures.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({formatMoney(s.amount)})
              </option>
            ))}
          </Select>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Amount override (optional)" type="number" value={bulkAmount} onChange={(e) => setBulkAmount(e.target.value)} />
            <Input label="Start date (optional)" type="date" value={bulkStart} onChange={(e) => setBulkStart(e.target.value)} />
          </div>
          <Input label="Search residents" placeholder="Type to filter residents…" value={bulkSearch} onChange={(e) => setBulkSearch(e.target.value)} />
          <div className="text-xs text-[var(--muted)]">{Object.keys(bulkSelected).length} selected</div>
          <div className="max-h-56 space-y-1 overflow-y-auto rounded-xl border border-[var(--border)] p-2">
            {bulkOptions.length === 0 ? (
              <div className="py-4 text-center text-sm text-[var(--muted)]">No residents match.</div>
            ) : (
              bulkOptions.map((r) => (
                <label key={r.id} className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-[var(--foreground)] hover:bg-[var(--background-secondary)]">
                  <input type="checkbox" checked={!!bulkSelected[r.id]} onChange={() => toggleBulk(r)} />
                  {r.full_name}
                </label>
              ))
            )}
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setBulkOpen(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={submitBulk}>
              Assign to {Object.keys(bulkSelected).length}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Waive */}
      <Modal open={!!waiving} title="Waive assignment" onClose={() => setWaiving(null)}>
        <div className="space-y-3">
          <p className="text-sm text-[var(--foreground-secondary)]">
            Waive <strong>{waiving?.fee_name}</strong> for {waiving?.resident_name}.
          </p>
          <Textarea label="Reason" value={waiveReason} onChange={(e) => setWaiveReason(e.target.value)} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setWaiving(null)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={submitWaive}>
              Waive
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
