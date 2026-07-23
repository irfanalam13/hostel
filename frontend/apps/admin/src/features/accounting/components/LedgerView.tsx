"use client";

import React, { useEffect, useState } from "react";
import { Button, EmptyState, Input, Select, Table, useToast } from "@hostel/ui";
import { Search } from "lucide-react";

import { accountingApi } from "../api/accounting.api";
import type { Account, AccountLedger } from "../types/accounting.types";
import { formatMoney } from "./primitives";

export function LedgerView() {
  const toast = useToast();

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  const [ledger, setLedger] = useState<AccountLedger | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    accountingApi.accounts
      .list({ is_group: "false", ordering: "code" })
      .then(setAccounts)
      .catch(() => {});
  }, []);

  const run = async () => {
    if (!accountId) {
      toast.error("Pick an account to view its ledger.");
      return;
    }
    setLoading(true);
    try {
      setLedger(
        await accountingApi.accounts.ledger(accountId, {
          start: start || undefined,
          end: end || undefined,
        }),
      );
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[220px] flex-1">
          <Select
            label="Account"
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            placeholder="Select account"
          >
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.code} · {a.name}
              </option>
            ))}
          </Select>
        </div>
        <Input label="From" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        <Input label="To" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        <Button loading={loading} onClick={run}>
          <Search className="h-4 w-4" /> View ledger
        </Button>
      </div>

      {!ledger ? (
        <EmptyState
          title="No ledger loaded"
          description="Pick an account and an optional date range, then view the ledger."
        />
      ) : (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-[var(--border)] bg-[var(--card)] px-4 py-3">
            <div>
              <div className="text-sm font-semibold text-[var(--foreground)]">
                {ledger.account.code} · {ledger.account.name}
              </div>
              <div className="text-xs capitalize text-[var(--muted)]">
                {ledger.account.type} · normal balance {ledger.account.normal_balance}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Opening</div>
              <div className="font-semibold text-[var(--foreground)]">
                {formatMoney(ledger.opening_balance)}
              </div>
            </div>
          </div>

          {ledger.rows.length === 0 ? (
            <EmptyState title="No postings" description="This account has no entries in the selected range." />
          ) : (
            <Table>
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Journal</th>
                  <th className="px-4 py-3 font-medium">Description</th>
                  <th className="px-4 py-3 font-medium text-right">Debit</th>
                  <th className="px-4 py-3 font-medium text-right">Credit</th>
                  <th className="px-4 py-3 font-medium text-right">Balance</th>
                </tr>
              </thead>
              <tbody>
                {ledger.rows.map((r) => (
                  <tr key={r.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.date}</td>
                    <td className="px-4 py-3 font-medium text-[var(--foreground)]">{r.journal_number}</td>
                    <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.description || "—"}</td>
                    <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
                      {parseFloat(r.debit || "0") ? formatMoney(r.debit) : "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
                      {parseFloat(r.credit || "0") ? formatMoney(r.credit) : "—"}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">
                      {formatMoney(r.balance)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="font-semibold text-[var(--foreground)]">
                  <td className="px-4 py-3" colSpan={5}>
                    Closing balance
                  </td>
                  <td className="px-4 py-3 text-right">{formatMoney(ledger.closing_balance)}</td>
                </tr>
              </tfoot>
            </Table>
          )}
        </div>
      )}
    </div>
  );
}
