"use client";

import { useEffect, useState } from "react";
import type { AuthUser } from "@/features/auth/api/auth.api";
import { authApi } from "@/features/auth/api/auth.api";
import { Button } from "@hostel/ui";
import { Card } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { useToast } from "@hostel/ui";

export function ProfileSection({
  user,
  onSaved,
}: {
  user: AuthUser | null;
  onSaved: () => void | Promise<void>;
}) {
  const toast = useToast();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setFirstName(user?.first_name || "");
    setLastName(user?.last_name || "");
    setEmail(user?.email || "");
  }, [user]);

  const dirty =
    firstName !== (user?.first_name || "") ||
    lastName !== (user?.last_name || "") ||
    email !== (user?.email || "");

  async function save() {
    setSaving(true);
    try {
      await authApi.updateMe({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
      });
      await onSaved();
      toast.success("Your profile has been updated.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't update your profile.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <div className="mb-1 text-base font-semibold text-[var(--foreground)]">Personal information</div>
      <p className="mb-4 text-sm text-[var(--muted)]">
        This is how your name and contact details appear across the hostel.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="First name"
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
          placeholder="e.g. Aayush"
          autoComplete="given-name"
        />
        <Input
          label="Last name"
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
          placeholder="e.g. Sharma"
          autoComplete="family-name"
        />
        <div className="sm:col-span-2">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
          />
          <p className="mt-1 text-xs text-[var(--muted)]">
            Used for password resets and account notices.
          </p>
        </div>
      </div>

      {/* Read-only identity */}
      <div className="mt-4 grid gap-4 border-t border-[var(--border)] pt-4 sm:grid-cols-2">
        <ReadOnly label="Username" value={user?.username || "—"} hint="Contact your owner to change this." />
        <ReadOnly label="Role" value={user?.role || "—"} hint="Assigned by your hostel owner." />
      </div>

      <div className="mt-5 flex items-center justify-end gap-3">
        {dirty && <span className="text-xs text-[var(--warning)]">Unsaved changes</span>}
        <Button loading={saving} disabled={!dirty} onClick={save}>
          Save changes
        </Button>
      </div>
    </Card>
  );
}

function ReadOnly({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <div className="mb-1 text-sm text-[var(--foreground-secondary)]">{label}</div>
      <div className="flex items-center justify-between rounded-xl border border-dashed border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2">
        <span className="text-sm font-medium text-[var(--foreground)]">{value}</span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--muted)]">Locked</span>
      </div>
      {hint && <p className="mt-1 text-xs text-[var(--muted)]">{hint}</p>}
    </div>
  );
}
