"use client";

import { ScrollText, CreditCard } from "lucide-react";
import { ActivitySection } from "@/features/account/components/ActivitySection";
import { BillingSection as AccountBillingSection } from "@/features/account/components/BillingSection";
import { SectionHeader } from "../primitives";

/**
 * Audit logs. Reuses the account activity timeline (server audit log) rather
 * than duplicating the fetch + rendering logic.
 */
export function AuditSection() {
  return (
    <div className="space-y-5">
      <SectionHeader
        icon={ScrollText}
        title="Audit Logs"
        description="Recent sign-ins, security and account events, newest first."
        status="partial"
      />
      <ActivitySection />
    </div>
  );
}

/** Plan & billing. Reuses the account billing preview surface. */
export function BillingSettingsSection() {
  return (
    <div className="space-y-5">
      <SectionHeader
        icon={CreditCard}
        title="Plan & Billing"
        description="Your subscription, storage usage and invoices."
        status="partial"
      />
      <AccountBillingSection />
    </div>
  );
}
