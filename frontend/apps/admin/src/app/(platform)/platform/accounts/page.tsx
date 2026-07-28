"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { AccountsDirectory } from "@/features/platform/components/AccountsDirectory";

export default function PlatformAccountsPage() {
  return (
    <PlatformShell
      title="Accounts"
      description="Every user account across every tenant and which hostel/plan they're on."
    >
      <AccountsDirectory />
    </PlatformShell>
  );
}
