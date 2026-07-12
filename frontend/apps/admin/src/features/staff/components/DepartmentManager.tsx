"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  EmptyState,
  Input,
  Modal,
  Select,
  Table,
  Textarea,
  useConfirm,
  useToast,
} from "@hostel/ui";
import { Plus, Trash2 } from "lucide-react";

import { staffApi } from "../api/staff.api";
import type { Department, Designation } from "../types/staff.types";

export function DepartmentManager() {
  const toast = useToast();
  const confirm = useConfirm();

  const [departments, setDepartments] = useState<Department[]>([]);
  const [designations, setDesignations] = useState<Designation[]>([]);
  const [loading, setLoading] = useState(true);

  const [deptOpen, setDeptOpen] = useState(false);
  const [deptName, setDeptName] = useState("");
  const [deptCode, setDeptCode] = useState("");
  const [deptDesc, setDeptDesc] = useState("");

  const [desigOpen, setDesigOpen] = useState(false);
  const [desigTitle, setDesigTitle] = useState("");
  const [desigDept, setDesigDept] = useState("");

  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [d, g] = await Promise.all([
        staffApi.departments.list(),
        staffApi.designations.list(),
      ]);
      setDepartments(d);
      setDesignations(g);
    } catch (e) {
      toast.error((e as Error).message, "Couldn't load departments");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const createDept = async () => {
    if (!deptName.trim()) return;
    setBusy(true);
    try {
      await staffApi.departments.create({ name: deptName.trim(), code: deptCode, description: deptDesc });
      toast.success("Department created.");
      setDeptOpen(false);
      setDeptName("");
      setDeptCode("");
      setDeptDesc("");
      await load();
    } catch (e) {
      toast.error((e as Error).message, "Create failed");
    } finally {
      setBusy(false);
    }
  };

  const createDesig = async () => {
    if (!desigTitle.trim()) return;
    setBusy(true);
    try {
      await staffApi.designations.create({
        title: desigTitle.trim(),
        department: desigDept || null,
      });
      toast.success("Designation created.");
      setDesigOpen(false);
      setDesigTitle("");
      setDesigDept("");
      await load();
    } catch (e) {
      toast.error((e as Error).message, "Create failed");
    } finally {
      setBusy(false);
    }
  };

  const removeDept = async (d: Department) => {
    const yes = await confirm({
      title: "Delete department",
      message: `Delete “${d.name}”? Staff in it are left without a department.`,
      danger: true,
      confirmText: "Delete",
    });
    if (!yes) return;
    try {
      await staffApi.departments.remove(d.id);
      toast.success("Department deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const removeDesig = async (g: Designation) => {
    const yes = await confirm({ title: "Delete designation", message: `Delete “${g.title}”?`, danger: true, confirmText: "Delete" });
    if (!yes) return;
    try {
      await staffApi.designations.remove(g.id);
      toast.success("Designation deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Departments */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--foreground)]">Departments</h2>
          <Button size="sm" onClick={() => setDeptOpen(true)}>
            <Plus className="h-4 w-4" /> New
          </Button>
        </div>
        {departments.length === 0 ? (
          <EmptyState title="No departments" description="Group staff into departments." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                <th className="px-4 py-2.5 font-medium">Name</th>
                <th className="px-4 py-2.5 font-medium">Staff</th>
                <th className="px-4 py-2.5 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {departments.map((d) => (
                <tr key={d.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-4 py-2.5">
                    <div className="font-medium text-[var(--foreground)]">{d.name}</div>
                    {d.code ? <div className="text-xs text-[var(--muted)]">{d.code}</div> : null}
                  </td>
                  <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{d.staff_count}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex justify-end">
                      <Button variant="ghost" size="sm" title="Delete" onClick={() => removeDept(d)}>
                        <Trash2 className="h-4 w-4 text-[var(--error)]" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      {/* Designations */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--foreground)]">Designations</h2>
          <Button size="sm" onClick={() => setDesigOpen(true)}>
            <Plus className="h-4 w-4" /> New
          </Button>
        </div>
        {designations.length === 0 ? (
          <EmptyState title="No designations" description="Add job titles for your staff." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                <th className="px-4 py-2.5 font-medium">Title</th>
                <th className="px-4 py-2.5 font-medium">Department</th>
                <th className="px-4 py-2.5 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {designations.map((g) => (
                <tr key={g.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-4 py-2.5 font-medium text-[var(--foreground)]">{g.title}</td>
                  <td className="px-4 py-2.5 text-[var(--foreground-secondary)]">{g.department_name || "—"}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex justify-end">
                      <Button variant="ghost" size="sm" title="Delete" onClick={() => removeDesig(g)}>
                        <Trash2 className="h-4 w-4 text-[var(--error)]" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <Modal open={deptOpen} title="New department" onClose={() => setDeptOpen(false)}>
        <div className="space-y-3">
          <Input label="Name" value={deptName} onChange={(e) => setDeptName(e.target.value)} placeholder="e.g. Housekeeping" />
          <Input label="Code (optional)" value={deptCode} onChange={(e) => setDeptCode(e.target.value)} />
          <Textarea label="Description (optional)" value={deptDesc} onChange={(e) => setDeptDesc(e.target.value)} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setDeptOpen(false)}>Cancel</Button>
            <Button loading={busy} onClick={createDept}>Create</Button>
          </div>
        </div>
      </Modal>

      <Modal open={desigOpen} title="New designation" onClose={() => setDesigOpen(false)}>
        <div className="space-y-3">
          <Input label="Title" value={desigTitle} onChange={(e) => setDesigTitle(e.target.value)} placeholder="e.g. Senior Warden" />
          <Select label="Department (optional)" value={desigDept} onChange={(e) => setDesigDept(e.target.value)} placeholder="None">
            {departments.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </Select>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setDesigOpen(false)}>Cancel</Button>
            <Button loading={busy} onClick={createDesig}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
