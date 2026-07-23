"use client";

import { useEffect, useState } from "react";
import { checkoutVisitor, createVisitor, listVisitors } from "@/features/operations/api";
import type { VisitorLog } from "@/features/operations/types";
import { getStudents } from "@/features/students/api/student.api";
import type { Student } from "@/features/students/types/student.types";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { Table } from "@hostel/ui";
import { Topbar } from "@/components/shell/Topbar";

export default function VisitorsPage() {
  const [rows, setRows] = useState<VisitorLog[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    student: "",
    visitor_name: "",
    visitor_phone: "",
    relation: "",
    purpose: "",
  });

  async function refresh() {
    try {
      const [visitorRows, studentRows] = await Promise.all([listVisitors(), getStudents({ status: "ACTIVE" })]);
      setRows(visitorRows);
      setStudents(studentRows);
    } catch (err: any) {
      setMessage(err?.message || "Failed to load visitor log.");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    await createVisitor({ ...form, student: form.student || null });
    setForm({ student: "", visitor_name: "", visitor_phone: "", relation: "", purpose: "" });
    setMessage("Visitor checked in.");
    await refresh();
  }

  async function checkout(id: string) {
    await checkoutVisitor(id);
    setMessage("Visitor checked out.");
    await refresh();
  }

  return (
    <div>
      <Topbar title="Visitor Log" />
      {message ? <div className="mb-3 text-sm text-zinc-700">{message}</div> : null}

      <form onSubmit={save} className="mb-4 grid gap-3 rounded-2xl border bg-white p-4 md:grid-cols-5">
        <select className="rounded-lg border border-gray-200 px-3 py-2" value={form.student} onChange={(e) => setForm({ ...form, student: e.target.value })} required>
          <option value="">Resident</option>
          {students.map((student) => (
            <option key={student.id} value={student.id}>{student.full_name}</option>
          ))}
        </select>
        <Input placeholder="Visitor name" value={form.visitor_name} onChange={(e) => setForm({ ...form, visitor_name: e.target.value })} required />
        <Input placeholder="Phone" value={form.visitor_phone} onChange={(e) => setForm({ ...form, visitor_phone: e.target.value })} />
        <Input placeholder="Relation" value={form.relation} onChange={(e) => setForm({ ...form, relation: e.target.value })} />
        <Button type="submit">Check In</Button>
        <Input className="md:col-span-5" placeholder="Purpose" value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} />
      </form>

      <Table>
        <thead>
          <tr className="border-b text-left">
            <th className="p-3">Visitor</th>
            <th className="p-3">Resident</th>
            <th className="p-3">Purpose</th>
            <th className="p-3">Check In</th>
            <th className="p-3">Check Out</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b">
              <td className="p-3">
                <div className="font-medium">{row.visitor_name}</div>
                <div className="text-xs text-zinc-500">{row.visitor_phone || row.relation || "-"}</div>
              </td>
              <td className="p-3">{row.student_name || row.resident_name || "-"}</td>
              <td className="p-3">{row.purpose || "-"}</td>
              <td className="p-3">{row.check_in_at ? new Date(row.check_in_at).toLocaleString() : "-"}</td>
              <td className="p-3">
                {row.check_out_at ? new Date(row.check_out_at).toLocaleString() : <Button variant="ghost" onClick={() => checkout(row.id)}>Check Out</Button>}
              </td>
            </tr>
          ))}
          {!rows.length ? (
            <tr><td className="p-6 text-center text-sm text-zinc-500" colSpan={5}>No visitor records.</td></tr>
          ) : null}
        </tbody>
      </Table>
    </div>
  );
}
