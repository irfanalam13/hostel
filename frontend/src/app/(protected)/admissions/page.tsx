"use client";

import { useEffect, useMemo, useState } from "react";
import { approveAdmission, createAdmission, listAdmissions, rejectAdmission } from "@/features/admissions/api";
import type { AdmissionRequest } from "@/features/admissions/types";
import { getBeds } from "@/features/beds/api/bed.api";
import type { Bed } from "@/features/beds/types/bed.types";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { Table } from "@/shared/ui/Table";
import { Topbar } from "@/shared/ui/Topbar";

export default function AdmissionsPage() {
  const [rows, setRows] = useState<AdmissionRequest[]>([]);
  const [beds, setBeds] = useState<Bed[]>([]);
  const [status, setStatus] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [bedByRequest, setBedByRequest] = useState<Record<string, string>>({});
  const [form, setForm] = useState({
    full_name: "",
    phone: "",
    guardian_name: "",
    guardian_phone: "",
    address: "",
    preferred_join_date: new Date().toISOString().slice(0, 10),
    requested_bed: "",
    notes: "",
  });

  const availableBeds = useMemo(
    () => beds.filter((bed) => bed.status === "AVAILABLE"),
    [beds]
  );

  async function refresh() {
    setLoading(true);
    setMessage("");
    try {
      const [admissions, bedRows] = await Promise.all([
        listAdmissions({ status: status || undefined }),
        getBeds(),
      ]);
      setRows(admissions);
      setBeds(bedRows);
    } catch (err: any) {
      setMessage(err?.message || "Failed to load admissions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    await createAdmission({
      ...form,
      requested_bed: form.requested_bed || null,
      preferred_join_date: form.preferred_join_date || null,
    });
    setForm({
      full_name: "",
      phone: "",
      guardian_name: "",
      guardian_phone: "",
      address: "",
      preferred_join_date: new Date().toISOString().slice(0, 10),
      requested_bed: "",
      notes: "",
    });
    setMessage("Admission request created.");
    await refresh();
  }

  async function approve(row: AdmissionRequest) {
    await approveAdmission(row.id, {
      bed: bedByRequest[row.id] || row.requested_bed || undefined,
      join_date: row.preferred_join_date || undefined,
    });
    setMessage("Admission approved and student record created.");
    await refresh();
  }

  async function reject(row: AdmissionRequest) {
    await rejectAdmission(row.id, "Rejected from admissions screen.");
    setMessage("Admission rejected.");
    await refresh();
  }

  return (
    <div>
      <Topbar title="Admissions" />
      {message ? <div className="mb-3 text-sm text-zinc-700">{message}</div> : null}

      <form onSubmit={save} className="mb-4 grid gap-3 rounded-2xl border bg-white p-4 md:grid-cols-4">
        <Input label="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
        <Input label="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} required />
        <Input label="Guardian" value={form.guardian_name} onChange={(e) => setForm({ ...form, guardian_name: e.target.value })} />
        <Input label="Guardian phone" value={form.guardian_phone} onChange={(e) => setForm({ ...form, guardian_phone: e.target.value })} />
        <Input label="Join date" type="date" value={form.preferred_join_date} onChange={(e) => setForm({ ...form, preferred_join_date: e.target.value })} />
        <Input label="Address" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
        <select className="rounded-lg border border-gray-200 px-3 py-2" value={form.requested_bed} onChange={(e) => setForm({ ...form, requested_bed: e.target.value })}>
          <option value="">Requested bed</option>
          {availableBeds.map((bed) => (
            <option key={bed.id} value={bed.id}>
              {bed.code || `${bed.room_detail?.room_no || bed.room}-${bed.bed_no}`}
            </option>
          ))}
        </select>
        <div className="flex items-end">
          <Button type="submit" className="w-full">Create</Button>
        </div>
      </form>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <select className="rounded-lg border border-gray-200 px-3 py-2 text-sm" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="PENDING">Pending</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
        </select>
        <Button variant="ghost" onClick={refresh} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </Button>
      </div>

      <Table>
        <thead>
          <tr className="border-b text-left">
            <th className="p-3">Applicant</th>
            <th className="p-3">Guardian</th>
            <th className="p-3">Requested Bed</th>
            <th className="p-3">Status</th>
            <th className="p-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-b">
              <td className="p-3">
                <div className="font-medium">{row.full_name}</div>
                <div className="text-xs text-zinc-500">{row.phone}</div>
              </td>
              <td className="p-3">{row.guardian_name || "-"} {row.guardian_phone ? `(${row.guardian_phone})` : ""}</td>
              <td className="p-3">{row.requested_bed_code || "-"}</td>
              <td className="p-3">{row.status}</td>
              <td className="p-3">
                {row.status === "PENDING" ? (
                  <div className="flex flex-wrap gap-2">
                    <select className="rounded-lg border border-gray-200 px-2 py-1 text-sm" value={bedByRequest[row.id] || ""} onChange={(e) => setBedByRequest({ ...bedByRequest, [row.id]: e.target.value })}>
                      <option value="">Bed</option>
                      {availableBeds.map((bed) => (
                        <option key={bed.id} value={bed.id}>
                          {bed.code || `${bed.room_detail?.room_no || bed.room}-${bed.bed_no}`}
                        </option>
                      ))}
                    </select>
                    <Button onClick={() => approve(row)}>Approve</Button>
                    <Button variant="danger" onClick={() => reject(row)}>Reject</Button>
                  </div>
                ) : (
                  row.student_name || row.decision_note || "-"
                )}
              </td>
            </tr>
          ))}
          {!rows.length && !loading ? (
            <tr>
              <td className="p-6 text-center text-sm text-zinc-500" colSpan={5}>No admission requests found.</td>
            </tr>
          ) : null}
        </tbody>
      </Table>
    </div>
  );
}
