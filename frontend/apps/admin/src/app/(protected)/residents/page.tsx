"use client";

import { useState } from "react";
import { createResident, listResidents } from "@/features/residents/residents.api";
import type { Resident } from "@/features/residents/residents.types";
import { Topbar } from "@/components/shell/Topbar";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { Table } from "@hostel/ui";
import { TableSkeleton } from "@hostel/ui";
import { EmptyState } from "@hostel/ui";
import { ErrorState } from "@hostel/ui";
import { useApi } from "@hostel/hooks";
import { useToast } from "@hostel/ui";

export default function ResidentsPage() {
  const toast = useToast();

  const { data, loading, error, refetch } = useApi<Resident[]>(() => listResidents(), {
    deps: [],
  });
  const rows = data ?? [];

  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [guardianPhone, setGuardianPhone] = useState("");
  const [monthlyFee, setMonthlyFee] = useState("0");
  const [saving, setSaving] = useState(false);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    try {
      await createResident({
        full_name: fullName,
        phone,
        guardian_phone: guardianPhone,
        monthly_fee: monthlyFee,
        security_deposit: "0",
        status: "active",
        join_date: new Date().toISOString().slice(0, 10),
      });
      toast.success(`${fullName} was admitted.`, "Resident added");
      setFullName("");
      setPhone("");
      setGuardianPhone("");
      setMonthlyFee("0");
      await refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add resident.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <Topbar title="Residents" />

      <form onSubmit={save} className="mb-4 grid gap-3 rounded-2xl border bg-white p-4 md:grid-cols-5">
        <Input placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
        <Input placeholder="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
        <Input
          placeholder="Guardian phone"
          value={guardianPhone}
          onChange={(e) => setGuardianPhone(e.target.value)}
        />
        <Input placeholder="Monthly fee" value={monthlyFee} onChange={(e) => setMonthlyFee(e.target.value)} />
        <Button type="submit" loading={saving}>
          {saving ? "Adding…" : "Add"}
        </Button>
      </form>

      {loading ? (
        <TableSkeleton cols={4} />
      ) : error ? (
        <ErrorState compact title="Couldn’t load residents" error={error} onRetry={refetch} />
      ) : rows.length === 0 ? (
        <EmptyState
          icon="🛏️"
          title="No residents yet"
          description="Add your first resident using the form above."
        />
      ) : (
        <Table>
          <thead>
            <tr className="border-b text-left">
              <th className="p-3">Name</th>
              <th className="p-3">Phone</th>
              <th className="p-3">Monthly Fee</th>
              <th className="p-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((resident) => (
              <tr key={resident.id} className="border-b">
                <td className="p-3 font-medium">{resident.full_name}</td>
                <td className="p-3">{resident.phone || "-"}</td>
                <td className="p-3">{resident.monthly_fee}</td>
                <td className="p-3">{resident.status}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
