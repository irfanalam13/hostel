"use client";

import { getBillingSummary, listDues } from "@/features/billing/billing.api";
import type { BillingSummary, MonthlyDue } from "@/features/billing/billing.types";
import { Topbar } from "@/components/shell/Topbar";
import { Button } from "@hostel/ui";
import { Table } from "@hostel/ui";
import { StatCardsSkeleton, TableSkeleton } from "@hostel/ui";
import { EmptyState } from "@hostel/ui";
import { ErrorState } from "@hostel/ui";
import { useApi } from "@hostel/hooks";

type BillingData = { summary: BillingSummary; dues: MonthlyDue[] };

export default function BillingPage() {
  const { data, loading, error, refetch } = useApi<BillingData>(
    async () => {
      const [summary, dues] = await Promise.all([getBillingSummary(), listDues()]);
      return { summary, dues };
    },
    { deps: [] }
  );

  const summary = data?.summary ?? null;
  const dues = data?.dues ?? [];

  const stats = [
    { label: "Total Due", value: summary?.total_due },
    { label: "Paid", value: summary?.total_paid },
    { label: "Pending", value: summary?.pending },
    { label: "Residents", value: summary?.active_residents },
  ];

  return (
    <div>
      <Topbar title="Billing" />

      {loading ? (
        <div className="space-y-4">
          <StatCardsSkeleton count={4} />
          <TableSkeleton cols={5} />
        </div>
      ) : error ? (
        <ErrorState compact title="Couldn’t load billing" error={error} onRetry={refetch} />
      ) : (
        <>
          <div className="mb-4 grid gap-4 md:grid-cols-4">
            {stats.map((s) => (
              <div key={s.label} className="rounded-2xl border bg-white p-4">
                <div className="text-sm text-gray-500">{s.label}</div>
                <div className="text-2xl font-semibold">{s.value ?? "-"}</div>
              </div>
            ))}
          </div>

          <div className="mb-3 flex justify-end">
            <Button onClick={refetch} loading={loading}>
              Refresh
            </Button>
          </div>

          {dues.length === 0 ? (
            <EmptyState
              icon="🧾"
              title="No dues yet"
              description="Monthly dues will appear here once they’re generated."
            />
          ) : (
            <Table>
              <thead>
                <tr className="border-b text-left">
                  <th className="p-3">Resident</th>
                  <th className="p-3">Month</th>
                  <th className="p-3">Amount</th>
                  <th className="p-3">Paid</th>
                  <th className="p-3">Remaining</th>
                </tr>
              </thead>
              <tbody>
                {dues.map((due) => (
                  <tr key={due.id} className="border-b">
                    <td className="p-3">#{due.resident}</td>
                    <td className="p-3">
                      {due.year}-{String(due.month).padStart(2, "0")}
                    </td>
                    <td className="p-3">{due.amount}</td>
                    <td className="p-3">{due.paid_amount}</td>
                    <td className="p-3 font-medium">{due.remaining}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </>
      )}
    </div>
  );
}
