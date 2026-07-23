"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
import { CheckCircle2, Eye, Pencil, Plus, RotateCcw, Send, Trash2, Upload } from "lucide-react";

import { accountingApi } from "../api/accounting.api";
import type {
  Account,
  Journal,
  JournalPayload,
  JournalType,
} from "../types/accounting.types";
import { JOURNAL_STATUSES, JOURNAL_TYPES, StatusBadge, formatMoney } from "./primitives";

const STATUS_FILTERS = [{ value: "", label: "All statuses" }, ...JOURNAL_STATUSES];
const TYPE_FILTERS = [{ value: "", label: "All types" }, ...JOURNAL_TYPES];

type LineForm = {
  account: string;
  debit: string;
  credit: string;
  description: string;
  cost_center: string;
};

const emptyLine: LineForm = { account: "", debit: "", credit: "", description: "", cost_center: "" };

const num = (v: string) => {
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : 0;
};

const todayIso = () => new Date().toISOString().slice(0, 10);

export function JournalList() {
  const toast = useToast();
  const confirm = useConfirm();
  const router = useRouter();

  const [rows, setRows] = useState<Journal[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const [accounts, setAccounts] = useState<Account[]>([]);

  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Journal | null>(null);
  const [busy, setBusy] = useState(false);

  // Journal form state.
  const [date, setDate] = useState(todayIso());
  const [reference, setReference] = useState("");
  const [description, setDescription] = useState("");
  const [journalType, setJournalType] = useState<JournalType>("manual");
  const [notes, setNotes] = useState("");
  const [postNow, setPostNow] = useState(false);
  const [lines, setLines] = useState<LineForm[]>([{ ...emptyLine }, { ...emptyLine }]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(
        await accountingApi.journals.list({
          search,
          status: statusFilter || undefined,
          journal_type: typeFilter || undefined,
          ordering: "-date",
        }),
      );
    } catch (e) {
      toast.error((e as Error).message, "Couldn't load journals");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, typeFilter, toast]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  useEffect(() => {
    accountingApi.accounts
      .list({ is_group: "false", is_active: "true", ordering: "code" })
      .then(setAccounts)
      .catch(() => {});
  }, []);

  const setLine = (i: number, patch: Partial<LineForm>) =>
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));

  const totals = useMemo(() => {
    let debit = 0;
    let credit = 0;
    for (const l of lines) {
      debit += num(l.debit);
      credit += num(l.credit);
    }
    const balanced = debit > 0 && Math.abs(debit - credit) < 0.005;
    return { debit, credit, balanced };
  }, [lines]);

  const resetForm = () => {
    setDate(todayIso());
    setReference("");
    setDescription("");
    setJournalType("manual");
    setNotes("");
    setPostNow(false);
    setLines([{ ...emptyLine }, { ...emptyLine }]);
    setEditing(null);
  };

  const startCreate = () => {
    resetForm();
    setCreating(true);
  };

  const startEdit = (j: Journal) => {
    setEditing(j);
    setDate(j.date);
    setReference(j.reference);
    setDescription(j.description);
    setJournalType(j.journal_type);
    setNotes(j.notes);
    setPostNow(false);
    setLines(
      j.lines.length
        ? j.lines.map((l) => ({
            account: l.account,
            debit: parseFloat(l.debit || "0") ? l.debit : "",
            credit: parseFloat(l.credit || "0") ? l.credit : "",
            description: l.description,
            cost_center: l.cost_center ?? "",
          }))
        : [{ ...emptyLine }, { ...emptyLine }],
    );
    setCreating(true);
  };

  const submit = async () => {
    const cleanLines = lines
      .filter((l) => l.account && (num(l.debit) > 0 || num(l.credit) > 0))
      .map((l) => {
        const line: JournalPayload["lines"][number] = { account: l.account };
        if (num(l.debit) > 0) line.debit = l.debit;
        if (num(l.credit) > 0) line.credit = l.credit;
        if (l.description) line.description = l.description;
        if (l.cost_center) line.cost_center = l.cost_center;
        return line;
      });
    if (cleanLines.length < 2) {
      toast.error("A journal needs at least two lines.");
      return;
    }
    if (!totals.balanced) {
      toast.error("Debits and credits must balance.");
      return;
    }
    const payload: JournalPayload = {
      date,
      description,
      journal_type: journalType,
      lines: cleanLines,
    };
    if (reference) payload.reference = reference;
    if (notes) payload.notes = notes;
    if (postNow && !editing) payload.post = true;

    setBusy(true);
    try {
      if (editing) {
        await accountingApi.journals.update(editing.id, payload);
        toast.success("Journal updated.");
      } else {
        const created = await accountingApi.journals.create(payload);
        toast.success(`Journal ${created.number} created.`);
      }
      setCreating(false);
      resetForm();
      await load();
    } catch (e) {
      toast.error((e as Error).message, "Couldn't save journal");
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

  const reverse = async (j: Journal) => {
    const yes = await confirm({
      title: "Reverse journal",
      message: `Post a reversing entry for ${j.number}?`,
      confirmText: "Reverse",
    });
    if (yes) await act(() => accountingApi.journals.reverse(j.id), "Reversal posted.");
  };

  const remove = async (j: Journal) => {
    const yes = await confirm({
      title: "Delete journal",
      message: `Delete ${j.number}? This can't be undone.`,
      danger: true,
      confirmText: "Delete",
    });
    if (yes) await act(() => accountingApi.journals.remove(j.id), "Journal deleted.");
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[180px] flex-1">
          <Input
            label="Search"
            placeholder="Number, reference or description…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select
          label="Status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          options={STATUS_FILTERS}
        />
        <Select
          label="Type"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          options={TYPE_FILTERS}
        />
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New journal
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No journals yet" description="Record your first journal entry to build the ledger." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Number</th>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Description</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium text-right">Total</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((j) => (
              <tr key={j.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <Link
                    href={`/accounting/journals/${j.id}`}
                    className="font-medium text-[var(--foreground)] hover:text-[var(--accent)]"
                  >
                    {j.number}
                  </Link>
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{j.date}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{j.description || "—"}</td>
                <td className="px-4 py-3 capitalize text-[var(--foreground-secondary)]">
                  {j.journal_type.replace(/_/g, " ")}
                </td>
                <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">
                  {formatMoney(j.total_debit, j.currency)}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={j.status} label={j.status_display} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      title="View"
                      onClick={() => router.push(`/accounting/journals/${j.id}`)}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    {j.status === "draft" ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        title="Submit"
                        onClick={() => act(() => accountingApi.journals.submit(j.id), "Journal submitted.")}
                      >
                        <Send className="h-4 w-4" />
                      </Button>
                    ) : null}
                    {j.status === "submitted" ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        title="Approve"
                        onClick={() => act(() => accountingApi.journals.approve(j.id), "Journal approved.")}
                      >
                        <CheckCircle2 className="h-4 w-4 text-[var(--success)]" />
                      </Button>
                    ) : null}
                    {j.status === "draft" || j.status === "approved" ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        title="Post"
                        onClick={() => act(() => accountingApi.journals.post(j.id), "Journal posted.")}
                      >
                        <Upload className="h-4 w-4 text-[var(--accent)]" />
                      </Button>
                    ) : null}
                    {j.status === "posted" ? (
                      <Button variant="ghost" size="sm" title="Reverse" onClick={() => reverse(j)}>
                        <RotateCcw className="h-4 w-4 text-[var(--warning)]" />
                      </Button>
                    ) : null}
                    {j.status !== "posted" && j.status !== "reversed" ? (
                      <>
                        <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(j)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(j)}>
                          <Trash2 className="h-4 w-4 text-[var(--error)]" />
                        </Button>
                      </>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal
        open={creating}
        title={editing ? `Edit journal · ${editing.number}` : "New journal"}
        onClose={() => setCreating(false)}
      >
        <div className="max-h-[74vh] space-y-4 overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Input label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            <Select
              label="Type"
              value={journalType}
              onChange={(e) => setJournalType(e.target.value as JournalType)}
              options={JOURNAL_TYPES}
            />
            <Input
              label="Reference (optional)"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
            />
          </div>
          <Input
            label="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />

          <section className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Lines</h3>
              <Button variant="ghost" size="sm" onClick={() => setLines((ls) => [...ls, { ...emptyLine }])}>
                <Plus className="h-4 w-4" /> Add line
              </Button>
            </div>
            {lines.map((l, i) => (
              <div key={i} className="rounded-xl border border-[var(--border)] p-3 space-y-2">
                <Select
                  label="Account"
                  value={l.account}
                  onChange={(e) => setLine(i, { account: e.target.value })}
                  placeholder="Select account"
                >
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.code} · {a.name}
                    </option>
                  ))}
                </Select>
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    label="Debit"
                    type="number"
                    value={l.debit}
                    onChange={(e) => setLine(i, { debit: e.target.value, credit: "" })}
                  />
                  <Input
                    label="Credit"
                    type="number"
                    value={l.credit}
                    onChange={(e) => setLine(i, { credit: e.target.value, debit: "" })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    label="Line description (optional)"
                    value={l.description}
                    onChange={(e) => setLine(i, { description: e.target.value })}
                  />
                  <Input
                    label="Cost center (optional)"
                    value={l.cost_center}
                    onChange={(e) => setLine(i, { cost_center: e.target.value })}
                  />
                </div>
                {lines.length > 2 ? (
                  <div className="flex justify-end">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))}
                    >
                      <Trash2 className="h-4 w-4 text-[var(--error)]" /> Remove
                    </Button>
                  </div>
                ) : null}
              </div>
            ))}
          </section>

          {/* Live totals footer */}
          <div className="rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-3 text-sm">
            <div className="flex justify-between text-[var(--foreground-secondary)]">
              <span>Total debit</span>
              <span className="font-semibold text-[var(--foreground)]">{formatMoney(totals.debit)}</span>
            </div>
            <div className="flex justify-between text-[var(--foreground-secondary)]">
              <span>Total credit</span>
              <span className="font-semibold text-[var(--foreground)]">{formatMoney(totals.credit)}</span>
            </div>
            <div className="mt-1 flex items-center justify-between border-t border-[var(--border)] pt-1.5">
              <span className="text-[var(--foreground-secondary)]">Balance check</span>
              <StatusBadge
                status={totals.balanced ? "balanced" : "unbalanced"}
                label={totals.balanced ? "Balanced" : "Out of balance"}
              />
            </div>
          </div>

          <Textarea label="Notes (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} />

          {!editing ? (
            <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
              <input type="checkbox" checked={postNow} onChange={(e) => setPostNow(e.target.checked)} />
              Post immediately (skip draft/approval)
            </label>
          ) : null}

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button loading={busy} disabled={!totals.balanced} onClick={submit}>
              {editing ? "Save" : "Create journal"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
