"use client";

import { useAuth } from "@hostel/auth";

/**
 * Parent portal home (Prompt 02 stub). Route access is enforced by the
 * protected layout via routePolicy ("parent-portal:view" — held only by
 * PARENT/GUARDIAN roles), and by the backend on every API call. The full
 * portal experience ships in a later prompt.
 */
export default function ParentDashboardPage() {
  const { user } = useAuth();
  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-bold text-[var(--foreground)]">
        Welcome{user?.username ? `, ${user.username}` : ""}
      </h1>
      <p className="mt-2 text-sm text-[var(--muted)]">
        This is your parent portal. Your child&apos;s stay, payments and
        notices will appear here.
      </p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {["Payments", "Attendance", "Notices", "Contact the hostel"].map((label) => (
          <div
            key={label}
            className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5 text-sm text-[var(--muted)]"
          >
            <div className="font-semibold text-[var(--foreground)]">{label}</div>
            <div className="mt-1">Coming soon.</div>
          </div>
        ))}
      </div>
    </div>
  );
}
