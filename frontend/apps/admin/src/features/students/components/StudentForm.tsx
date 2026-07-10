"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createStudent } from "../api/student.api";
import type { Student } from "../types/student.types";

type StudentFormState = Pick<Student, "full_name" | "phone" | "guardian_phone" | "status"> & {
  join_date: string;
  address: string;
  guardian_name: string;
  name_nepali: string;
  date_of_birth: string;
  gender: NonNullable<Student["gender"]>;
  citizenship_number: string;
  father_name: string;
  mother_name: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  emergency_contact_relation: string;
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
    name_nepali: "",
    date_of_birth: "",
    gender: "OTHER",
    citizenship_number: "",
    father_name: "",
    mother_name: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    emergency_contact_relation: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await createStudent({ ...form, date_of_birth: form.date_of_birth || null });
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
        placeholder="Name (Nepali)"
        className="border p-2 w-full rounded"
        value={form.name_nepali}
        onChange={(e) => setForm({ ...form, name_nepali: e.target.value })}
      />

      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm text-gray-600">
          Date of birth
          <input
            type="date"
            className="border p-2 w-full rounded"
            value={form.date_of_birth}
            onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
          />
        </label>
        <label className="text-sm text-gray-600">
          Gender
          <select
            className="border p-2 w-full rounded"
            value={form.gender}
            onChange={(e) => setForm({ ...form, gender: e.target.value as StudentFormState["gender"] })}
          >
            <option value="MALE">Male</option>
            <option value="FEMALE">Female</option>
            <option value="OTHER">Other</option>
          </select>
        </label>
      </div>

      <input
        placeholder="Citizenship number"
        className="border p-2 w-full rounded"
        value={form.citizenship_number}
        onChange={(e) => setForm({ ...form, citizenship_number: e.target.value })}
      />

      <div className="grid grid-cols-2 gap-3">
        <input
          placeholder="Father's name"
          className="border p-2 w-full rounded"
          value={form.father_name}
          onChange={(e) => setForm({ ...form, father_name: e.target.value })}
        />
        <input
          placeholder="Mother's name"
          className="border p-2 w-full rounded"
          value={form.mother_name}
          onChange={(e) => setForm({ ...form, mother_name: e.target.value })}
        />
      </div>

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

      <div className="grid grid-cols-2 gap-3">
        <input
          placeholder="Emergency contact name"
          className="border p-2 w-full rounded"
          value={form.emergency_contact_name}
          onChange={(e) => setForm({ ...form, emergency_contact_name: e.target.value })}
        />
        <input
          placeholder="Emergency contact phone"
          className="border p-2 w-full rounded"
          value={form.emergency_contact_phone}
          onChange={(e) => setForm({ ...form, emergency_contact_phone: e.target.value })}
        />
      </div>

      <input
        placeholder="Emergency contact relation"
        className="border p-2 w-full rounded"
        value={form.emergency_contact_relation}
        onChange={(e) => setForm({ ...form, emergency_contact_relation: e.target.value })}
      />

      <label className="block text-sm text-gray-600">
        Join date
        <input
          type="date"
          className="border p-2 w-full rounded"
          value={form.join_date}
          onChange={(e) => setForm({ ...form, join_date: e.target.value })}
          required
        />
      </label>

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
