"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createStudent } from "../api/student.api";
import type { Student } from "../types/student.types";

type StudentFormState = Pick<Student, "full_name" | "phone" | "guardian_phone" | "status"> & {
  join_date: string;
  address: string;
  guardian_name: string;
};

export default function StudentForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [form, setForm] = useState<StudentFormState>({
    full_name: "",
    phone: "",
    guardian_phone: "",
    guardian_name: "",
    address: "",
    join_date: new Date().toISOString().slice(0, 10),
    status: "ACTIVE",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await createStudent(form);
      router.push("/students");
    } catch (err: any) {
      setError(err?.message || "Failed to save student.");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
      {error ? <div className="text-sm text-red-600">{error}</div> : null}

      <input
        placeholder="Full Name"
        className="border p-2 w-full rounded"
        value={form.full_name}
        onChange={(e) => setForm({ ...form, full_name: e.target.value })}
        required
      />

      <input
        placeholder="Phone"
        className="border p-2 w-full rounded"
        value={form.phone}
        onChange={(e) => setForm({ ...form, phone: e.target.value })}
        required
      />

      <input
        placeholder="Guardian Name"
        className="border p-2 w-full rounded"
        value={form.guardian_name}
        onChange={(e) => setForm({ ...form, guardian_name: e.target.value })}
      />

      <input
        placeholder="Guardian Phone"
        className="border p-2 w-full rounded"
        value={form.guardian_phone}
        onChange={(e) => setForm({ ...form, guardian_phone: e.target.value })}
      />

      <input
        placeholder="Address"
        className="border p-2 w-full rounded"
        value={form.address}
        onChange={(e) => setForm({ ...form, address: e.target.value })}
      />

      <input
        type="date"
        className="border p-2 w-full rounded"
        value={form.join_date}
        onChange={(e) => setForm({ ...form, join_date: e.target.value })}
        required
      />

      <select
        className="border p-2 w-full rounded"
        value={form.status}
        onChange={(e) => setForm({ ...form, status: e.target.value as Student["status"] })}
      >
        <option value="ACTIVE">Active</option>
        <option value="INACTIVE">Inactive</option>
      </select>

      <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">
        Save
      </button>
    </form>
  );
}
