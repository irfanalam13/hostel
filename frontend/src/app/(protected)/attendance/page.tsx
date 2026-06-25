"use client";

import { useEffect, useState } from "react";
import { api } from "@/shared/api/apiClient";
import { listResidents } from "@/features/residents/residents.api";
import type { Resident } from "@/features/residents/residents.types";
import { Topbar } from "@/shared/ui/Topbar";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { Table } from "@/shared/ui/Table";

type Attendance = {
  id: number;
  resident: string;
  date: string;
  status: "present" | "absent" | "went_home";
  note?: string;
};

export default function AttendancePage() {
  const [residents, setResidents] = useState<Resident[]>([]);
  const [rows, setRows] = useState<Attendance[]>([]);
  const [resident, setResident] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [status, setStatus] = useState<Attendance["status"]>("present");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    setError("");
    try {
      const [residentRows, attendanceRes] = await Promise.all([
        listResidents({ status: "active" }),
        api.get<Attendance[]>("/attendance/", { params: { date } }),
      ]);
      setResidents(residentRows);
      setRows(attendanceRes.data);
    } catch (err: any) {
      setError(err?.message || "Failed to load attendance.");
    }
  }

  useEffect(() => {
    refresh();
  }, [date]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    await api.post<Attendance>("/attendance/", {
      resident,
      date,
      status,
      note,
    });
    setNote("");
    await refresh();
  }

  return (
    <div>
      <Topbar title="Attendance" />
      {error ? <div className="mb-3 text-sm text-red-600">{error}</div> : null}

      <form onSubmit={save} className="rounded-2xl border bg-white p-4 mb-4 grid gap-3 md:grid-cols-5">
        <select
          className="px-3 py-2 rounded-lg border border-gray-200"
          value={resident}
          onChange={(e) => setResident(e.target.value)}
          required
        >
          <option value="">Resident</option>
          {residents.map((item) => (
            <option key={item.id} value={item.id}>
              {item.full_name}
            </option>
          ))}
        </select>
        <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
        <select
          className="px-3 py-2 rounded-lg border border-gray-200"
          value={status}
          onChange={(e) => setStatus(e.target.value as Attendance["status"])}
        >
          <option value="present">Present</option>
          <option value="absent">Absent</option>
          <option value="went_home">Went Home</option>
        </select>
        <Input placeholder="Note" value={note} onChange={(e) => setNote(e.target.value)} />
        <Button type="submit">Mark</Button>
      </form>

      <Table>
        <thead>
          <tr className="text-left border-b">
            <th className="p-3">Resident</th>
            <th className="p-3">Date</th>
            <th className="p-3">Status</th>
            <th className="p-3">Note</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b">
              <td className="p-3">{residents.find((item) => item.id === row.resident)?.full_name || `#${row.resident}`}</td>
              <td className="p-3">{row.date}</td>
              <td className="p-3">{row.status}</td>
              <td className="p-3">{row.note || "-"}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}
