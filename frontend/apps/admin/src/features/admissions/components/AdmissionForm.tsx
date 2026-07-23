"use client";

import React, { useState } from "react";
import { Input } from "@hostel/ui";
import { Select } from "@hostel/ui";
import { Textarea } from "@hostel/ui";
import { Button } from "@hostel/ui";
import type { AdmissionRequest } from "../types";
import {
  BLOOD_OPTIONS,
  FOOD_OPTIONS,
  GENDER_OPTIONS,
  LEVEL_OPTIONS,
  MARITAL_OPTIONS,
  PAYMENT_STATUS_OPTIONS,
  ROOM_TYPE_OPTIONS,
  SOURCE_OPTIONS,
  TIMING_OPTIONS,
} from "../types";

type FormState = Partial<AdmissionRequest>;

function defaults(initial?: FormState): FormState {
  return {
    source: "WALK_IN",
    gender: "MALE",
    nationality: "Nepal",
    blood_group: "UNKNOWN",
    marital_status: "SINGLE",
    current_level: "BACHELOR",
    class_timing: "DAY",
    food_preference: "NON_VEGETARIAN",
    preferred_room_type: "DOUBLE",
    payment_status: "PENDING",
    hostel_stay_duration: 12,
    ...initial,
  };
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4">
      <legend className="px-2 text-sm font-semibold text-[var(--accent)]">{title}</legend>
      <div className="grid gap-3 md:grid-cols-3">{children}</div>
    </fieldset>
  );
}

