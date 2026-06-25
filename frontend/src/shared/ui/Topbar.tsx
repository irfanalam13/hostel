"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Button } from "./Button";
import { useAuth } from "@/shared/auth/AuthProvider";

const nav = [
  { href: "/dashboard", label: "Home" },
  { href: "/admissions", label: "Admissions" },
  { href: "/students", label: "Students" },
  //{ href: "/residents", label: "Residents" },
  //{ href: "/rooms", label: "Rooms" },
  //{ href: "/beds", label: "Beds" },
  { href: "/fees", label: "Fees" },
  //{ href: "/payments", label: "Payments" },
  { href: "/billing", label: "Billing" },
  //{ href: "/attendance", label: "Attendance" },
  //{ href: "/gate", label: "Gate" },
  //{ href: "/leave", label: "Leave" },
  //{ href: "/visitors", label: "Visitors" },
  //{ href: "/complaints", label: "Complaints" },
  //{ href: "/notices", label: "Notices" },
  //{ href: "/vacate", label: "Vacate" },
  //{ href: "/reports", label: "Reports" },
  //{ href: "/exports", label: "Exports" },
  { href: "/settings", label: "Settings" },
  { href: "/profile", label: "Profile" },
  //{ href: "/backup", label: "Backup" },
];

export function Topbar({ title = "Dashboard" }: { title?: string }) {
  const pathname = usePathname();
  const { role, logout } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);

  async function onLogout() {
    // Guard against logout race conditions / double clicks.
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <div className="sticky top-0 z-40 border-b border-zinc-200 bg-white/80 backdrop-blur">
      <div className="max-w-6xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-lg font-semibold">{title}</div>
            <div className="text-xs text-zinc-500">Role: {role ?? "unknown"}</div>
          </div>

          <Button variant="ghost" onClick={onLogout} loading={loggingOut}>
            {loggingOut ? "Logging out…" : "Logout"}
          </Button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {nav.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={[
                  "px-3 py-1.5 rounded-full text-sm border transition",
                  active
                    ? "bg-zinc-900 text-white border-zinc-900"
                    : "bg-white text-zinc-700 border-zinc-200 hover:bg-zinc-50",
                ].join(" ")}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
