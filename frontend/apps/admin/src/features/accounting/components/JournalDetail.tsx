"use client";

import React from "react";
import Link from "next/link";
import { Button, Card, ErrorState, useConfirm, useToast } from "@hostel/ui";
import { ArrowLeft, CheckCircle2, RotateCcw, Send, Upload } from "lucide-react";
import { useApi } from "@hostel/hooks";

import { accountingApi } from "../api/accounting.api";
import { ReadField, StatusBadge, formatMoney } from "./primitives";

export function JournalDetail({ journalId }: { journalId: string }) {
  const toast = useToast();
  const confirm = useConfirm();

  const { data: journal, loading, error, refetch } = useApi(
    () => accountingApi.journals.retrieve(journalId),
    { deps: [journalId], toastOnError: false },
  );

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      toast.success(ok);
      await refetch();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const reverse = async () => {
    if (!journal) return;
    const yes = await confirm({
      title: "Reverse journal",
      message: `Post a reversing entry for ${journal.number}?`,
      confirmText: "Reverse",
    });
    if (yes) await act(() => accountingApi.journals.reverse(journal.id), "Reversal posted.");
  };

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (error || !journal)
    return <ErrorState description={error || "Journal not found."} onRetry={refetch} />;

  return (
    <div className="space-y-5">
      <Link
        href="/accounting/journals"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--muted)] hover:text-[var(--foreground)]"
      >
        <ArrowLeft className="h-4 w-4" /> Back to journals
      </Link>

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-[var(--foreground)]">{journal.number}</h2>
              <StatusBadge status={journal.status} label={journal.status_display} />
              <StatusBadge
                status={journal.is_balanced ? "balanced" : "unbalanced"}
                label={journal.is_balanced ? "Balanced" : "Out of balance"}
              />
            </div>
            {journal.description ? (
              <div className="mt-0.5 text-sm text-[var(--muted)]">{journal.description}</div>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {journal.status === "draft" ? (
              <Button
                variant="secondary"
                onClick={() => act(() => accountingApi.journals.submit(journal.id), "Journal submitted.")}
              >
                <Send className="h-4 w-4" /> Submit
              </Button>
            ) : null}
            {journal.status === "submitted" ? (
              <Button
                variant="secondary"
                onClick={() => act(() => accountingApi.journals.approve(journal.id), "Journal approved.")}
              >
                <CheckCircle2 className="h-4 w-4" /> Approve
              </Button>
            ) : null}
            {journal.status === "draft" || journal.status === "approved" ? (
              <Button onClick={() => act(() => accountingApi.journals.post(journal.id), "Journal posted.")}>
                <Upload className="h-4 w-4" /> Post
              </Button>
            ) : null}
            {journal.status === "posted" ? (
              <Button variant="ghost" onClick={reverse}>
                <RotateCcw className="h-4 w-4 text-[var(--warning)]" /> Reverse
              </Button>
            ) : null}
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 border-t border-[var(--border)] pt-4 md:grid-cols-4">
          <ReadField label="Date" value={journal.date} />
          <ReadField label="Posting date" value={journal.posting_date} />
          <ReadField label="Type" value={<span className="capitalize">{journal.journal_type}</span>} />
          <ReadField label="Reference" value={journal.reference} />
          <ReadField label="Currency" value={journal.currency} />
          <ReadField label="Exchange rate" value={journal.exchange_rate} />
          <ReadField
            label="Created"
            value={journal.created_at ? new Date(journal.created_at).toLocaleDateString() : "—"}
          />
          <ReadField label="Locked" value={journal.is_locked ? "Yes" : "No"} />
        </div>

        {journal.reverses ? (
          <div className="mt-3 rounded-xl bg-[var(--background-secondary)] px-3 py-2 text-xs text-[var(--muted)]">
            This entry reverses journal{" "}
            <Link
              href={`/accounting/journals/${journal.reverses}`}
              className="font-medium text-[var(--accent)] hover:underline"
            >
              {journal.reverses}
            </Link>
            .
          </div>
        ) : null}
      </Card>

      <Card>
        <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">Lines</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                <th className="py-2 pr-3 font-medium">Account</th>
                <th className="py-2 pr-3 font-medium">Description</th>
                <th className="py-2 pr-3 font-medium text-right">Debit</th>
                <th className="py-2 font-medium text-right">Credit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {journal.lines.map((l) => (
                <tr key={l.id}>
                  <td className="py-2.5 pr-3 text-[var(--foreground)]">
                    <span className="font-mono text-[var(--foreground-secondary)]">{l.account_code}</span>{" "}
                    {l.account_name}
                  </td>
                  <td className="py-2.5 pr-3 text-[var(--foreground-secondary)]">{l.description || "—"}</td>
                  <td className="py-2.5 pr-3 text-right text-[var(--foreground-secondary)]">
                    {parseFloat(l.debit || "0") ? formatMoney(l.debit, journal.currency) : "—"}
                  </td>
                  <td className="py-2.5 text-right text-[var(--foreground-secondary)]">
                    {parseFloat(l.credit || "0") ? formatMoney(l.credit, journal.currency) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-[var(--border)] font-semibold text-[var(--foreground)]">
                <td className="py-2.5 pr-3" colSpan={2}>
                  Totals
                </td>
                <td className="py-2.5 pr-3 text-right">{formatMoney(journal.total_debit, journal.currency)}</td>
                <td className="py-2.5 text-right">{formatMoney(journal.total_credit, journal.currency)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </Card>

      {journal.notes ? (
        <Card>
          <h3 className="mb-2 text-sm font-semibold text-[var(--foreground-secondary)]">Notes</h3>
          <p className="text-sm text-[var(--foreground-secondary)]">{journal.notes}</p>
        </Card>
      ) : null}
    </div>
  );
}
