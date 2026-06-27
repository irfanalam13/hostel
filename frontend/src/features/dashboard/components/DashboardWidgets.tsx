"use client";

import React from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, AlertTriangle, Bell, CreditCard, Shield, User } from "lucide-react";
import type { HostelState } from "@/features/hostels/types";

type Props = {
  state: HostelState;
};

const cardClass =
  "rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-6 shadow-[var(--shadow-sm)] transition duration-200 hover:border-[var(--border-hover)] hover:shadow-[var(--shadow-md)]";

function SectionTitle({
  icon: Icon,
  title,
  tone = "accent",
}: {
  icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>;
  title: string;
  tone?: "accent" | "success" | "warning" | "error";
}) {
  const color =
    tone === "success"
      ? "var(--success)"
      : tone === "warning"
        ? "var(--warning)"
        : tone === "error"
          ? "var(--error)"
          : "var(--accent)";
  return (
    <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-[var(--foreground-secondary)]">
      <Icon className="h-4 w-4" style={{ color }} />
      <span>{title}</span>
    </h3>
  );
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-2 text-xs shadow-[var(--shadow-lg)]">
      <div className="mb-1 font-semibold text-[var(--foreground)]">{label}</div>
      {payload.map((item: any) => (
        <div key={item.dataKey} className="text-[var(--foreground-secondary)]">
          {item.dataKey}: Rs. {Number(item.value || 0).toLocaleString()}
        </div>
      ))}
    </div>
  );
}

