"use client";

import { useMemo, useState } from "react";
import { Topbar } from "@/shared/ui/Topbar";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { Table } from "@/shared/ui/Table";
import { loadState } from "@/features/hostels/store";
import { isoToday, ymToday } from "@/shared/lib/dates";
import { dailyCollections, sumPayments, sumExpenses } from "@/shared/lib/finance";
import { downloadCSV } from "@/shared/lib/exporters";

export default function ReportsPage() {
  const [tick, setTick] = useState(0);
  const [month, setMonth] = useState(ymToday());
  const [date, setDate] = useState(isoToday());

  const state = useMemo(() => loadState(), [tick]);

  const monthCollections = sumPayments(state.payments, month, false);
  const monthExpenses = sumExpenses(state.expenses, month);
  const monthNet = monthCollections - monthExpenses;

  const todayCollections = dailyCollections(state.payments, date);

  function exportPaymentsCSV() {
    const rows = state.payments
      .filter(p => p.date.startsWith(month))
      .map(p => {
        const s = state.students.find(x => x.id === p.studentId);
        return {
          date: p.date,
          student: s?.fullName ?? "Unknown",
          amount: p.amount,
          note: p.note ?? "",
        };
      });

    downloadCSV(`payments_${month}.csv`, rows);
  }

  function exportExpensesCSV() {
    const rows = state.expenses
      .filter(e => e.date.startsWith(month))
      .map(e => ({
        date: e.date,
        category: e.category,
        amount: e.amount,
        note: e.note ?? "",
      }));

    downloadCSV(`expenses_${month}.csv`, rows);
  }

  function exportStudentsCSV() {
    const rows = state.students.map(s => {
      const room = state.rooms.find(r => r.id === s.roomId);
      const bed = state.beds.find(b => b.id === s.bedId);
      return {
        name: s.fullName,
        phone: s.phone ?? "",
        status: s.status,
        room: room?.label ?? "",
        bed: bed?.label ?? "",
        monthlyFee: s.monthlyFee,
        joinedAt: s.joinedAt,
      };
    });

    downloadCSV(`students.csv`, rows);
  }

  return (
    <div>
      <Topbar title="Reports & Export" />

      <div className="grid md:grid-cols-2 gap-4 mb-4">
        <div className="border border-gray-200 rounded-2xl bg-white p-4">
          <div className="text-sm text-gray-600 mb-2">Daily Report</div>
          <Input label="Date" value={date} onChange={(e) => setDate(e.target.value)} />
          <div className="mt-3 text-lg">
            Collections: <b>{todayCollections}</b>
          </div>
        </div>

        <div className="border border-gray-200 rounded-2xl bg-white p-4">
          <div className="text-sm text-gray-600 mb-2">Monthly Summary</div>
          <Input label="Month (YYYY-MM)" value={month} onChange={(e) => setMonth(e.target.value)} />
          <div className="mt-3 grid gap-1">
            <div>Collections: <b>{monthCollections}</b></div>
            <div>Expenses: <b>{monthExpenses}</b></div>
            <div>Net: <b>{monthNet}</b></div>
          </div>

          <div className="flex flex-wrap gap-2 mt-3">
            <Button onClick={exportPaymentsCSV}>Export Payments (CSV)</Button>
            <Button variant="ghost" onClick={exportExpensesCSV}>Export Expenses (CSV)</Button>
            <Button variant="ghost" onClick={exportStudentsCSV}>Export Students (CSV)</Button>
          </div>
          <div className="text-xs text-gray-500 mt-2">
            CSV opens in Excel. Later we can add real .xlsx.
          </div>
        </div>
      </div>

      <Table>
        <thead>
          <tr className="text-left border-b border-gray-200">
            <th className="p-3">Latest Activity Logs</th>
            <th className="p-3">Time</th>
          </tr>
        </thead>
        <tbody>
          {state.audit.slice(0, 20).map(a => (
            <tr key={a.id} className="border-b border-gray-100">
              <td className="p-3">
                <div className="font-medium">{a.action}</div>
                <div className="text-xs text-gray-600">{a.message}</div>
              </td>
              <td className="p-3 text-sm">{a.at}</td>
            </tr>
          ))}
          {state.audit.length === 0 ? (
            <tr><td className="p-4 text-gray-500" colSpan={2}>No logs yet.</td></tr>
          ) : null}
        </tbody>
      </Table>
    </div>
  );
}