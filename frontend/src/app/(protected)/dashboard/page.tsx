"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useApi } from "@/shared/hooks/useApi";
import { loadState } from "@/features/hostels/store";
import { ymToday } from "@/shared/lib/dates";
import { computeDues, occupancy, sumPayments } from "@/shared/lib/finance";
import { getOwnerDashboard } from "@/features/dashboard/api";
import type { OwnerDashboardResponse } from "@/features/dashboard/types";
import { DashboardAnalytics } from "@/features/dashboard/components/DashboardAnalytics";
import { DashboardWidgets } from "@/features/dashboard/components/DashboardWidgets";
import { Button } from "@/shared/ui/Button";
import { PageSkeleton } from "@/shared/ui/Skeleton";
import { Topbar } from "@/shared/ui/Topbar";
import {
  AlertCircle,
  AlertTriangle,
  Bed,
  CheckSquare,
  CreditCard,
  DollarSign,
  Home,
  Receipt,
  RefreshCw,
  Settings,
  TrendingUp,
  UserCheck,
  UserPlus,
  UserRound,
  Users,
} from "lucide-react";

function formatMoney(value: number) {
  return Number(value || 0).toLocaleString();
}

function KpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  tone = "accent",
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  tone?: "accent" | "success" | "warning" | "error";
}) {
  const toneVar =
    tone === "success"
      ? "var(--success)"
      : tone === "warning"
        ? "var(--warning)"
        : tone === "error"
          ? "var(--error)"
          : "var(--accent)";

  return (
    <div className="min-w-[82vw] sm:min-w-0 snap-start flex-shrink-0 rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5 shadow-[var(--shadow-sm)] transition duration-200 hover:-translate-y-0.5 hover:border-[var(--border-hover)] hover:shadow-[var(--shadow-md)]">
      <div className="flex items-start justify-between gap-3">
        <span className="text-sm font-semibold leading-none text-[var(--muted)]">{title}</span>
        <div
          className="rounded-xl p-2"
          style={{
            color: toneVar,
            backgroundColor: `color-mix(in srgb, ${toneVar} 12%, transparent)`,
          }}
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div className="mt-4">
        <div className="text-2xl font-bold text-[var(--foreground)]">{value}</div>
        <p className="mt-1 text-[10px] font-semibold text-[var(--muted)]">{subtitle}</p>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [tick, setTick] = useState(0);
  const ym = ymToday();

  const { data, loading, error, refetch } = useApi<OwnerDashboardResponse>(
    () => getOwnerDashboard(),
    { deps: [] }
  );

  useEffect(() => {
    const onFocus = () => setTick((t) => t + 1);
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  const state = useMemo(() => loadState(), [tick]);

  const dateCardInfo = useMemo(() => {
    const d = new Date();
    return {
      dateStr: d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }),
      dayStr: d.toLocaleDateString("en-US", { weekday: "long" }),
    };
  }, []);

  const derivedStats = useMemo(() => {
    const activeStudents = state.students.filter((s) => s.status === "active");
    const todayColl = sumPayments(state.payments, ym, true);
    const monthColl = sumPayments(state.payments, ym, false);
    const { totalDue, studentsDue } = computeDues(activeStudents, state.payments, ym);
    const occ = occupancy(state.students, state.rooms, state.beds);
    const totalBeds = occ.totalBeds || state.settings.totalBeds || 20;
    const occupied = occ.occupied;
    const available = Math.max(0, totalBeds - occupied);

    return {
      todayColl,
      monthColl,
      totalDue,
      studentsDue,
      totalBeds,
      occupied,
      available,
      activeCount: activeStudents.length,
    };
  }, [state, ym]);

  const stats = {
    todayCollection: data?.today_collection ?? derivedStats.todayColl,
    monthCollection: data?.month_collection ?? derivedStats.monthColl,
    totalDue: data?.total_due_this_month ?? derivedStats.totalDue,
    studentsDue: data?.due_students_this_month ?? derivedStats.studentsDue,
    totalBeds: data?.beds.total ?? derivedStats.totalBeds,
    occupiedBeds: data?.beds.occupied ?? derivedStats.occupied,
    availableBeds: data?.beds.available ?? derivedStats.available,
    activeResidents: data?.total_residents ?? derivedStats.activeCount,
  };

  const quickAccessItems = [
    { name: "Admissions", href: "/admissions", icon: UserPlus },
    { name: "Students", href: "/students", icon: Users },
    { name: "Residents", href: "/residents", icon: UserCheck },
    { name: "Rooms", href: "/rooms", icon: Home },
    { name: "Beds", href: "/beds", icon: Bed },
    { name: "Fees", href: "/fees", icon: Receipt },
    { name: "Payments", href: "/payments", icon: CreditCard },
    { name: "Attendance", href: "/attendance", icon: CheckSquare },
    { name: "Visitors", href: "/visitors", icon: UserRound },
    { name: "Complaints", href: "/complaints", icon: AlertTriangle },
    { name: "More", href: "/settings", icon: Settings },
  ];

  if (loading) {
    return (
      <div className="flex min-w-0 flex-1 flex-col bg-[var(--background)] text-[var(--foreground)]">
        <Topbar title="Dashboard" />
        <div className="space-y-6 p-6 md:p-8">
          <PageSkeleton />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen min-w-0 flex-1 flex-col bg-[var(--background)] pb-12 text-[var(--foreground)] transition-colors duration-200">
      <Topbar title="Dashboard Overview" />

      <div className="mx-auto w-full max-w-[1600px] space-y-8 p-6 md:p-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-[var(--foreground)] md:text-3xl">
              Welcome back, Admin
            </h2>
            <p className="mt-1 text-sm font-medium text-[var(--muted)]">
              Here&apos;s what&apos;s happening in{" "}
              <b className="text-[var(--accent)]">{state.settings.hostelName}</b> today.
            </p>
          </div>

          <div className="flex items-center gap-3 self-start rounded-[20px] border border-[var(--border)] bg-[var(--card)] px-4 py-2.5 shadow-[var(--shadow-sm)] md:self-auto">
            <div className="rounded-xl bg-[var(--accent-soft)] px-2.5 py-1.5 text-xs font-bold text-[var(--accent)]">
              Today
            </div>
            <div className="text-left leading-tight">
              <div className="text-xs font-bold text-[var(--foreground)]">{dateCardInfo.dateStr}</div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--muted)]">
                {dateCardInfo.dayStr}
              </div>
            </div>
          </div>
        </div>

        <div className="flex snap-x snap-mandatory gap-4 overflow-x-auto pb-4 sm:grid sm:grid-cols-2 sm:overflow-visible sm:pb-0 lg:grid-cols-4 xl:grid-cols-5">
          <KpiCard
            title="Today Collection"
            value={`Rs. ${formatMoney(stats.todayCollection)}`}
            subtitle="Collected today"
            icon={TrendingUp}
          />
          <KpiCard
            title="This Month"
            value={`Rs. ${formatMoney(stats.monthCollection)}`}
            subtitle="Monthly collection"
            icon={DollarSign}
            tone="success"
          />
          <KpiCard
            title="Total Due"
            value={`Rs. ${formatMoney(stats.totalDue)}`}
            subtitle={`${stats.studentsDue} students due`}
            icon={AlertCircle}
            tone="error"
          />
          <KpiCard
            title="Total Beds"
            value={String(stats.totalBeds)}
            subtitle={`Occupied ${stats.occupiedBeds} / Available ${stats.availableBeds}`}
            icon={Bed}
          />
          <KpiCard
            title="Active Residents"
            value={String(stats.activeResidents)}
            subtitle="Currently active students"
            icon={Users}
          />
        </div>

        <section className="space-y-4">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-[var(--foreground-secondary)]">
            Quick Access Modules
          </h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6 xl:grid-cols-11">
            {quickAccessItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className="group flex flex-col items-center justify-center rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-3.5 text-center shadow-[var(--shadow-sm)] transition-all duration-200 hover:-translate-y-0.5 hover:border-[var(--accent)] hover:shadow-[var(--shadow-md)]"
                >
                  <div className="rounded-xl bg-[var(--background-secondary)] p-2.5 text-[var(--foreground-secondary)] transition group-hover:bg-[var(--accent-soft)] group-hover:text-[var(--accent)]">
                    <Icon className="h-5 w-5 shrink-0" />
                  </div>
                  <span className="mt-2 text-xs font-semibold text-[var(--foreground-secondary)] transition group-hover:text-[var(--accent)]">
                    {item.name}
                  </span>
                </Link>
              );
            })}
          </div>
        </section>

        <DashboardAnalytics state={state} apiData={data || undefined} />

        {error && (
          <div className="flex items-center gap-3 rounded-[20px] border border-[color-mix(in_srgb,var(--warning)_28%,var(--border))] bg-[color-mix(in_srgb,var(--warning)_10%,var(--card))] p-4 text-xs text-[var(--foreground-secondary)]">
            <AlertCircle className="h-5 w-5 shrink-0 text-[var(--warning)]" />
            <div>
              <span className="font-bold text-[var(--foreground)]">Standalone demo mode:</span> Connection to backend API failed ({error}). Displaying local storage state variables.
            </div>
            <Button variant="secondary" size="sm" onClick={refetch} className="ml-auto">
              <RefreshCw className="h-3 w-3" />
              <span>Retry</span>
            </Button>
          </div>
        )}

        <DashboardWidgets state={state} />
      </div>
    </div>
  );
}
