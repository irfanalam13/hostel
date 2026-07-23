"use client";

import { useEffect, useState } from "react";
import { createComplaint, listComplaints, setComplaintStatus } from "@/features/complaints/api";
import type { Complaint, ComplaintStatus } from "@/features/complaints/types";
import { getStudents } from "@/features/students/api/student.api";
import type { Student } from "@/features/students/types/student.types";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { Table } from "@hostel/ui";
import { Topbar } from "@/components/shell/Topbar";

export default function ComplaintsPage() {
  const [rows, setRows] = useState<Complaint[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [status, setStatus] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    student: "",
    title: "",
    category: "General",
    priority: "MEDIUM",
    description: "",
  });

  async function refresh() {
    try {
      const [complaints, studentRows] = await Promise.all([
        listComplaints({ status: status || undefined }),
        getStudents({ status: "ACTIVE" }),
      ]);
      setRows(complaints);
      setStudents(studentRows);
    } catch (err: any) {
      setMessage(err?.message || "Failed to load complaints.");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    await createComplaint({
      ...form,
      student: form.student || null,
      priority: form.priority as Complaint["priority"],
    });
    setForm({ student: "", title: "", category: "General", priority: "MEDIUM", description: "" });
    setMessage("Complaint created.");
    await refresh();
  }

  async function changeStatus(id: string, next: ComplaintStatus) {
    await setComplaintStatus(id, next);
    setMessage(`Complaint moved to ${next}.`);
    await refresh();
  }

  return (
    <div>
      <Topbar title="Complaints" />
      {message ? <div className="mb-3 text-sm text-zinc-700">{message}</div> : null}

      <form onSubmit={save} className="mb-4 grid gap-3 rounded-2xl border bg-white p-4 md:grid-cols-5">
        <select className="rounded-lg border border-gray-200 px-3 py-2" value={form.student} onChange={(e) => setForm({ ...form, student: e.target.value })}>
          <option value="">Student</option>
          {students.map((student) => (
            <option key={student.id} value={student.id}>{student.full_name}</option>
          ))}
        </select>
        <Input placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
        <Input placeholder="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
        <select className="rounded-lg border border-gray-200 px-3 py-2" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
          <option value="LOW">Low</option>
          <option value="MEDIUM">Medium</option>
          <option value="HIGH">High</option>
          <option value="URGENT">Urgent</option>
        </select>
        <Button type="submit">Create</Button>
        <textarea className="md:col-span-5 rounded-lg border border-gray-200 px-3 py-2" placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      </form>

      <div className="mb-3 flex gap-2">
        <select className="rounded-lg border border-gray-200 px-3 py-2 text-sm" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="OPEN">Open</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="RESOLVED">Resolved</option>
          <option value="CLOSED">Closed</option>
        </select>
        <Button variant="ghost" onClick={refresh}>Refresh</Button>
      </div>

      <Table>
        <thead>
          <tr className="border-b text-left">
            <th className="p-3">Ticket</th>
            <th className="p-3">Student</th>
            <th className="p-3">Priority</th>
            <th className="p-3">Status</th>
            <th className="p-3">Workflow</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b">
              <td className="p-3">
                <div className="font-medium">{row.title}</div>
                <div className="text-xs text-zinc-500">{row.category}</div>
              </td>
              <td className="p-3">{row.student_name || row.resident_name || "-"}</td>
              <td className="p-3">{row.priority}</td>
              <td className="p-3">{row.status}</td>
              <td className="p-3">
                <div className="flex flex-wrap gap-2">
                  <Button variant="ghost" onClick={() => changeStatus(row.id, "IN_PROGRESS")}>Start</Button>
                  <Button variant="ghost" onClick={() => changeStatus(row.id, "RESOLVED")}>Resolve</Button>
                  <Button variant="ghost" onClick={() => changeStatus(row.id, "CLOSED")}>Close</Button>
                </div>
              </td>
            </tr>
          ))}
          {!rows.length ? (
            <tr><td className="p-6 text-center text-sm text-zinc-500" colSpan={5}>No complaints found.</td></tr>
          ) : null}
        </tbody>
      </Table>
    </div>
  );
}
