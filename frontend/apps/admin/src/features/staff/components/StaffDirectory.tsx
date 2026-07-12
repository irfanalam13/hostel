"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Button,
  EmptyState,
  Input,
  Modal,
  Select,
  Table,
  useConfirm,
  useToast,
} from "@hostel/ui";
import {
  Ban,
  KeyRound,
  Lock,
  Pause,
  Play,
  Plus,
  Trash2,
  Unlock,
  UserRoundPlus,
} from "lucide-react";

import { staffApi } from "../api/staff.api";
import type {
  CreateStaffPayload,
  Department,
  Role,
  StaffProfile,
} from "../types/staff.types";
import { StatCard, StatusBadge } from "./primitives";

const ACCOUNT_ROLES = ["STAFF", "MANAGER", "RECEPTIONIST", "ACCOUNTANT", "WARDEN", "ADMIN", "READ_ONLY"];
const EMPLOYMENT_TYPES: { value: string; label: string }[] = [
  { value: "full_time", label: "Full Time" },
  { value: "part_time", label: "Part Time" },
  { value: "contract", label: "Contract" },
  { value: "temporary", label: "Temporary" },
  { value: "internship", label: "Internship" },
];

const STATUS_FILTERS = ["", "active", "invited", "suspended", "disabled", "locked"];

const emptyForm: CreateStaffPayload = {
  email: "",
  username: "",
  account_role: "STAFF",
  first_name: "",
  middle_name: "",
  last_name: "",
  phone: "",
  role: "",
  department: "",
  employment_type: "full_time",
  joining_date: "",
  work_location: "",
  basic_salary: "0",
};

