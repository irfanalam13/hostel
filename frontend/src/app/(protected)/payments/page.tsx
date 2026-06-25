"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthed } from "@/shared/lib/auth";
import { Topbar } from "@/shared/ui/Topbar";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { Modal } from "@/shared/ui/Modal";
import { Table } from "@/shared/ui/Table";
import { useToast } from "@/shared/ui/toast/ToastProvider";
import { addPayment, loadState } from "@/features/hostels/store";
import { isoToday, ymToday } from "@/shared/lib/dates";
import { computeDues } from "@/shared/lib/finance";

export default function PaymentsPage() {
  const router = useRouter();
  const toast = useToast();
  const [tick, setTick] = useState(0);
  const [open, setOpen] = useState(false);

  const [month, setMonth] = useState(ymToday());
  const [date, setDate] = useState(isoToday());
  const [studentId, setStudentId] = useState("");
  const [amount, setAmount] = useState<number>(0);
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!isAuthed()) router.replace("/login");
  }, [router]);

  const state = useMemo(() => loadState(), [tick]);
  const activeStudents = state.students.filter(s => s.status === "active");

  const { dues, totalDue, studentsDue } = computeDues(activeStudents, state.payments, month);

  function openAdd() {
    setDate(isoToday());
    setStudentId(activeStudents[0]?.id ?? "");
    setAmount(0);
    setNote("");
    setOpen(true);
  }

  function save() {
    if (!studentId) return toast.warning("Please select a student.");
    if (amount <= 0) return toast.warning("Amount must be greater than 0.");

    addPayment({ date, studentId, amount, note });
    toast.success("Payment recorded.");
    setOpen(false);
    setTick(t => t + 1);
  }

  return (
    <div>
      <Topbar />

      <div className="flex flex-wrap gap-2 justify-between items-end mb-3">
        <div>
          <div className="text-lg font-semibold">Payments</div>
          <div className="text-sm text-gray-600">
            Month {month} — Total Due: <b>{totalDue}</b> | Students Due: <b>{studentsDue}</b>
          </div>
        </div>

        <div className="flex gap-2 items-end">
          <Input label="Month (YYYY-MM)" value={month} onChange={(e) => setMonth(e.target.value)} />
          <Button onClick={openAdd}>Add Payment</Button>
        </div>
      </div>

      <Table>
        <thead>
          <tr className="text-left border-b border-gray-200">
            <th className="p-3">Student</th>
            <th className="p-3">Monthly Fee</th>
            <th className="p-3">Paid</th>
            <th className="p-3">Due</th>
          </tr>
        </thead>
        <tbody>
          {dues.map(d => (
            <tr key={d.studentId} className="border-b border-gray-100">
              <td className="p-3">{d.name}</td>
              <td className="p-3">{d.monthlyFee}</td>
              <td className="p-3">{d.paid}</td>
              <td className="p-3"><b>{d.due}</b></td>
            </tr>
          ))}
          {dues.length === 0 ? (
            <tr><td className="p-4 text-gray-500" colSpan={4}>No active students.</td></tr>
          ) : null}
        </tbody>
      </Table>

      <Modal open={open} title="Add Payment" onClose={() => setOpen(false)}>
        <div className="grid gap-3">
          <Input label="Date" value={date} onChange={(e) => setDate(e.target.value)} />

          <label className="block">
            <div className="text-sm mb-1 text-gray-700">Student</div>
            <select
              className="w-full px-3 py-2 rounded-lg border border-gray-200"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
            >
              {activeStudents.map(s => (
                <option key={s.id} value={s.id}>
                  {s.fullName} (
                  {state.rooms.find((room) => room.id === s.roomId)?.label || "-"} /{" "}
                  {state.beds.find((bed) => bed.id === s.bedId)?.label || "-"})
                </option>
              ))}
            </select>
          </label>

          <Input label="Amount" type="number" value={String(amount)} onChange={(e) => setAmount(Number(e.target.value))} />
          <Input label="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={save}>Save</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
