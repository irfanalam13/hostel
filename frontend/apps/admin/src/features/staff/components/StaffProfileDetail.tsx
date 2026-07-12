"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Button,
  Card,
  ErrorState,
  Input,
  Modal,
  Select,
  useConfirm,
  useToast,
} from "@hostel/ui";
import {
  ArrowLeft,
  Ban,
  KeyRound,
  Lock,
  Pause,
  Pencil,
  Play,
  RotateCcw,
  Trash2,
  Unlock,
} from "lucide-react";

import { staffApi } from "../api/staff.api";
import type {
  CreateStaffPayload,
  Department,
  Designation,
  Role,
  StaffProfile,
} from "../types/staff.types";
import { ReadField, StatusBadge } from "./primitives";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "employment", label: "Employment" },
  { id: "salary", label: "Salary" },
  { id: "documents", label: "Documents" },
] as const;
type TabId = (typeof TABS)[number]["id"];

const EMPLOYMENT_TYPES = [
  { value: "full_time", label: "Full Time" },
  { value: "part_time", label: "Part Time" },
  { value: "contract", label: "Contract" },
  { value: "temporary", label: "Temporary" },
  { value: "internship", label: "Internship" },
];
const SALARY_TYPES = [
  { value: "monthly", label: "Monthly" },
  { value: "hourly", label: "Hourly" },
  { value: "daily", label: "Daily Wage" },
  { value: "contract", label: "Contract" },
];

// Fields the edit form writes back (subset of the full profile).
const EDITABLE_KEYS: (keyof CreateStaffPayload)[] = [
  "first_name", "middle_name", "last_name", "gender", "date_of_birth", "nationality",
  "citizenship_number", "passport_number", "marital_status", "phone",
  "emergency_contact_name", "emergency_contact_phone", "country", "province", "district",
  "city", "ward", "street", "postal_code", "role", "department", "designation",
  "joining_date", "employment_type", "work_location", "shift", "salary_type",
  "basic_salary", "allowances", "tax_percentage", "payment_method", "bank_name",
  "bank_account", "pan_number", "notes",
];

