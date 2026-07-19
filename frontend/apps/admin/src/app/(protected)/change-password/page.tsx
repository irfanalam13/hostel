"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@hostel/auth";
import { normalizeRole, postAuthHome } from "@hostel/permissions";
import { Button, Input, useToast } from "@hostel/ui";
import { Eye, EyeOff, KeyRound, ShieldCheck } from "lucide-react";
import { authApi } from "@/features/auth/api/auth.api";
import { passwordScore } from "@/features/account/lib";

const STRENGTH = [
  { label: "Too weak", color: "var(--error)" },
  { label: "Weak", color: "var(--error)" },
  { label: "Fair", color: "var(--warning)" },
  { label: "Good", color: "var(--info)" },
  { label: "Strong", color: "var(--success)" },
];

// First-login forced password change. Accounts provisioned with a temporary or
// default password (staff, team invite, student admission) are funnelled here
// by the (protected) layout until they set their own password. Rendered as a
// full-screen overlay so the app shell behind it is not a distraction.
export default function ChangePasswordPage() {
  const router = useRouter();
  const toast = useToast();
  const { role, refresh } = useAuth();

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [saving, setSaving] = useState(false);

  const score = passwordScore(newPassword);
  const mismatch = confirm.length > 0 && confirm !== newPassword;
  const canSubmit =
    oldPassword.length > 0 && newPassword.length >= 8 && confirm === newPassword && !saving;

  async function submit() {
    if (!canSubmit) return;
    setSaving(true);
    try {
      await authApi.changePassword({ old_password: oldPassword, new_password: newPassword });
      // Re-read /auth/me so must_change_password clears before we navigate,
      // otherwise the layout gate would bounce us straight back here.
      await refresh();
      toast.success("Password updated. Welcome aboard!");
      router.replace(postAuthHome(normalizeRole(role)));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't change your password.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-[var(--background)] p-4">
      <div className="w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--card,var(--background))] p-6 shadow-xl sm:p-8">
        <div className="mb-2 flex items-center gap-2 text-[var(--accent)]">
          <ShieldCheck className="h-6 w-6" />
        </div>
        <h1 className="text-xl font-semibold text-[var(--foreground)]">Set a new password</h1>
        <p className="mt-1 mb-6 text-sm text-[var(--muted)]">
          Your account was created with a temporary password. Choose your own password to finish
          signing in — you&apos;ll use it every time from now on.
        </p>

        <div className="grid gap-4">
          <Input
            label="Temporary / current password"
            type={show ? "text" : "password"}
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            autoComplete="current-password"
          />

          <div>
            <div className="relative">
              <Input
                label="New password"
                type={show ? "text" : "password"}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
              />
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                className="absolute right-3 top-9 text-[var(--muted)] transition hover:text-[var(--foreground)]"
                aria-label={show ? "Hide passwords" : "Show passwords"}
              >
                {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {newPassword.length > 0 && (
              <div className="mt-2">
                <div className="flex gap-1">
                  {[0, 1, 2, 3].map((i) => (
                    <span
                      key={i}
                      className="h-1.5 flex-1 rounded-full transition-colors"
                      style={{ backgroundColor: i < score ? STRENGTH[score].color : "var(--border)" }}
                    />
                  ))}
                </div>
                <p className="mt-1 text-xs font-medium" style={{ color: STRENGTH[score].color }}>
                  {STRENGTH[score].label}
                </p>
              </div>
            )}
          </div>

          <Input
            label="Confirm new password"
            type={show ? "text" : "password"}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
          />
          {mismatch && <p className="-mt-2 text-xs text-[var(--error)]">Passwords don&apos;t match.</p>}

          <Button loading={saving} disabled={!canSubmit} onClick={submit} className="w-full">
            <KeyRound className="mr-2 h-4 w-4" />
            Set password &amp; continue
          </Button>
        </div>
      </div>
    </div>
  );
}
