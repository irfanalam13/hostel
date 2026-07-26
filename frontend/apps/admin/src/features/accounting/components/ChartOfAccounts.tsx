"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
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
import { Lock, Pencil, Plus, ScrollText, Sparkles, Trash2 } from "lucide-react";

import { accountingApi } from "../api/accounting.api";
import type { Account, AccountLedger, AccountPayload, AccountType } from "../types/accounting.types";
import { ACCOUNT_TYPES, Badge, StatusBadge, formatMoney } from "./primitives";

const TYPE_FILTERS = [{ value: "", label: "All types" }, ...ACCOUNT_TYPES];

type AccountForm = {
  code: string;
  name: string;
  type: AccountType;
  subtype: string;
  parent: string;
  is_group: boolean;
  opening_balance: string;
  description: string;
  is_active: boolean;
};

const emptyAccount: AccountForm = {
  code: "",
  name: "",
  type: "asset",
  subtype: "",
  parent: "",
  is_group: false,
  opening_balance: "0",
  description: "",
  is_active: true,
};

export function ChartOfAccounts() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [activeOnly, setActiveOnly] = useState(false);

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [form, setForm] = useState<AccountForm>(emptyAccount);
  const [busy, setBusy] = useState(false);
  const [seeding, setSeeding] = useState(false);

  // Ledger drawer.
  const [ledgerFor, setLedgerFor] = useState<Account | null>(null);
  const [ledger, setLedger] = useState<AccountLedger | null>(null);
  const [ledgerLoading, setLedgerLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(
        await accountingApi.accounts.list({
          search,
          type: typeFilter || undefined,
          is_active: activeOnly ? "true" : undefined,
          ordering: "code",
        }),
      );
    } catch (e) {
      toast.error((e as Error).message, "Couldn't load accounts");
    } finally {
      setLoading(false);
    }
  }, [search, typeFilter, activeOnly, toast]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  const set = (patch: Partial<AccountForm>) => setForm((f) => ({ ...f, ...patch }));

  // Group accounts scoped to the currently-selected type make valid parents.
  const parentOptions = useMemo(
    () => rows.filter((a) => a.is_group && a.type === form.type && a.id !== editing?.id),
    [rows, form.type, editing],
  );

  // Rows sorted by type then code so the type grouping reads top-to-bottom.
  const grouped = useMemo(() => {
    const order: AccountType[] = ["asset", "liability", "equity", "income", "expense"];
    return [...rows].sort((a, b) => {
      const ta = order.indexOf(a.type);
      const tb = order.indexOf(b.type);
      if (ta !== tb) return ta - tb;
      return a.code.localeCompare(b.code);
    });
  }, [rows]);

  const startCreate = () => {
    setEditing(null);
    setForm({ ...emptyAccount, type: (typeFilter as AccountType) || "asset" });
    setOpen(true);
  };
  const startEdit = (a: Account) => {
    setEditing(a);
    setForm({
      code: a.code,
      name: a.name,
      type: a.type,
      subtype: a.subtype,
      parent: a.parent ?? "",
      is_group: a.is_group,
      opening_balance: a.opening_balance,
      description: a.description,
      is_active: a.is_active,
    });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.name.trim()) {
      toast.error("An account name is required.");
      return;
    }
    setBusy(true);
    try {
      const body: AccountPayload = {
        name: form.name.trim(),
        subtype: form.subtype,
        parent: form.parent || null,
        is_group: form.is_group,
        opening_balance: form.opening_balance || "0",
        description: form.description,
        is_active: form.is_active,
      };
      if (form.code.trim()) body.code = form.code.trim();
      // System accounts have a locked type — only send type on create / non-system.
      if (!editing || !editing.is_system) body.type = form.type;
      if (editing) await accountingApi.accounts.update(editing.id, body);
      else await accountingApi.accounts.create(body);
      toast.success(editing ? "Account updated." : "Account created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (a: Account) => {
    const yes = await confirm({
      title: "Delete account",
      message: `Delete "${a.code} · ${a.name}"?`,
      danger: true,
      confirmText: "Delete",
    });
    if (!yes) return;
    try {
      await accountingApi.accounts.remove(a.id);
      toast.success("Account deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const seed = async () => {
    const yes = await confirm({
      title: "Seed default accounts",
      message: "Create the standard chart of accounts? Existing accounts are kept.",
      confirmText: "Seed defaults",
    });
    if (!yes) return;
    setSeeding(true);
    try {
      const res = await accountingApi.accounts.seedDefaults();
      toast.success(`${res.created} default account(s) created.`);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setSeeding(false);
    }
  };

  const openLedger = async (a: Account) => {
    setLedgerFor(a);
    setLedger(null);
    setLedgerLoading(true);
    try {
      setLedger(await accountingApi.accounts.ledger(a.id));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLedgerLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[200px] flex-1">
          <Input
            label="Search"
            placeholder="Code or account name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select
          label="Type"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          options={TYPE_FILTERS}
        />
        <label className="flex items-center gap-2 py-2 text-sm text-[var(--foreground-secondary)]">
          <input type="checkbox" checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} />
          Active only
        </label>
        <Button variant="secondary" loading={seeding} onClick={seed}>
          <Sparkles className="h-4 w-4" /> Seed defaults
        </Button>
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New account
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : grouped.length === 0 ? (
        <EmptyState
          title="No accounts yet"
          description="Seed the default chart of accounts or create accounts manually."
        />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Code</th>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Normal</th>
              <th className="px-4 py-3 font-medium text-right">Opening</th>
              <th className="px-4 py-3 font-medium">Active</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {grouped.map((a) => (
              <tr key={a.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-mono text-[var(--foreground-secondary)]">{a.code}</td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center gap-2 text-[var(--foreground)] ${
                      a.is_group ? "font-semibold" : "font-medium"
                    }`}
                    style={{ paddingLeft: a.parent ? 16 : 0 }}
                  >
                    {a.name}
                    {a.is_system ? (
                      <Badge tone="accent">
                        <Lock className="h-3 w-3" /> System
                      </Badge>
                    ) : null}
                    {a.is_group ? <Badge>Group</Badge> : null}
                  </span>
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{a.type_display}</td>
                <td className="px-4 py-3 capitalize text-[var(--foreground-secondary)]">
                  {a.normal_balance}
                </td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
                  {formatMoney(a.opening_balance, a.currency)}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge
                    status={a.is_active ? "active" : "inactive"}
                    label={a.is_active ? "Active" : "Inactive"}
                  />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Ledger" onClick={() => openLedger(a)}>
                      <ScrollText className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(a)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    {!a.is_system ? (
                      <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(a)}>
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

      {/* Create / edit */}
      <Modal open={open} title={editing ? "Edit account" : "New account"} onClose={() => setOpen(false)}>
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Code (auto if blank)"
              value={form.code}
              onChange={(e) => set({ code: e.target.value })}
            />
            <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="Type"
              value={form.type}
              onChange={(e) => set({ type: e.target.value as AccountType, parent: "" })}
              options={ACCOUNT_TYPES}
              disabled={!!editing?.is_system}
            />
            <Input
              label="Subtype (optional)"
              value={form.subtype}
              onChange={(e) => set({ subtype: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="Parent group (optional)"
              value={form.parent}
              onChange={(e) => set({ parent: e.target.value })}
              placeholder="No parent"
            >
              {parentOptions.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} · {p.name}
                </option>
              ))}
            </Select>
            <Input
              label="Opening balance"
              type="number"
              value={form.opening_balance}
              onChange={(e) => set({ opening_balance: e.target.value })}
            />
          </div>
          <Textarea
            label="Description (optional)"
            value={form.description}
            onChange={(e) => set({ description: e.target.value })}
          />
          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
              <input
                type="checkbox"
                checked={form.is_group}
                onChange={(e) => set({ is_group: e.target.checked })}
              />
              Group (header) account
            </label>
            <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => set({ is_active: e.target.checked })}
              />
              Active
            </label>
          </div>
          {editing?.is_system ? (
            <p className="text-[11px] text-[var(--muted)]">
              This is a system account — its type is locked and it can&apos;t be deleted.
            </p>
          ) : null}
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

      {/* Ledger drawer */}
      <Modal
        open={!!ledgerFor}
        title={ledgerFor ? `Ledger · ${ledgerFor.code} ${ledgerFor.name}` : "Ledger"}
        onClose={() => setLedgerFor(null)}
      >
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          {ledgerLoading ? (
            <div className="text-sm text-[var(--muted)]">Loading…</div>
          ) : !ledger ? (
            <p className="py-4 text-center text-sm text-[var(--muted)]">No ledger data.</p>
          ) : (
            <>
              <div className="flex items-center justify-between rounded-xl bg-[var(--background-secondary)] px-3 py-2 text-sm">
                <span className="text-[var(--foreground-secondary)]">Opening balance</span>
                <span className="font-semibold text-[var(--foreground)]">
                  {formatMoney(ledger.opening_balance)}
                </span>
              </div>
              {ledger.rows.length === 0 ? (
                <p className="py-4 text-center text-sm text-[var(--muted)]">No postings yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                        <th className="py-2 pr-3 font-medium">Date</th>
                        <th className="py-2 pr-3 font-medium">Journal</th>
                        <th className="py-2 pr-3 font-medium text-right">Debit</th>
                        <th className="py-2 pr-3 font-medium text-right">Credit</th>
                        <th className="py-2 font-medium text-right">Balance</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border)]">
                      {ledger.rows.map((r) => (
                        <tr key={r.id}>
                          <td className="py-2 pr-3 text-[var(--foreground-secondary)]">{r.date}</td>
                          <td className="py-2 pr-3 text-[var(--foreground)]">{r.journal_number}</td>
                          <td className="py-2 pr-3 text-right text-[var(--foreground-secondary)]">
                            {parseFloat(r.debit || "0") ? formatMoney(r.debit) : "—"}
                          </td>
                          <td className="py-2 pr-3 text-right text-[var(--foreground-secondary)]">
                            {parseFloat(r.credit || "0") ? formatMoney(r.credit) : "—"}
                          </td>
                          <td className="py-2 text-right font-medium text-[var(--foreground)]">
                            {formatMoney(r.balance)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="flex items-center justify-between border-t border-[var(--border)] pt-2 text-sm font-semibold text-[var(--foreground)]">
                <span>Closing balance</span>
                <span>{formatMoney(ledger.closing_balance)}</span>
              </div>
            </>
          )}
        </div>
      </Modal>
    </div>
  );
}