export function AdmissionForm({
  initial,
  submitLabel = "Create application",
  onSubmit,
  onCancel,
}: {
  initial?: FormState;
  submitLabel?: string;
  onSubmit: (payload: FormState) => Promise<void> | void;
  onCancel?: () => void;
}) {
  const [form, setForm] = useState<FormState>(defaults(initial));
  const [saving, setSaving] = useState(false);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function field(key: keyof FormState) {
    return {
      value: (form[key] as string | number | undefined) ?? "",
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
        set(key, e.target.value as FormState[typeof key]),
    };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      // Strip empty date strings to null so DRF accepts them.
      const payload: FormState = { ...form };
      (["date_of_birth", "citizenship_issue_date", "expected_checkout_date", "booking_date"] as const).forEach(
        (k) => {
          if (!payload[k]) payload[k] = null;
        }
      );
      await onSubmit(payload);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Section title="1. Application Information">
        <Select label="Source" options={SOURCE_OPTIONS} {...field("source")} />
        <Input label="Form number" {...field("form_number")} />
        <Input label="Application date" type="date" {...field("application_date")} />
      </Section>

      <Section title="2. Student Profile">
        <Input label="Full name (English)" {...field("full_name")} required />
        <Input label="Name (Nepali)" {...field("name_nepali")} />
        <Input label="Date of birth" type="date" {...field("date_of_birth")} />
        <Select label="Gender" options={GENDER_OPTIONS} {...field("gender")} />
        <Input label="Phone" {...field("phone")} required />
        <Input label="Alternate phone" {...field("alternate_phone")} />
        <Input label="Email" type="email" {...field("email")} />
        <Select label="Blood group" {...field("blood_group")}>
          {BLOOD_OPTIONS.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </Select>
        <Select label="Marital status" options={MARITAL_OPTIONS} {...field("marital_status")} />
        <Input label="Nationality" {...field("nationality")} />
        <Input label="Religion" {...field("religion")} />
        <Input label="Citizenship number" {...field("citizenship_number")} />
      </Section>

      <Section title="Permanent Address">
        <Input label="Province" {...field("province")} />
        <Input label="District" {...field("district")} />
        <Input label="Municipality" {...field("municipality")} />
        <Input label="Ward number" {...field("ward_number")} />
        <Input label="Street / Tole" {...field("street_tole")} />
      </Section>

      <Section title="Temporary Address">
        <Input label="Province" {...field("temp_province")} />
        <Input label="District" {...field("temp_district")} />
        <Input label="Municipality" {...field("temp_municipality")} />
        <Input label="Ward number" {...field("temp_ward_number")} />
        <Input label="Street / Tole" {...field("temp_street_tole")} />
      </Section>

      <Section title="Health & Emergency">
        <Textarea label="Medical condition" {...field("medical_condition")} />
        <Input label="Disability" {...field("disability")} />
        <div />
        <Input label="Emergency contact name" {...field("emergency_contact_name")} />
        <Input label="Emergency contact phone" {...field("emergency_contact_phone")} />
        <Input label="Relation" {...field("emergency_contact_relation")} />
      </Section>

      <Section title="3. Education">
        <Input label="Educational institute" {...field("educational_institute")} required />
        <Select label="Current level" options={LEVEL_OPTIONS} {...field("current_level")} />
        <Input label="Faculty" {...field("faculty")} />
        <Input label="Roll number" {...field("roll_number")} />
        <Select label="Class timing" options={TIMING_OPTIONS} {...field("class_timing")} />
        <Input
          label="Stay duration (months)"
          type="number"
          value={form.hostel_stay_duration ?? 12}
          onChange={(e) => set("hostel_stay_duration", Number(e.target.value))}
        />
        <Input label="Expected checkout date" type="date" {...field("expected_checkout_date")} />
      </Section>

      <Section title="4. Food Preference">
        <Select label="Food preference" options={FOOD_OPTIONS} {...field("food_preference")} />
        <Input label="Food allergy" {...field("food_allergy")} />
        <Input label="Special diet" {...field("special_diet")} />
      </Section>

      <Section title="5. Guardian Information">
        <Input label="Father's name" {...field("father_name")} />
        <Input label="Father's phone" {...field("father_phone")} />
        <Input label="Father's occupation" {...field("father_occupation")} />
        <Input label="Mother's name" {...field("mother_name")} />
        <Input label="Mother's phone" {...field("mother_phone")} />
        <Input label="Mother's occupation" {...field("mother_occupation")} />
        <Input label="Spouse's name" {...field("spouse_name")} />
        <Input label="Spouse's phone" {...field("spouse_phone")} />
        <Input label="Spouse's occupation" {...field("spouse_occupation")} />
        <Input label="Local guardian name" {...field("local_guardian_name")} />
        <Input label="Local guardian phone" {...field("local_guardian_phone")} />
        <Input label="Local guardian relation" {...field("local_guardian_relation")} />
        <Input label="Local guardian address" {...field("local_guardian_address")} />
        <Input label="Local guardian occupation" {...field("local_guardian_occupation")} />
        <Input label="Guardian email" type="email" {...field("guardian_email")} />
      </Section>

      <Section title="6. Hostel Allocation">
        <Select label="Preferred room type" options={ROOM_TYPE_OPTIONS} {...field("preferred_room_type")} />
        <Input label="Preferred floor" {...field("preferred_floor")} />
        <div />
      </Section>

      <Section title="7. Official Use">
        <Input label="Booking date" type="date" {...field("booking_date")} />
        <Input label="Monthly fee" type="number" step="0.01" {...field("monthly_fee")} />
        <Input label="Security deposit" type="number" step="0.01" {...field("security_deposit")} />
        <Input label="Admission fee" type="number" step="0.01" {...field("admission_fee")} />
        <Input label="Discount" type="number" step="0.01" {...field("discount")} />
        <Input label="Scholarship" type="number" step="0.01" {...field("scholarship")} />
        <Input label="Receipt number" {...field("receipt_number")} />
        <Select label="Payment status" options={PAYMENT_STATUS_OPTIONS} {...field("payment_status")} />
        <div />
        <div className="md:col-span-3">
          <Textarea label="Remarks / Notes" {...field("remarks")} />
        </div>
      </Section>

      <div className="flex justify-end gap-2">
        {onCancel ? (
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
        <Button type="submit" loading={saving}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
