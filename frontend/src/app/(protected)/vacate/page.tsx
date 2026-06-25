"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthed } from "@/shared/lib/auth";
import { Topbar } from "@/shared/ui/Topbar";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { Table } from "@/shared/ui/Table";
import { useToast } from "@/shared/ui/toast/ToastProvider";
import { useConfirm } from "@/shared/ui/ConfirmProvider";
import { loadState, vacateStudentIfCleared } from "@/features/hostels/store";
import { ymToday } from "@/shared/lib/dates";
import { computeDues } from "@/shared/lib/finance";

export default function VacatePage() {
  const router = useRouter();
  const toast = useToast();
  const confirm = useConfirm();
  const [tick, setTick] = useState(0);
  const [month, setMonth] = useState(ymToday());

  useEffect(() => {
    if (!isAuthed()) router.replace("/login");
  }, [router]);

  const state = useMemo(() => loadState(), [tick]);
  const active = state.students.filter(s => s.status === "active");
  const { dues } = computeDues(active, state.payments, month);

  function refresh() { setTick(t => t + 1); }

  async function vacate(studentId: string, due: number) {
    if (due > 0) return toast.warning(`Clear the outstanding due first: ${due}`);
    const ok = await confirm({
      title: "Vacate student",
      message: "Vacate this student? Their bed will be released.",
      confirmText: "Vacate",
    });
    if (!ok) return;
    const res = vacateStudentIfCleared(studentId, month);
    if (!res.ok) return toast.error(res.error || "Could not vacate student.");
    toast.success("Student vacated.");
    refresh();
  }

  return (
    <div>
      <Topbar title="Vacate Students (Clear Dues First)" />

      <div className="flex gap-2 items-end mb-3">
        <Input label="Month (YYYY-MM)" value={month} onChange={(e) => setMonth(e.target.value)} />
      </div>

      <Table>
        <thead>
          <tr className="text-left border-b border-gray-200">
            <th className="p-3">Student</th>
            <th className="p-3">Paid</th>
            <th className="p-3">Due</th>
            <th className="p-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {dues.map(d => (
            <tr key={d.studentId} className="border-b border-gray-100">
              <td className="p-3">{d.name}</td>
              <td className="p-3">{d.paid}</td>
              <td className="p-3"><b>{d.due}</b></td>
              <td className="p-3">
                <Button
                  variant={d.due === 0 ? "primary" : "ghost"}
                  onClick={() => vacate(d.studentId, d.due)}
                >
                  Vacate
                </Button>
              </td>
            </tr>
          ))}
          {!dues.length ? <tr><td className="p-4 text-gray-500" colSpan={4}>No active students.</td></tr> : null}
        </tbody>
      </Table>

      <div className="text-xs text-gray-500 mt-3">
        Rule: Vacating is blocked if due &gt; 0 for the selected month.
      </div>
    </div>
  );
}