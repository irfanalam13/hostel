"use client";

import { useState } from "react";
import type { AuthUser } from "@/features/auth/api/auth.api";
import { authApi } from "@/features/auth/api/auth.api";
import { Button } from "@hostel/ui";
import { Card } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { useToast } from "@hostel/ui";
import { Eye, EyeOff, KeyRound } from "lucide-react";
import { formatDateTime, passwordScore } from "../lib";
import { ActiveSessions } from "./ActiveSessions";
import { ApiTokensCard, ConnectedAccountsCard, TwoFactorCard } from "./SecurityShells";

const STRENGTH = [
  { label: "Too weak", color: "var(--error)" },
  { label: "Weak", color: "var(--error)" },
  { label: "Fair", color: "var(--warning)" },
  { label: "Good", color: "var(--info)" },
  { label: "Strong", color: "var(--success)" },
];

export function SecuritySection({ user }: { user: AuthUser | null }) {
  const toast = useToast();
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
      setOldPassword("");
      setNewPassword("");
      setConfirm("");
      toast.success("Your password has been changed.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't change your password.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <div className="mb-1 flex items-center gap-2 text-base font-semibold text-[var(--foreground)]">
          <KeyRound className="h-4 w-4 text-[var(--accent)]" />
          Change password
        </div>
        <p className="mb-4 text-sm text-[var(--muted)]">
          Use at least 8 characters. A mix of upper/lowercase, numbers and symbols is strongest.
        </p>

        <div className="grid max-w-md gap-4">
          <Input
            label="Current password"
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

          <div className="flex justify-end">
            <Button loading={saving} disabled={!canSubmit} onClick={submit}>
              Update password
            </Button>
          </div>
        </div>
      </Card>

      <Card>
        <div className="mb-3 text-base font-semibold text-[var(--foreground)]">Sign-in activity</div>
        <div className="flex items-center justify-between rounded-xl bg-[var(--background-secondary)] px-4 py-3">
          <div>
            <div className="text-sm font-medium text-[var(--foreground)]">Last successful sign-in</div>
            <div className="text-xs text-[var(--muted)]">This is the most recent time your account was accessed.</div>
          </div>
          <span className="text-sm font-medium text-[var(--foreground-secondary)]">
            {formatDateTime(user?.last_login)}
          </span>
        </div>
      </Card>

      <ActiveSessions />

      <TwoFactorCard />

      <ConnectedAccountsCard />

      <ApiTokensCard />
    </div>
  );
}
