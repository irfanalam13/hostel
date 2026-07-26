"use client";

import { useState } from "react";
import { authApi } from "@/features/auth/api/auth.api";
import { useAuth } from "@hostel/auth";
import { Button } from "@hostel/ui";
import { useConfirm } from "@hostel/ui";
import { useToast } from "@hostel/ui";
import { AlertTriangle, LogOut } from "lucide-react";

export function DangerZoneSection() {
  const confirm = useConfirm();
  const toast = useToast();
  const { logout } = useAuth();
  const [busy, setBusy] = useState(false);

  async function signOutEverywhere() {
    const ok = await confirm({
      title: "Sign out of all devices?",
      message:
        "This revokes every active session for your account, including phones and other browsers. You'll need to sign in again everywhere.",
      confirmText: "Sign out everywhere",
      danger: true,
    });
    if (!ok) return;
    setBusy(true);
    try {
      await authApi.logoutAll();
      toast.success("Signed out of all devices.");
      await logout();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't sign out of all devices.");
      setBusy(false);
    }
  }

  return (
    <div className="rounded-[20px] border border-[var(--error)]/30 bg-[color-mix(in_srgb,var(--error)_5%,var(--card))] p-5 shadow-[var(--shadow-sm)]">
      <div className="mb-1 flex items-center gap-2 text-base font-semibold text-[var(--error)]">
        <AlertTriangle className="h-4 w-4" />
        Danger zone
      </div>
      <p className="mb-4 text-sm text-[var(--muted)]">
        Sensitive account actions. Deleting your account is handled by your hostel owner.
      </p>

      <div className="flex flex-col gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="text-sm font-semibold text-[var(--foreground)]">Sign out of all devices</div>
          <p className="text-sm text-[var(--muted)]">
            End every active session. Recommended if you&apos;ve lost a device or suspect unauthorized access.
          </p>
        </div>
        <Button variant="danger" loading={busy} onClick={signOutEverywhere} className="shrink-0">
          <LogOut className="h-4 w-4" />
          Sign out everywhere
        </Button>
      </div>
    </div>
  );
}