export function StaffDirectory() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<StaffProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [roles, setRoles] = useState<Role[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);

  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<CreateStaffPayload>(emptyForm);
  const [busy, setBusy] = useState(false);
  const [tempPassword, setTempPassword] = useState<{ username: string; password: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await staffApi.staff.list({ search, status: statusFilter }));
    } catch (e) {
      toast.error((e as Error).message, "Couldn't load staff");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, toast]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  // Lookups for the create form (best-effort — don't block the directory).
  useEffect(() => {
    staffApi.roles.list().then(setRoles).catch(() => {});
    staffApi.departments.list().then(setDepartments).catch(() => {});
  }, []);

  const counts = useMemo(() => {
    const active = rows.filter((r) => r.status === "active").length;
    const suspended = rows.filter((r) => r.status === "suspended" || r.status === "locked").length;
    return { total: rows.length, active, suspended };
  }, [rows]);

  const set = (patch: Partial<CreateStaffPayload>) => setForm((f) => ({ ...f, ...patch }));

  const submit = async () => {
    setBusy(true);
    try {
      // Prune empty optional relations so the API doesn't reject "".
      const payload: CreateStaffPayload = { ...form };
      if (!payload.role) delete payload.role;
      if (!payload.department) delete payload.department;
      if (!payload.joining_date) delete payload.joining_date;
      if (!payload.username) delete payload.username;
      const created = await staffApi.staff.create(payload);
      toast.success(`${created.full_name || created.username} added.`);
      setCreating(false);
      setForm(emptyForm);
      if (created.temporary_password) {
        setTempPassword({ username: created.username, password: created.temporary_password });
      }
      await load();
    } catch (e) {
      toast.error((e as Error).message, "Couldn't create staff");
    } finally {
      setBusy(false);
    }
  };

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      toast.success(ok);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const resetPassword = async (staff: StaffProfile) => {
    const yes = await confirm({
      title: "Reset password",
      message: `Generate a new temporary password for ${staff.full_name}? Their current password stops working immediately.`,
      confirmText: "Reset",
    });
    if (!yes) return;
    try {
      const res = await staffApi.staff.resetPassword(staff.id);
      setTempPassword({ username: staff.username, password: res.temporary_password });
      toast.success("Password reset.");
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const remove = async (staff: StaffProfile) => {
    const yes = await confirm({
      title: "Remove staff member",
      message: `Remove ${staff.full_name}? Their account is disabled and archived (soft delete) — it can be restored later.`,
      danger: true,
      confirmText: "Remove",
    });
    if (yes) await act(() => staffApi.staff.remove(staff.id), "Staff removed.");
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Total staff" value={counts.total} />
        <StatCard label="Active" value={counts.active} />
        <StatCard label="Suspended / locked" value={counts.suspended} />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex-1 min-w-[200px]">
          <Input
            placeholder="Search by name, employee ID, email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="w-44">
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            {STATUS_FILTERS.map((s) => (
              <option key={s || "all"} value={s}>
                {s ? s[0].toUpperCase() + s.slice(1) : "All statuses"}
              </option>
            ))}
          </Select>
        </div>
        <Button onClick={() => setCreating(true)}>
          <Plus className="h-4 w-4" /> Add staff
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState
          title="No staff yet"
          description="Add your first team member to start managing roles, departments and access."
        />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Employee</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Department</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <Link href={`/staff/${r.id}`} className="font-medium text-[var(--foreground)] hover:text-[var(--accent)]">
                    {r.full_name || r.username}
                  </Link>
                  <div className="text-xs text-[var(--muted)]">
                    {r.employee_id} · {r.email || r.username}
                  </div>
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">
                  {r.role_name || r.account_role}
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">
                  {r.department_name || "—"}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={r.status} label={r.status_display} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    {r.status === "active" ? (
                      <Button variant="ghost" size="sm" title="Suspend" onClick={() => act(() => staffApi.staff.suspend(r.id), "Suspended.")}>
                        <Pause className="h-4 w-4" />
                      </Button>
                    ) : (
                      <Button variant="ghost" size="sm" title="Activate" onClick={() => act(() => staffApi.staff.activate(r.id), "Activated.")}>
                        <Play className="h-4 w-4" />
                      </Button>
                    )}
                    {r.status === "locked" ? (
                      <Button variant="ghost" size="sm" title="Unlock" onClick={() => act(() => staffApi.staff.unlock(r.id), "Unlocked.")}>
                        <Unlock className="h-4 w-4" />
                      </Button>
                    ) : (
                      <Button variant="ghost" size="sm" title="Lock" onClick={() => act(() => staffApi.staff.lock(r.id), "Locked.")}>
                        <Lock className="h-4 w-4" />
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" title="Disable" onClick={() => act(() => staffApi.staff.disable(r.id), "Disabled.")}>
                      <Ban className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Reset password" onClick={() => resetPassword(r)}>
                      <KeyRound className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Remove" onClick={() => remove(r)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {/* Create staff drawer */}
      <Modal open={creating} title="Add staff member" onClose={() => setCreating(false)}>
        <div className="max-h-[70vh] space-y-4 overflow-y-auto pr-1">
          <section className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Account</h3>
            <div className="grid grid-cols-2 gap-3">
              <Input label="Email" type="email" value={form.email} onChange={(e) => set({ email: e.target.value })} placeholder="name@example.com" />
              <Input label="Username (optional)" value={form.username} onChange={(e) => set({ username: e.target.value })} placeholder="auto from email" />
              <Select label="Account role" value={form.account_role} onChange={(e) => set({ account_role: e.target.value })}>
                {ACCOUNT_ROLES.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </Select>
              <Select label="Custom role" value={(form.role as string) || ""} onChange={(e) => set({ role: e.target.value })} placeholder="None">
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </Select>
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Identity</h3>
            <div className="grid grid-cols-3 gap-3">
              <Input label="First name" value={form.first_name} onChange={(e) => set({ first_name: e.target.value })} />
              <Input label="Middle name" value={form.middle_name} onChange={(e) => set({ middle_name: e.target.value })} />
              <Input label="Last name" value={form.last_name} onChange={(e) => set({ last_name: e.target.value })} />
            </div>
            <Input label="Phone" value={form.phone} onChange={(e) => set({ phone: e.target.value })} />
          </section>

          <section className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Employment</h3>
            <div className="grid grid-cols-2 gap-3">
              <Select label="Department" value={(form.department as string) || ""} onChange={(e) => set({ department: e.target.value })} placeholder="None">
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </Select>
              <Select label="Employment type" value={form.employment_type} onChange={(e) => set({ employment_type: e.target.value as CreateStaffPayload["employment_type"] })}>
                {EMPLOYMENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </Select>
              <Input label="Joining date" type="date" value={form.joining_date || ""} onChange={(e) => set({ joining_date: e.target.value })} />
              <Input label="Work location" value={form.work_location} onChange={(e) => set({ work_location: e.target.value })} />
              <Input label="Basic salary" type="number" value={form.basic_salary} onChange={(e) => set({ basic_salary: e.target.value })} />
            </div>
          </section>

          <p className="text-xs text-[var(--muted)]">
            A login account is created with a one-time temporary password (shown once and emailed when an address is given). Creating staff counts against your plan&apos;s staff limit.
          </p>

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCreating(false)}>Cancel</Button>
            <Button loading={busy} onClick={submit}>
              <UserRoundPlus className="h-4 w-4" /> Create staff
            </Button>
          </div>
        </div>
      </Modal>

      {/* One-time temporary-password reveal */}
      <Modal open={!!tempPassword} title="Temporary password" onClose={() => setTempPassword(null)}>
        <div className="space-y-3">
          <p className="text-sm text-[var(--foreground-secondary)]">
            Share these credentials securely with <strong>{tempPassword?.username}</strong>. This
            password is shown only once.
          </p>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] px-4 py-3 font-mono text-sm text-[var(--foreground)]">
            {tempPassword?.password}
          </div>
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                if (tempPassword) navigator.clipboard?.writeText(tempPassword.password);
                toast.success("Copied to clipboard.");
              }}
            >
              Copy
            </Button>
            <Button onClick={() => setTempPassword(null)}>Done</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
