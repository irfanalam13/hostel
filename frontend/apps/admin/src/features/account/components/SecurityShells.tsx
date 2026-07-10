"use client";

import { Button } from "@hostel/ui";
import { Card } from "@hostel/ui";
import { useToast } from "@hostel/ui";
import { KeySquare, Link2, ShieldCheck } from "lucide-react";
import { ComingSoonBadge } from "./ComingSoon";

function useNotify() {
  const toast = useToast();
  return () => toast.info("This is a preview — the feature isn't enabled yet.");
}

export function TwoFactorCard() {
  const notify = useNotify();
  return (
    <Card>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-[var(--background-secondary)] text-[var(--muted)]">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-[var(--foreground)]">Two-factor authentication</span>
              <ComingSoonBadge />
            </div>
            <p className="mt-0.5 text-sm text-[var(--muted)]">
              Add an authenticator app and backup codes for a second layer of security.
            </p>
          </div>
        </div>
        <Button variant="secondary" onClick={notify} className="shrink-0">
          Enable 2FA
        </Button>
      </div>
    </Card>
  );
}

const PROVIDERS = ["Google", "Microsoft", "Apple", "GitHub"];

export function ConnectedAccountsCard() {
  const notify = useNotify();
  return (
    <Card>
      <div className="mb-4 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-base font-semibold text-[var(--foreground)]">
          <Link2 className="h-4 w-4 text-[var(--accent)]" />
          Connected accounts
        </div>
        <ComingSoonBadge />
      </div>
      <ul className="space-y-2">
        {PROVIDERS.map((name) => (
          <li
            key={name}
            className="flex items-center justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2.5"
          >
            <div className="flex items-center gap-3">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-[var(--card)] text-xs font-bold text-[var(--muted)]">
                {name.charAt(0)}
              </span>
              <div>
                <div className="text-sm font-medium text-[var(--foreground)]">{name}</div>
                <div className="text-xs text-[var(--muted)]">Not connected</div>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={notify}>
              Connect
            </Button>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function ApiTokensCard() {
  const notify = useNotify();
  return (
    <Card>
      <div className="mb-4 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-base font-semibold text-[var(--foreground)]">
          <KeySquare className="h-4 w-4 text-[var(--accent)]" />
          Personal access tokens
        </div>
        <ComingSoonBadge />
      </div>
      <div className="rounded-xl border border-dashed border-[var(--border)] bg-[var(--background-secondary)] px-4 py-8 text-center">
        <div className="text-2xl" aria-hidden>
          🔑
        </div>
        <p className="mt-2 text-sm font-medium text-[var(--foreground)]">No tokens yet</p>
        <p className="mx-auto mt-1 max-w-sm text-sm text-[var(--muted)]">
          Create scoped API tokens to integrate the hostel with your own tools. Rotation and
          expiry controls will land with this feature.
        </p>
        <Button variant="secondary" size="sm" className="mt-3" onClick={notify}>
          Create token
        </Button>
      </div>
    </Card>
  );
}
