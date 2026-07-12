"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Button, EmptyState, Input, Modal, useConfirm, useToast } from "@hostel/ui";
import { CalendarPlus, Lock, LockOpen, Plus } from "lucide-react";

import { accountingApi } from "../api/accounting.api";
import type { FiscalYear, Period } from "../types/accounting.types";
import { StatusBadge } from "./primitives";

type YearForm = { name: string; start_date: string; end_date: string };
const emptyYear: YearForm = { name: "", start_date: "", end_date: "" };

export function FiscalYears() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<FiscalYear[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<YearForm>(emptyYear);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await accountingApi.fiscalYears.list());
    } catch (e) {
      toast.error((e as Error).message, "Couldn't load fiscal years");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (patch: Partial<YearForm>) => setForm((f) => ({ ...f, ...patch }));

  const submit = async () => {
    if (!form.name.trim() || !form.start_date || !form.end_date) {
      toast.error("Name, start and end dates are required.");
      return;
    }
    setBusy(true);
    try {
      await accountingApi.fiscalYears.create(form);
      toast.success("Fiscal year created.");
      setOpen(false);
      setForm(emptyYear);
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

  const closeYear = async (y: FiscalYear) => {
    const yes = await confirm({
      title: "Close fiscal year",
      message: `Close "${y.name}"? Posting into this year will be locked.`,
      danger: true,
      confirmText: "Close year",
    });
    if (yes) await act(() => accountingApi.fiscalYears.close(y.id), "Fiscal year closed.");
  };

  const closePeriod = async (p: Period) => {
    await act(() => accountingApi.periods.close(p.id), "Period closed.");
  };
  const reopenPeriod = async (p: Period) => {
    await act(() => accountingApi.periods.reopen(p.id), "Period reopened.");
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setOpen(true)}>
          <Plus className="h-4 w-4" /> New fiscal year
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No fiscal years" description="Create a fiscal year, then generate its monthly periods." />
      ) : (
        <div className="space-y-4">
          {rows.map((y) => (
            <div
              key={y.id}
              className="rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5 shadow-[var(--shadow-sm)]"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-semibold text-[var(--foreground)]">{y.name}</h3>
                    <StatusBadge
                      status={y.is_closed ? "closed" : "active"}
                      label={y.is_closed ? "Closed" : "Open"}
                    />
                  </div>
                  <div className="mt-0.5 text-xs text-[var(--muted)]">
                    {y.start_date} → {y.end_date}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      act(() => accountingApi.fiscalYears.generatePeriods(y.id), "Periods generated.")
                    }
                  >
                    <CalendarPlus className="h-4 w-4" /> Generate periods
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      act(
                        () => accountingApi.fiscalYears.postOpeningBalances(y.id),
                        "Opening balances posted.",
                      )
                    }
                  >
                    Post opening balances
                  </Button>
                  {!y.is_closed ? (
                    <Button variant="ghost" size="sm" onClick={() => closeYear(y)}>
                      <Lock className="h-4 w-4 text-[var(--error)]" /> Close year
                    </Button>
                  ) : null}
                </div>
              </div>

              {y.periods.length === 0 ? (
                <p className="mt-4 border-t border-[var(--border)] pt-4 text-sm text-[var(--muted)]">
                  No periods yet. Use &ldquo;Generate periods&rdquo; to create the 12 monthly periods.
                </p>
              ) : (
                <div className="mt-4 grid gap-2 border-t border-[var(--border)] pt-4 sm:grid-cols-2 lg:grid-cols-3">
                  {y.periods.map((p) => (
                    <div
                      key={p.id}
                      className="flex items-center justify-between rounded-xl border border-[var(--border)] px-3 py-2 text-sm"
                    >
                      <div>
                        <div className="font-medium text-[var(--foreground)]">{p.name}</div>
                        <div className="text-[11px] text-[var(--muted)]">
                          {p.start_date} → {p.end_date}
                        </div>
                      </div>
                      {p.is_closed ? (
                        <Button variant="ghost" size="sm" title="Reopen" onClick={() => reopenPeriod(p)}>
                          <LockOpen className="h-4 w-4 text-[var(--success)]" />
                        </Button>
                      ) : (
                        <Button variant="ghost" size="sm" title="Close" onClick={() => closePeriod(p)}>
                          <Lock className="h-4 w-4 text-[var(--muted)]" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <Modal open={open} title="New fiscal year" onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Start date"
              type="date"
              value={form.start_date}
              onChange={(e) => set({ start_date: e.target.value })}
            />
            <Input
              label="End date"
              type="date"
              value={form.end_date}
              onChange={(e) => set({ end_date: e.target.value })}
            />
          </div>
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
