"use client";

import { useEffect, useState } from "react";
import { createEntryExit, listEntryExit } from "@/features/operations/api";
import type { EntryExitLog } from "@/features/operations/types";
import { getStudents } from "@/features/students/api/student.api";
import type { Student } from "@/features/students/types/student.types";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { Table } from "@hostel/ui";
import { Topbar } from "@/components/shell/Topbar";

export default function GatePage() {
  const [rows, setRows] = useState<EntryExitLog[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    student: "",
    direction: "OUT",
    purpose: "",
    note: "",
  });

  async function refresh() {
    try {
      const [logRows, studentRows] = await Promise.all([listEntryExit(), getStudents({ status: "ACTIVE" })]);
      setRows(logRows);
      setStudents(studentRows);
    } catch (err: any) {
      setMessage(err?.message || "Failed to load gate register.");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    await createEntryExit({
      ...form,
      student: form.student || null,
      direction: form.direction as EntryExitLog["direction"],
    });
    setForm({ student: "", direction: "OUT", purpose: "", note: "" });
    setMessage("Gate log saved.");
    await refresh();
  }

  return (
    <div>
      <Topbar title="Gate Register" />
      {message ? <div className="mb-3 text-sm text-zinc-700">{message}</div> : null}

      <form onSubmit={save} className="mb-4 grid gap-3 rounded-2xl border bg-white p-4 md:grid-cols-5">
        <select className="rounded-lg border border-gray-200 px-3 py-2" value={form.student} onChange={(e) => setForm({ ...form, student: e.target.value })} required>
          <option value="">Student</option>
          {students.map((student) => (
            <option key={student.id} value={student.id}>{student.full_name}</option>
          ))}
        </select>
        <select className="rounded-lg border border-gray-200 px-3 py-2" value={form.direction} onChange={(e) => setForm({ ...form, direction: e.target.value })}>
          <option value="OUT">Exit</option>
          <option value="IN">Entry</option>
        </select>
        <Input placeholder="Purpose" value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} />
        <Input placeholder="Note" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
        <Button type="submit">Save</Button>
      </form>

      <Table>
        <thead>
          <tr className="border-b text-left">
            <th className="p-3">Student</th>
            <th className="p-3">Direction</th>
            <th className="p-3">Time</th>
            <th className="p-3">Purpose</th>
            <th className="p-3">Note</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b">
              <td className="p-3">{row.student_name || row.resident_name || "-"}</td>
              <td className="p-3">{row.direction}</td>
              <td className="p-3">{row.event_at ? new Date(row.event_at).toLocaleString() : "-"}</td>
              <td className="p-3">{row.purpose || "-"}</td>
              <td className="p-3">{row.note || "-"}</td>
            </tr>
          ))}
          {!rows.length ? (
            <tr><td className="p-6 text-center text-sm text-zinc-500" colSpan={5}>No gate entries yet.</td></tr>
          ) : null}
        </tbody>
      </Table>
    </div>
  );
}