export function DashboardWidgets({ state }: Props) {
  const latestStudents = [...state.students].sort((a, b) => b.joinedAt.localeCompare(a.joinedAt)).slice(0, 4);

  const latestPayments = [...state.payments]
    .sort((a, b) => b.date.localeCompare(a.date))
    .slice(0, 4)
    .map((p) => {
      const student = state.students.find((s) => s.id === p.studentId);
      return {
        id: p.id,
        studentName: student?.fullName ?? "Unknown Student",
        amount: p.amount,
        date: p.date,
        method: p.note || "Cash / Transfer",
      };
    });

  const floorStats = state.rooms.reduce((acc: Record<string, { total: number; occupied: number }>, room) => {
    const floor = room.floor || "Ground Floor";
    const roomBeds = state.beds.filter((b) => b.roomId === room.id);
    const occupied = state.students.filter((s) => s.status === "active" && s.roomId === room.id).length;
    if (!acc[floor]) acc[floor] = { total: 0, occupied: 0 };
    acc[floor].total += roomBeds.length;
    acc[floor].occupied += occupied;
    return acc;
  }, {});

  const floorStatsArray = Object.entries(floorStats).map(([floor, stats]) => ({
    floor,
    percent: stats.total > 0 ? Math.round((stats.occupied / stats.total) * 100) : 0,
    ...stats,
  }));

  const paymentsByMonth = state.payments.reduce((acc: Record<string, number>, p) => {
    const month = p.date.slice(0, 7);
    acc[month] = (acc[month] || 0) + p.amount;
    return acc;
  }, {});

  const expensesByMonth = state.expenses.reduce((acc: Record<string, number>, e) => {
    const month = e.date.slice(0, 7);
    acc[month] = (acc[month] || 0) + e.amount;
    return acc;
  }, {});

  const months = Array.from(new Set([...Object.keys(paymentsByMonth), ...Object.keys(expensesByMonth)])).sort();
  const revenueChartData = months.map((m) => ({
    name: m.slice(5, 7) === "06" ? "Jun" : m.slice(5, 7) === "05" ? "May" : m.slice(5, 7) === "04" ? "Apr" : m,
    Income: paymentsByMonth[m] || 0,
    Expense: expensesByMonth[m] || 0,
  }));

  const displayRevenueData =
    revenueChartData.length > 0
      ? revenueChartData
      : [
          { name: "Jan", Income: 35000, Expense: 12000 },
          { name: "Feb", Income: 42000, Expense: 15000 },
          { name: "Mar", Income: 38000, Expense: 18000 },
          { name: "Apr", Income: 45000, Expense: 21000 },
          { name: "May", Income: 48000, Expense: 17000 },
          { name: "Jun", Income: 52000, Expense: 22000 },
        ];

  const collectionTrendData =
    state.payments.length > 0
      ? [...state.payments].reverse().slice(-6).map((p, idx) => ({ name: `P${idx + 1}`, amount: p.amount }))
      : [
          { name: "Wk 1", amount: 8000 },
          { name: "Wk 2", amount: 15000 },
          { name: "Wk 3", amount: 12000 },
          { name: "Wk 4", amount: 19000 },
          { name: "Wk 5", amount: 24000 },
          { name: "Wk 6", amount: 30000 },
        ];

  const latestActivity = state.audit.slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-1 xl:grid-cols-2">
        <div className={`${cardClass} flex flex-col justify-between`}>
          <div>
            <SectionTitle icon={User} title="Recent Admissions" />
            {latestStudents.length === 0 ? (
              <div className="py-12 text-center text-xs text-[var(--muted)]">No students admitted yet.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                      <th className="py-3 font-semibold uppercase tracking-wider">Student</th>
                      <th className="py-3 font-semibold uppercase tracking-wider">Joined Date</th>
                      <th className="py-3 font-semibold uppercase tracking-wider">Monthly Fee</th>
                      <th className="py-3 text-right font-semibold uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {latestStudents.map((s) => (
                      <tr key={s.id} className="transition hover:bg-[var(--background-secondary)]">
                        <td className="flex items-center gap-2.5 py-3.5 font-medium text-[var(--foreground)]">
                          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[10px] font-bold text-[var(--accent)]">
                            {s.fullName.slice(0, 2).toUpperCase()}
                          </div>
                          <span>{s.fullName}</span>
                        </td>
                        <td className="py-3.5 text-[var(--foreground-secondary)]">{s.joinedAt}</td>
                        <td className="py-3.5 text-[var(--foreground)]">Rs. {s.monthlyFee.toLocaleString()}</td>
                        <td className="py-3.5 text-right">
                          <span
                            className="rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider"
                            style={{
                              color: s.status === "active" ? "var(--success)" : "var(--muted)",
                              backgroundColor:
                                s.status === "active"
                                  ? "color-mix(in srgb, var(--success) 12%, transparent)"
                                  : "var(--background-secondary)",
                            }}
                          >
                            {s.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <div className={`${cardClass} flex flex-col justify-between`}>
          <div>
            <SectionTitle icon={CreditCard} title="Recent Payments" tone="success" />
            {latestPayments.length === 0 ? (
              <div className="py-12 text-center text-xs font-medium text-[var(--muted)]">No payments received yet.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                      <th className="py-3 font-semibold uppercase tracking-wider">Student</th>
                      <th className="py-3 font-semibold uppercase tracking-wider">Date</th>
                      <th className="py-3 font-semibold uppercase tracking-wider">Payment Note</th>
                      <th className="py-3 text-right font-semibold uppercase tracking-wider">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {latestPayments.map((p) => (
                      <tr key={p.id} className="transition hover:bg-[var(--background-secondary)]">
                        <td className="flex items-center gap-2.5 py-3.5 font-medium text-[var(--foreground)]">
                          <div className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-[var(--success)]" style={{ backgroundColor: "color-mix(in srgb, var(--success) 12%, transparent)" }}>
                            Rs
                          </div>
                          <span>{p.studentName}</span>
                        </td>
                        <td className="py-3.5 text-[var(--foreground-secondary)]">{p.date}</td>
                        <td className="py-3.5 capitalize text-[var(--muted)]">{p.method}</td>
                        <td className="py-3.5 text-right font-bold text-[var(--success)]">+Rs. {p.amount.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-1 xl:grid-cols-2">
        <div className={cardClass}>
          <SectionTitle icon={Activity} title="Revenue Statistics (Income vs Expense)" />
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={displayRevenueData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--muted)" }} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "var(--muted)" }} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: "11px", color: "var(--muted)" }} />
                <Bar dataKey="Income" fill="#2563EB" radius={[6, 6, 0, 0]} />
                <Bar dataKey="Expense" fill="#EF4444" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className={cardClass}>
          <SectionTitle icon={Activity} title="Fee Collection Trend" tone="success" />
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={collectionTrendData}>
                <defs>
                  <linearGradient id="dashboardCollectionAmount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22C55E" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#22C55E" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--muted)" }} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "var(--muted)" }} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="amount" stroke="#22C55E" strokeWidth={3} fillOpacity={1} fill="url(#dashboardCollectionAmount)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3">
        <div className={`${cardClass} flex flex-col justify-between`}>
          <div>
            <SectionTitle icon={Shield} title="Room Occupancy by Floor" />
            <div className="space-y-4">
              {floorStatsArray.length === 0 ? (
                <div className="py-10 text-center text-xs text-[var(--muted)]">No rooms or floors added.</div>
              ) : (
                floorStatsArray.map((item) => (
                  <div key={item.floor} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-[var(--foreground-secondary)]">{item.floor}</span>
                      <span className="font-semibold text-[var(--muted)]">
                        {item.occupied} / {item.total} Beds ({item.percent}%)
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--background-secondary)]">
                      <div className="h-full rounded-full bg-[var(--accent)] transition-all duration-300" style={{ width: `${item.percent}%` }} />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div className={`${cardClass} flex flex-col justify-between`}>
          <div>
            <SectionTitle icon={AlertTriangle} title="Pending Complaints" tone="error" />
            <div className="space-y-3">
              {[
                {
                  tone: "error",
                  label: "Critical",
                  time: "Today, 10:15 AM",
                  title: "Room 101 - Water Tap Leakage",
                  body: "Water overflowing from bathroom basin faucet.",
                },
                {
                  tone: "warning",
                  label: "Medium",
                  time: "Yesterday, 4:30 PM",
                  title: "Room 102 - Wifi disconnected",
                  body: "Speed is too low and drops continuously.",
                },
              ].map((item) => {
                const color = item.tone === "error" ? "var(--error)" : "var(--warning)";
                return (
                  <div
                    key={item.title}
                    className="rounded-xl border p-3"
                    style={{
                      borderColor: `color-mix(in srgb, ${color} 24%, var(--border))`,
                      backgroundColor: `color-mix(in srgb, ${color} 8%, var(--card))`,
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <span className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider" style={{ color, backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)` }}>
                        {item.label}
                      </span>
                      <span className="text-[9px] text-[var(--muted)]">{item.time}</span>
                    </div>
                    <p className="mt-1.5 text-xs font-semibold text-[var(--foreground)]">{item.title}</p>
                    <p className="mt-0.5 text-[10px] text-[var(--foreground-secondary)]">{item.body}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className={`${cardClass} flex flex-col justify-between`}>
          <div>
            <SectionTitle icon={Activity} title="Activity Timeline" tone="warning" />
            <div className="space-y-4">
              {latestActivity.length === 0 ? (
                <div className="py-10 text-center text-xs text-[var(--muted)]">No actions recorded in log.</div>
              ) : (
                <div className="relative space-y-4 border-l border-[var(--border)] pl-4 text-xs">
                  {latestActivity.map((log) => (
                    <div key={log.id} className="relative">
                      <span className="absolute -left-[20px] top-1 h-2.5 w-2.5 rounded-full border border-[var(--card)] bg-[var(--accent)]" />
                      <div className="font-semibold text-[var(--foreground)]">{log.message}</div>
                      <span className="mt-0.5 block text-[10px] text-[var(--muted)]">
                        {new Date(log.at).toLocaleDateString()} at{" "}
                        {new Date(log.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className={cardClass}>
        <SectionTitle icon={Bell} title="Latest Notices & Announcements" />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[
            {
              tag: "Notice",
              title: "Wi-Fi Maintenance Scheduled",
              body: "Wifi services will be down for 2 hours tomorrow for access point firmware upgrades.",
              meta: "Admins • 1 day ago",
            },
            {
              tag: "Power",
              title: "Generator Fuel Refill Complete",
              body: "The main diesel generator has been refilled. Power backup is fully active.",
              meta: "Operations • 2 days ago",
            },
            {
              tag: "Fees",
              title: "Monthly Dues Reminder",
              body: "Please ensure all pending monthly mess fees are paid and ledger entries are updated.",
              meta: "Billing • 3 days ago",
            },
          ].map((notice) => (
            <div key={notice.title} className="flex items-start gap-3 rounded-[20px] border border-[var(--border)] bg-[var(--background-secondary)] p-4">
              <span className="rounded-xl bg-[var(--accent-soft)] px-2 py-1 text-[10px] font-bold text-[var(--accent)]">
                {notice.tag}
              </span>
              <div>
                <h4 className="text-xs font-semibold text-[var(--foreground)]">{notice.title}</h4>
                <p className="mt-1 text-[11px] text-[var(--foreground-secondary)]">{notice.body}</p>
                <span className="mt-2 block text-[9px] font-medium text-[var(--muted)]">{notice.meta}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
