"use client";

import { useCallback, useEffect, useState } from "react";
import { listAttendance, markAttendance, type Attendance } from "@/features/attendance/api";
import { OfflineQueuedError } from "@hostel/api";
import { listResidents } from "@/features/residents/residents.api";
import type { Resident } from "@/features/residents/residents.types";
import { Topbar } from "@/components/shell/Topbar";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { Table } from "@hostel/ui";
import { useToast } from "@hostel/ui";

export default function AttendancePage() {
  const toast = useToast();
  const [residents, setResidents] = useState<Resident[]>([]);
  const [rows, setRows] = useState<Attendance[]>([]);
  const [resident, setResident] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [status, setStatus] = useState<Attendance["status"]>("present");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [residentRows, attendanceRows] = await Promise.all([
        listResidents({ status: "active" }),
        listAttendance({ date }),
      ]);
      setResidents(residentRows);
      setRows(attendanceRows);
    } catch (err: any) {
      setError(err?.message || "Failed to load attendance.");
    }
  }, [date]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await markAttendance({ resident, date, status, note });
      toast.success("Attendance marked.");
    } catch (err) {
      if (err instanceof OfflineQueuedError) {
        toast.info("You're offline — attendance saved and will sync automatically.");
      } else {
        toast.error(err instanceof Error ? err.message : "Failed to mark attendance.");
        return;
      }
    }
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
