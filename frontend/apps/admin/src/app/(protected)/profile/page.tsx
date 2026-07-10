"use client";

import { useState } from "react";
import { useAuth } from "@hostel/auth";
import { Topbar } from "@/components/shell/Topbar";
import { AccountHeader } from "@/features/account/components/AccountHeader";
import { ProfileCompletion } from "@/features/account/components/ProfileCompletion";
import { ProfileSection } from "@/features/account/components/ProfileSection";
import { SecuritySection } from "@/features/account/components/SecuritySection";
import { ActivitySection } from "@/features/account/components/ActivitySection";
import { BillingSection } from "@/features/account/components/BillingSection";
import { PreferencesSection } from "@/features/account/components/PreferencesSection";
import { DangerZoneSection } from "@/features/account/components/DangerZoneSection";
import { Activity, AlertTriangle, CreditCard, KeyRound, SlidersHorizontal, User } from "lucide-react";

type TabId = "profile" | "security" | "activity" | "billing" | "preferences" | "danger";

const TABS: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "profile", label: "Profile", icon: User },
  { id: "security", label: "Security", icon: KeyRound },
  { id: "activity", label: "Activity", icon: Activity },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "preferences", label: "Preferences", icon: SlidersHorizontal },
  { id: "danger", label: "Danger zone", icon: AlertTriangle },
];

export default function ProfilePage() {
  const { user, refresh } = useAuth();
  const [tab, setTab] = useState<TabId>("profile");

  return (
    <div className="space-y-5">
      <Topbar title="Account" />

      <AccountHeader user={user} />

      {/* Tab navigation */}
      <div className="sticky top-[72px] z-10 -mx-1 overflow-x-auto">
        <div className="flex gap-1 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-1 shadow-[var(--shadow-sm)]">
          {TABS.map(({ id, label, icon: Icon }) => {
            const active = tab === id;
            return (
              <button
                key={id}
                type="button"
                onClick={() => setTab(id)}
                aria-current={active ? "page" : undefined}
                className={`flex flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-xl px-4 py-2 text-sm font-medium transition ${
                  active
                    ? "bg-[var(--accent)] text-white shadow-sm"
                    : "text-[var(--foreground-secondary)] hover:bg-[var(--background-secondary)] hover:text-[var(--foreground)]"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className={id === "danger" ? "hidden sm:inline" : ""}>{label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab content */}
      <div>
        {tab === "profile" && (
          <div className="space-y-5">
            <ProfileCompletion user={user} />
            <ProfileSection user={user} onSaved={refresh} />
          </div>
        )}
        {tab === "security" && <SecuritySection user={user} />}
        {tab === "activity" && <ActivitySection />}
        {tab === "billing" && <BillingSection />}
        {tab === "preferences" && <PreferencesSection />}
        {tab === "danger" && <DangerZoneSection />}
      </div>
    </div>
  );
}
