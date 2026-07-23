"use client";

import { useEffect, useState } from "react";
import { approveLeave, createLeaveRequest, listLeaveRequests, rejectLeave } from "@/features/operations/api";
import type { LeaveRequest } from "@/features/operations/types";
import { getStudents } from "@/features/students/api/student.api";
import type { Student } from "@/features/students/types/student.types";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { Table } from "@hostel/ui";
import { Topbar } from "@/components/shell/Topbar";

export default function LeavePage() {
  const [rows, setRows] = useState<LeaveRequest[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [status, setStatus] = useState("");
  const [message, setMessage] = useState("");
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    student: "",
    start_date: today,
    end_date: today,
    reason: "",
  });

  async function refresh() {
    try {
      const [leaveRows, studentRows] = await Promise.all([
        listLeaveRequests({ status: status || undefined }),
        getStudents({ status: "ACTIVE" }),
      ]);
      setRows(leaveRows);
      setStudents(studentRows);
    } catch (err: any) {
      setMessage(err?.message || "Failed to load leave requests.");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    await createLeaveRequest({ ...form, student: form.student || null });
    setForm({ student: "", start_date: today, end_date: today, reason: "" });
    setMessage("Leave request created.");
    await refresh();
  }

  async function decide(id: string, approved: boolean) {
    if (approved) await approveLeave(id, "Approved from leave screen.");
    else await rejectLeave(id, "Rejected from leave screen.");
    setMessage(approved ? "Leave approved." : "Leave rejected.");
    await refresh();
  }

  return (
    <div>
      <Topbar title="Leave Requests" />
      {message ? <div className="mb-3 text-sm text-zinc-700">{message}</div> : null}

      <form onSubmit={save} className="mb-4 grid gap-3 rounded-2xl border bg-white p-4 md:grid-cols-5">
        <select className="rounded-lg border border-gray-200 px-3 py-2" value={form.student} onChange={(e) => setForm({ ...form, student: e.target.value })} required>
          <option value="">Student</option>
          {students.map((student) => (
            <option key={student.id} value={student.id}>{student.full_name}</option>
          ))}
        </select>
        <Input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} required />
        <Input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} required />
        <Input placeholder="Reason" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
        <Button type="submit">Request</Button>
      </form>

      <div className="mb-3 flex gap-2">
        <select className="rounded-lg border border-gray-200 px-3 py-2 text-sm" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="PENDING">Pending</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
        </select>
        <Button variant="ghost" onClick={refresh}>Refresh</Button>
      </div>

      <Table>
        <thead>
          <tr className="border-b text-left">
            <th className="p-3">Student</th>
            <th className="p-3">Dates</th>
            <th className="p-3">Reason</th>
            <th className="p-3">Status</th>
            <th className="p-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b">
              <td className="p-3">{row.student_name || row.resident_name || "-"}</td>
              <td className="p-3">{row.start_date} to {row.end_date}</td>
              <td className="p-3">{row.reason || "-"}</td>
              <td className="p-3">{row.status}</td>
              <td className="p-3">
                {row.status === "PENDING" ? (
                  <div className="flex gap-2">
                    <Button onClick={() => decide(row.id, true)}>Approve</Button>
                    <Button variant="danger" onClick={() => decide(row.id, false)}>Reject</Button>
                  </div>
                ) : row.decision_note || "-"}
              </td>
            </tr>
          ))}
          {!rows.length ? (
            <tr><td className="p-6 text-center text-sm text-zinc-500" colSpan={5}>No leave requests.</td></tr>
          ) : null}
        </tbody>
      </Table>
    </div>
  );
}