export function StaffProfileDetail({ staffId }: { staffId: string }) {
  const toast = useToast();
  const confirm = useConfirm();

  const [profile, setProfile] = useState<StaffProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabId>("overview");
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<CreateStaffPayload>>({});
  const [busy, setBusy] = useState(false);
  const [tempPassword, setTempPassword] = useState<string | null>(null);

  const [roles, setRoles] = useState<Role[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [designations, setDesignations] = useState<Designation[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setProfile(await staffApi.staff.retrieve(staffId));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [staffId]);

  useEffect(() => {
    load();
    staffApi.roles.list().then(setRoles).catch(() => {});
    staffApi.departments.list().then(setDepartments).catch(() => {});
    staffApi.designations.list().then(setDesignations).catch(() => {});
  }, [load]);

  const startEdit = () => {
    if (!profile) return;
    const seed: Partial<CreateStaffPayload> = {};
    EDITABLE_KEYS.forEach((k) => {
      const v = (profile as unknown as Record<string, unknown>)[k];
      seed[k] = (v ?? "") as never;
    });
    setForm(seed);
    setEditing(true);
  };

  const set = (patch: Partial<CreateStaffPayload>) => setForm((f) => ({ ...f, ...patch }));

  const save = async () => {
    setBusy(true);
    try {
      const body: Partial<CreateStaffPayload> = { ...form };
      // Empty relation strings mean "unset" — send null so DRF accepts them.
      (["role", "department", "designation"] as const).forEach((k) => {
        if (body[k] === "") body[k] = null;
      });
      if (body.date_of_birth === "") body.date_of_birth = null;
      if (body.joining_date === "") body.joining_date = null;
      const updated = await staffApi.staff.update(staffId, body);
      setProfile(updated);
      setEditing(false);
      toast.success("Profile updated.");
    } catch (e) {
      toast.error((e as Error).message, "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const act = async (fn: () => Promise<StaffProfile>, ok: string) => {
    try {
      const updated = await fn();
      setProfile(updated);
      toast.success(ok);
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const resetPassword = async () => {
    if (!profile) return;
    const yes = await confirm({
      title: "Reset password",
      message: `Generate a new temporary password for ${profile.full_name}?`,
      confirmText: "Reset",
    });
    if (!yes) return;
    try {
      const res = await staffApi.staff.resetPassword(profile.id);
      setTempPassword(res.temporary_password);
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const remove = async () => {
    if (!profile) return;
    const yes = await confirm({
      title: "Remove staff member",
      message: `Remove ${profile.full_name}? Their account is archived (soft delete) and can be restored.`,
      danger: true,
      confirmText: "Remove",
    });
    if (yes) await act(() => staffApi.staff.remove(profile.id).then(() => staffApi.staff.retrieve(profile.id)), "Staff removed.");
  };

  const initials = useMemo(() => {
    if (!profile) return "";
    const n = profile.full_name || profile.username;
    return n.split(/\s+/).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("");
  }, [profile]);

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (error || !profile)
    return <ErrorState description={error || "Staff member not found."} onRetry={load} />;

  const rd = (label: string, value?: React.ReactNode) => <ReadField label={label} value={value} />;

  return (
    <div className="space-y-5">
      <Link href="/staff" className="inline-flex items-center gap-1.5 text-sm text-[var(--muted)] hover:text-[var(--foreground)]">
        <ArrowLeft className="h-4 w-4" /> Back to directory
      </Link>

      {/* Header */}
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4 p-1">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-lg font-semibold text-[var(--accent)]">
              {initials}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold text-[var(--foreground)]">{profile.full_name || profile.username}</h2>
                <StatusBadge status={profile.status} label={profile.status_display} />
              </div>
              <div className="text-sm text-[var(--muted)]">
                {profile.employee_id} · {profile.designation_title || profile.account_role}
                {profile.department_name ? ` · ${profile.department_name}` : ""}
              </div>
              <div className="text-xs text-[var(--muted)]">{profile.email || profile.username}</div>
            </div>
          </div>
          {!editing ? (
            <Button variant="secondary" onClick={startEdit}>
              <Pencil className="h-4 w-4" /> Edit
            </Button>
          ) : null}
        </div>

        {/* Lifecycle actions */}
        <div className="mt-4 flex flex-wrap gap-2 border-t border-[var(--border)] pt-4">
          {profile.status === "active" ? (
            <Button variant="ghost" size="sm" onClick={() => act(() => staffApi.staff.suspend(profile.id), "Suspended.")}><Pause className="h-4 w-4" /> Suspend</Button>
          ) : (
            <Button variant="ghost" size="sm" onClick={() => act(() => staffApi.staff.activate(profile.id), "Activated.")}><Play className="h-4 w-4" /> Activate</Button>
          )}
          {profile.status === "locked" ? (
            <Button variant="ghost" size="sm" onClick={() => act(() => staffApi.staff.unlock(profile.id), "Unlocked.")}><Unlock className="h-4 w-4" /> Unlock</Button>
          ) : (
            <Button variant="ghost" size="sm" onClick={() => act(() => staffApi.staff.lock(profile.id), "Locked.")}><Lock className="h-4 w-4" /> Lock</Button>
          )}
          <Button variant="ghost" size="sm" onClick={() => act(() => staffApi.staff.disable(profile.id), "Disabled.")}><Ban className="h-4 w-4" /> Disable</Button>
          <Button variant="ghost" size="sm" onClick={resetPassword}><KeyRound className="h-4 w-4" /> Reset password</Button>
          <Button variant="ghost" size="sm" onClick={() => act(() => staffApi.staff.forcePasswordReset(profile.id), "Password change will be required.")}><RotateCcw className="h-4 w-4" /> Force reset</Button>
          <Button variant="ghost" size="sm" onClick={remove}><Trash2 className="h-4 w-4 text-[var(--error)]" /> Remove</Button>
        </div>
      </Card>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-[var(--border)]">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition ${
              t.id === tab
                ? "border-[var(--accent)] text-[var(--foreground)]"
                : "border-transparent text-[var(--muted)] hover:text-[var(--foreground)]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Edit mode form */}
      {editing ? (
        <Card>
          <div className="space-y-4">
            {tab === "overview" && (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                <Input label="First name" value={form.first_name as string} onChange={(e) => set({ first_name: e.target.value })} />
                <Input label="Middle name" value={form.middle_name as string} onChange={(e) => set({ middle_name: e.target.value })} />
                <Input label="Last name" value={form.last_name as string} onChange={(e) => set({ last_name: e.target.value })} />
                <Input label="Gender" value={form.gender as string} onChange={(e) => set({ gender: e.target.value })} />
                <Input label="Date of birth" type="date" value={(form.date_of_birth as string) || ""} onChange={(e) => set({ date_of_birth: e.target.value })} />
                <Input label="Nationality" value={form.nationality as string} onChange={(e) => set({ nationality: e.target.value })} />
                <Input label="Citizenship no." value={form.citizenship_number as string} onChange={(e) => set({ citizenship_number: e.target.value })} />
                <Input label="Passport no." value={form.passport_number as string} onChange={(e) => set({ passport_number: e.target.value })} />
                <Input label="Marital status" value={form.marital_status as string} onChange={(e) => set({ marital_status: e.target.value })} />
                <Input label="Phone" value={form.phone as string} onChange={(e) => set({ phone: e.target.value })} />
                <Input label="Emergency contact" value={form.emergency_contact_name as string} onChange={(e) => set({ emergency_contact_name: e.target.value })} />
                <Input label="Emergency phone" value={form.emergency_contact_phone as string} onChange={(e) => set({ emergency_contact_phone: e.target.value })} />
                <Input label="Country" value={form.country as string} onChange={(e) => set({ country: e.target.value })} />
                <Input label="Province" value={form.province as string} onChange={(e) => set({ province: e.target.value })} />
                <Input label="District" value={form.district as string} onChange={(e) => set({ district: e.target.value })} />
                <Input label="City" value={form.city as string} onChange={(e) => set({ city: e.target.value })} />
                <Input label="Ward" value={form.ward as string} onChange={(e) => set({ ward: e.target.value })} />
                <Input label="Street" value={form.street as string} onChange={(e) => set({ street: e.target.value })} />
                <Input label="Postal code" value={form.postal_code as string} onChange={(e) => set({ postal_code: e.target.value })} />
              </div>
            )}
            {tab === "employment" && (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                <Select label="Custom role" value={(form.role as string) || ""} onChange={(e) => set({ role: e.target.value })} placeholder="None">
                  {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                </Select>
                <Select label="Department" value={(form.department as string) || ""} onChange={(e) => set({ department: e.target.value })} placeholder="None">
                  {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </Select>
                <Select label="Designation" value={(form.designation as string) || ""} onChange={(e) => set({ designation: e.target.value })} placeholder="None">
                  {designations.map((g) => <option key={g.id} value={g.id}>{g.title}</option>)}
                </Select>
                <Select label="Employment type" value={form.employment_type as string} onChange={(e) => set({ employment_type: e.target.value as CreateStaffPayload["employment_type"] })}>
                  {EMPLOYMENT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </Select>
                <Input label="Joining date" type="date" value={(form.joining_date as string) || ""} onChange={(e) => set({ joining_date: e.target.value })} />
                <Input label="Work location" value={form.work_location as string} onChange={(e) => set({ work_location: e.target.value })} />
                <Input label="Shift" value={form.shift as string} onChange={(e) => set({ shift: e.target.value })} />
              </div>
            )}
            {tab === "salary" && (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                <Select label="Salary type" value={form.salary_type as string} onChange={(e) => set({ salary_type: e.target.value as CreateStaffPayload["salary_type"] })}>
                  {SALARY_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </Select>
                <Input label="Basic salary" type="number" value={form.basic_salary as string} onChange={(e) => set({ basic_salary: e.target.value })} />
                <Input label="Allowances" type="number" value={form.allowances as string} onChange={(e) => set({ allowances: e.target.value })} />
                <Input label="Tax %" type="number" value={form.tax_percentage as string} onChange={(e) => set({ tax_percentage: e.target.value })} />
                <Input label="Payment method" value={form.payment_method as string} onChange={(e) => set({ payment_method: e.target.value })} />
                <Input label="Bank name" value={form.bank_name as string} onChange={(e) => set({ bank_name: e.target.value })} />
                <Input label="Bank account" value={form.bank_account as string} onChange={(e) => set({ bank_account: e.target.value })} />
                <Input label="PAN number" value={form.pan_number as string} onChange={(e) => set({ pan_number: e.target.value })} />
              </div>
            )}
            {tab === "documents" && (
              <p className="text-sm text-[var(--muted)]">Switch off edit mode to view documents. Document upload is available in the Documents tab.</p>
            )}
            {tab !== "documents" && (
              <div className="flex justify-end gap-2 border-t border-[var(--border)] pt-3">
                <Button variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
                <Button loading={busy} onClick={save}>Save changes</Button>
              </div>
            )}
          </div>
        </Card>
      ) : (
        <Card>
          {tab === "overview" && (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              {rd("Full name", profile.full_name)}
              {rd("Gender", profile.gender)}
              {rd("Date of birth", profile.date_of_birth)}
              {rd("Nationality", profile.nationality)}
              {rd("Citizenship no.", profile.citizenship_number)}
              {rd("Passport no.", profile.passport_number)}
              {rd("Marital status", profile.marital_status)}
              {rd("Phone", profile.phone)}
              {rd("Email", profile.email)}
              {rd("Emergency contact", profile.emergency_contact_name)}
              {rd("Emergency phone", profile.emergency_contact_phone)}
              {rd("Address", [profile.street, profile.ward, profile.city, profile.district, profile.province, profile.country].filter(Boolean).join(", "))}
            </div>
          )}
          {tab === "employment" && (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              {rd("Employee ID", profile.employee_id)}
              {rd("Account role", profile.account_role)}
              {rd("Custom role", profile.role_name)}
              {rd("Department", profile.department_name)}
              {rd("Designation", profile.designation_title)}
              {rd("Reporting manager", profile.reporting_manager_name)}
              {rd("Employment type", profile.employment_type)}
              {rd("Joining date", profile.joining_date)}
              {rd("Work location", profile.work_location)}
              {rd("Shift", profile.shift)}
              {rd("Last login", profile.last_login ? new Date(profile.last_login).toLocaleString() : "Never")}
            </div>
          )}
          {tab === "salary" && (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              {rd("Salary type", profile.salary_type)}
              {rd("Basic salary", profile.basic_salary)}
              {rd("Allowances", profile.allowances)}
              {rd("Tax %", profile.tax_percentage)}
              {rd("Payment method", profile.payment_method)}
              {rd("Bank name", profile.bank_name)}
              {rd("Bank account", profile.bank_account)}
              {rd("PAN number", profile.pan_number)}
            </div>
          )}
          {tab === "documents" && (
            <div className="space-y-2">
              {profile.documents.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">No documents uploaded.</p>
              ) : (
                profile.documents.map((doc) => (
                  <div key={doc.id} className="flex items-center justify-between rounded-xl border border-[var(--border)] px-4 py-2.5">
                    <div>
                      <div className="text-sm font-medium text-[var(--foreground)]">{doc.title || doc.doc_type_display}</div>
                      <div className="text-xs text-[var(--muted)]">{doc.doc_type_display}{doc.expiry_date ? ` · expires ${doc.expiry_date}` : ""}</div>
                    </div>
                    <a href={doc.file} target="_blank" rel="noreferrer" className="text-sm font-medium text-[var(--accent)] hover:underline">Download</a>
                  </div>
                ))
              )}
            </div>
          )}
        </Card>
      )}

      <Modal open={!!tempPassword} title="Temporary password" onClose={() => setTempPassword(null)}>
        <div className="space-y-3">
          <p className="text-sm text-[var(--foreground-secondary)]">Shown only once — share it securely.</p>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] px-4 py-3 font-mono text-sm text-[var(--foreground)]">{tempPassword}</div>
          <div className="flex justify-end">
            <Button onClick={() => setTempPassword(null)}>Done</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
