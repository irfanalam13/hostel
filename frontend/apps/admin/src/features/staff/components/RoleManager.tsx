"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Button,
  EmptyState,
  Input,
  Modal,
  Table,
  useConfirm,
  useToast,
} from "@hostel/ui";
import { Pencil, Plus, ShieldCheck, Trash2 } from "lucide-react";

import { staffApi } from "../api/staff.api";
import type { PermissionCatalog, Role } from "../types/staff.types";
import { Badge } from "./primitives";

const ACTION_LABEL: Record<string, string> = {
  view: "View",
  create: "Create",
  edit: "Edit",
  delete: "Delete",
};

function prettyAction(perm: string): string {
  const action = perm.split(".").slice(1).join(".");
  return ACTION_LABEL[action] || action.replace(/_/g, " ");
}

/** A role grants a permission if it lists it directly, the module wildcard, or `*`. */
function granted(perms: string[], perm: string): boolean {
  if (perms.includes("*") || perms.includes(perm)) return true;
  const mod = perm.split(".")[0];
  return perms.includes(`${mod}.*`);
}

export function RoleManager() {
  const toast = useToast();
  const confirm = useConfirm();

  const [roles, setRoles] = useState<Role[]>([]);
  const [catalog, setCatalog] = useState<PermissionCatalog["modules"]>([]);
  const [loading, setLoading] = useState(true);

  const [editing, setEditing] = useState<Role | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRoles(await staffApi.roles.list());
    } catch (e) {
      toast.error((e as Error).message, "Couldn't load roles");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
    staffApi.roles.catalog().then((c) => setCatalog(c.modules)).catch(() => {});
  }, [load]);

  const openNew = () => {
    setIsNew(true);
    setEditing(null);
    setName("");
    setDescription("");
    setSelected(new Set());
  };

  const openEdit = (role: Role) => {
    setIsNew(false);
    setEditing(role);
    setName(role.name);
    setDescription(role.description);
    // Expand any wildcards into concrete selections for the checkbox grid.
    const next = new Set<string>();
    catalog.forEach((group) =>
      group.permissions.forEach((p) => {
        if (granted(role.permissions, p)) next.add(p);
      }),
    );
    setSelected(next);
  };

  const close = () => {
    setEditing(null);
    setIsNew(false);
  };

  const toggle = (perm: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(perm) ? next.delete(perm) : next.add(perm);
      return next;
    });

  const toggleModule = (perms: string[], on: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev);
      perms.forEach((p) => (on ? next.add(p) : next.delete(p)));
      return next;
    });

  const save = async () => {
    if (!name.trim()) {
      toast.error("Give the role a name.");
      return;
    }
    setBusy(true);
    const body = { name: name.trim(), description, permissions: Array.from(selected) };
    try {
      if (isNew) {
        await staffApi.roles.create(body);
        toast.success(`Role “${body.name}” created.`);
      } else if (editing) {
        await staffApi.roles.update(editing.id, body);
        toast.success(`Role “${body.name}” updated.`);
      }
      close();
      await load();
    } catch (e) {
      toast.error((e as Error).message, "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (role: Role) => {
    const yes = await confirm({
      title: "Delete role",
      message: `Delete “${role.name}”? Staff assigned to it lose its permissions (they keep their base account role).`,
      danger: true,
      confirmText: "Delete",
    });
    if (!yes) return;
    try {
      await staffApi.roles.remove(role.id);
      toast.success("Role deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const open = isNew || !!editing;
  const selectedCount = selected.size;

  const grantSummary = useMemo(
    () => (role: Role) => {
      if (role.permissions.includes("*")) return "All permissions";
      const wild = role.permissions.filter((p) => p.endsWith(".*")).length;
      const exact = role.permissions.filter((p) => !p.endsWith(".*") && p !== "*").length;
      return `${wild} module${wild === 1 ? "" : "s"} · ${exact} action${exact === 1 ? "" : "s"}`;
    },
    [],
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-[var(--muted)]">
          Custom roles layer granular permissions on top of a member&apos;s base account role.
        </p>
        <Button onClick={openNew}>
          <Plus className="h-4 w-4" /> New role
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : roles.length === 0 ? (
        <EmptyState title="No roles yet" description="Create your first custom role." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Permissions</th>
              <th className="px-4 py-3 font-medium">Staff</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {roles.map((role) => (
              <tr key={role.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-[var(--foreground)]">{role.name}</span>
                    {role.is_system ? <Badge tone="accent">System</Badge> : null}
                    {!role.is_active ? <Badge color="var(--muted)">Inactive</Badge> : null}
                  </div>
                  {role.description ? (
                    <div className="text-xs text-[var(--muted)]">{role.description}</div>
                  ) : null}
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{grantSummary(role)}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{role.staff_count}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Edit" onClick={() => openEdit(role)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    {!role.is_system ? (
                      <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(role)}>
                        <Trash2 className="h-4 w-4 text-[var(--error)]" />
                      </Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title={isNew ? "New role" : `Edit role · ${editing?.name ?? ""}`} onClose={close}>
        <div className="max-h-[72vh] space-y-4 overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Role name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Night Warden" />
            <Input label="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>

          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
              Permissions
            </h3>
            <Badge tone="accent">
              <ShieldCheck className="h-3 w-3" /> {selectedCount} selected
            </Badge>
          </div>

          <div className="space-y-3">
            {catalog.map((group) => {
              const allOn = group.permissions.every((p) => selected.has(p));
              return (
                <div key={group.module} className="rounded-xl border border-[var(--border)] p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-sm font-semibold capitalize text-[var(--foreground)]">
                      {group.module}
                    </span>
                    <button
                      type="button"
                      onClick={() => toggleModule(group.permissions, !allOn)}
                      className="text-xs font-medium text-[var(--accent)] hover:underline"
                    >
                      {allOn ? "Clear" : "Select all"}
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {group.permissions.map((perm) => {
                      const on = selected.has(perm);
                      return (
                        <button
                          key={perm}
                          type="button"
                          onClick={() => toggle(perm)}
                          className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition ${
                            on
                              ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                              : "border-[var(--border)] text-[var(--foreground-secondary)] hover:border-[var(--border-hover)]"
                          }`}
                          title={perm}
                        >
                          {prettyAction(perm)}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={close}>Cancel</Button>
            <Button loading={busy} onClick={save}>{isNew ? "Create role" : "Save changes"}</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
