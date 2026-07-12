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
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";

import { financeApi } from "../api/finance.api";
import { AWARD_TYPES, SCHOLARSHIP_TYPES } from "../constants";
import type {
  AwardType,
  Scholarship,
  ScholarshipAward,
  ScholarshipType,
} from "../types/finance.types";
import { ResidentPicker } from "./ResidentPicker";
import { StatusBadge, formatMoney } from "./primitives";

const TABS = [
  { id: "programs", label: "Programs" },
  { id: "awards", label: "Awards" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export function ScholarshipManager() {
  const [tab, setTab] = useState<TabId>("programs");
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
      {tab === "programs" ? <ProgramsTab /> : <AwardsTab />}
    </div>
  );
}

/* -------------------------------- Programs ------------------------------- */

type ProgramForm = {
  name: string;
  scholarship_type: ScholarshipType;
  award_type: AwardType;
  value: string;
  description: string;
  is_active: boolean;
};

const emptyProgram: ProgramForm = {
  name: "",
  scholarship_type: "merit",
  award_type: "percentage",
  value: "0",
  description: "",
  is_active: true,
};

function programValue(s: Scholarship): string {
  return s.award_type === "percentage" ? `${parseFloat(s.value)}%` : formatMoney(s.value);
}

function ProgramsTab() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<Scholarship[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Scholarship | null>(null);
  const [form, setForm] = useState<ProgramForm>(emptyProgram);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await financeApi.scholarships.list());
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (patch: Partial<ProgramForm>) => setForm((f) => ({ ...f, ...patch }));

  const startCreate = () => {
    setEditing(null);
    setForm(emptyProgram);
    setOpen(true);
  };
  const startEdit = (s: Scholarship) => {
    setEditing(s);
    setForm({
      name: s.name,
      scholarship_type: s.scholarship_type,
      award_type: s.award_type,
      value: s.value,
      description: s.description,
      is_active: s.is_active,
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
      if (editing) await financeApi.scholarships.update(editing.id, form);
      else await financeApi.scholarships.create(form);
      toast.success(editing ? "Scholarship updated." : "Scholarship created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (s: Scholarship) => {
    const yes = await confirm({
      title: "Delete scholarship",
      message: `Delete "${s.name}"?`,
      danger: true,
      confirmText: "Delete",
    });
    if (!yes) return;
    try {
      await financeApi.scholarships.remove(s.id);
      toast.success("Scholarship deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New scholarship
        </Button>
      </div>
      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No scholarships" description="Define scholarship programs residents can be awarded." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium text-right">Award</th>
              <th className="px-4 py-3 font-medium text-right">Awards</th>
              <th className="px-4 py-3 font-medium">Active</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium text-[var(--foreground)]">{s.name}</td>
                <td className="px-4 py-3 capitalize text-[var(--foreground-secondary)]">{s.scholarship_type.replace(/_/g, " ")}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground)]">{programValue(s)}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{s.awards_count}</td>
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

      <Modal open={open} title={editing ? "Edit scholarship" : "New scholarship"} onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
          <div className="grid grid-cols-3 gap-3">
            <Select label="Type" value={form.scholarship_type} onChange={(e) => set({ scholarship_type: e.target.value as ScholarshipType })} options={SCHOLARSHIP_TYPES} />
            <Select label="Award" value={form.award_type} onChange={(e) => set({ award_type: e.target.value as AwardType })} options={AWARD_TYPES} />
            <Input label={form.award_type === "percentage" ? "Value %" : "Amount"} type="number" value={form.value} onChange={(e) => set({ value: e.target.value })} />
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

/* --------------------------------- Awards -------------------------------- */

function AwardsTab() {
  const toast = useToast();

  const [rows, setRows] = useState<ScholarshipAward[]>([]);
  const [programs, setPrograms] = useState<Scholarship[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");

  const [open, setOpen] = useState(false);
  const [scholarship, setScholarship] = useState("");
  const [resident, setResident] = useState("");
  const [validFrom, setValidFrom] = useState("");
  const [validUntil, setValidUntil] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await financeApi.scholarshipAwards.list({ status: statusFilter || undefined }));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, toast]);

  useEffect(() => {
    load();
    financeApi.scholarships.list().then(setPrograms).catch(() => {});
  }, [load]);

  const submit = async () => {
    if (!scholarship || !resident) {
      toast.error("Pick a scholarship and a resident.");
      return;
    }
    setBusy(true);
    try {
      await financeApi.scholarshipAwards.create({
        scholarship,
        resident,
        valid_from: validFrom || undefined,
        valid_until: validUntil || undefined,
        note: note || undefined,
      });
      toast.success("Award created.");
      setOpen(false);
      setScholarship("");
      setResident("");
      setValidFrom("");
      setValidUntil("");
      setNote("");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
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

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <Select
          label="Status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          options={[
            { value: "", label: "All statuses" },
            { value: "pending", label: "Pending" },
            { value: "approved", label: "Approved" },
            { value: "rejected", label: "Rejected" },
            { value: "revoked", label: "Revoked" },
          ]}
        />
        <Button onClick={() => setOpen(true)}>
          <Plus className="h-4 w-4" /> New award
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No awards" description="Award scholarships to residents and route them through approval." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Scholarship</th>
              <th className="px-4 py-3 font-medium">Resident</th>
              <th className="px-4 py-3 font-medium">Valid until</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium text-[var(--foreground)]">{a.scholarship_name}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{a.resident_name}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{a.valid_until || "—"}</td>
                <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    {a.status === "pending" ? (
                      <>
                        <Button variant="ghost" size="sm" title="Approve" onClick={() => act(() => financeApi.scholarshipAwards.approve(a.id), "Award approved.")}>
                          <Check className="h-4 w-4 text-[var(--success)]" />
                        </Button>
                        <Button variant="ghost" size="sm" title="Reject" onClick={() => act(() => financeApi.scholarshipAwards.reject(a.id), "Award rejected.")}>
                          <X className="h-4 w-4 text-[var(--error)]" />
                        </Button>
                      </>
                    ) : null}
                    {a.status === "approved" ? (
                      <Button variant="ghost" size="sm" title="Revoke" onClick={() => act(() => financeApi.scholarshipAwards.revoke(a.id), "Award revoked.")}>
                        Revoke
                      </Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title="New award" onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <Select label="Scholarship" value={scholarship} onChange={(e) => setScholarship(e.target.value)} placeholder="Select scholarship">
            {programs.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </Select>
          <ResidentPicker value={resident} onChange={setResident} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Valid from (optional)" type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />
            <Input label="Valid until (optional)" type="date" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} />
          </div>
          <Textarea label="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={submit}>
              Create
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
