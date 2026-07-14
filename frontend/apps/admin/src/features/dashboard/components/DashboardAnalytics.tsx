"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertCircle, ChevronRight, TrendingUp } from "lucide-react";
import type { HostelState } from "@/features/hostels/types";
import type { OwnerDashboardResponse } from "../types";

type Props = {
  state: HostelState;
  apiData?: OwnerDashboardResponse;
};

const cardClass =
  "rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-6 shadow-[var(--shadow-sm)] transition duration-200 hover:border-[var(--border-hover)] hover:shadow-[var(--shadow-md)]";

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-2 text-xs shadow-[var(--shadow-lg)]">
      <div className="font-semibold text-[var(--foreground)]">{label}</div>
      <div className="text-[var(--foreground-secondary)]">Rs. {Number(payload[0].value || 0).toLocaleString()}</div>
    </div>
  );
}

export function DashboardAnalytics({ state, apiData }: Props) {
  const [selectedMonth, setSelectedMonth] = useState("June 2026");

  const paymentsByDay = state.payments.reduce((acc: Record<string, number>, payment) => {
    const day = payment.date.slice(5, 10);
    acc[day] = (acc[day] || 0) + payment.amount;
    return acc;
  }, {});

  const chartData = Object.entries(paymentsByDay)
    .map(([date, amount]) => ({ date, amount }))
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(-7);

  const displayChartData =
    chartData.length > 0
      ? chartData
      : [
          { date: "06-21", amount: 2000 },
          { date: "06-22", amount: 5000 },
          { date: "06-23", amount: 3500 },
          { date: "06-24", amount: 8000 },
          { date: "06-25", amount: 4500 },
          { date: "06-26", amount: 9000 },
          { date: "06-27", amount: 12000 },
        ];

  const totalCollection =
    apiData?.month_collection ??
    state.payments.filter((p) => p.date.startsWith("2026-06")).reduce((sum, p) => sum + p.amount, 0);

  const targetCollection = 50000;
  const percentOfTarget = Math.min(100, Math.round((totalCollection / targetCollection) * 100)) || 0;

  const activeStudents = state.students.filter((s) => s.status === "active");
  const dueAmount =
    apiData?.total_due_this_month ??
    activeStudents.reduce((sum, s) => {
      const paid = state.payments
        .filter((p) => p.studentId === s.id && p.date.startsWith("2026-06"))
        .reduce((a, p) => a + p.amount, 0);
      return sum + Math.max(0, s.monthlyFee - paid);
    }, 0);

  const studentsDueCount =
    apiData?.due_students_this_month ??
    activeStudents.filter((s) => {
      const paid = state.payments
        .filter((p) => p.studentId === s.id && p.date.startsWith("2026-06"))
        .reduce((a, p) => a + p.amount, 0);
      return s.monthlyFee > paid;
    }).length;

  const overdueStudents = activeStudents
    .map((s) => {
      const paid = state.payments
        .filter((p) => p.studentId === s.id && p.date.startsWith("2026-06"))
        .reduce((a, p) => a + p.amount, 0);
      const room = state.rooms.find((r) => r.id === s.roomId);
      return {
        id: s.id,
        name: s.fullName,
        room: room?.label ?? "N/A",
        due: Math.max(0, s.monthlyFee - paid),
      };
    })
    .filter((s) => s.due > 0)
    .sort((a, b) => b.due - a.due);

  const totalBeds = apiData?.beds.total ?? (state.beds.length || 20);
  const occupiedBeds = apiData?.beds.occupied ?? activeStudents.filter((s) => s.bedId).length;
  const maintenanceBeds = Math.min(2, Math.max(1, Math.round((totalBeds - occupiedBeds) * 0.1)));
  const availableBeds = Math.max(0, totalBeds - occupiedBeds - maintenanceBeds);

  const bedChartData = [
    { name: "Occupied", value: occupiedBeds, color: "#2563EB" },
    { name: "Available", value: availableBeds, color: "#22C55E" },
    { name: "Maintenance", value: maintenanceBeds, color: "#F59E0B" },
  ];

  return (
    <div className="mb-6 grid gap-6 md:grid-cols-1 xl:grid-cols-3">
      <div className={`${cardClass} flex flex-col justify-between`}>
        <div>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-[var(--foreground-secondary)]">Collection Overview</h3>
              <p className="text-[11px] text-[var(--muted)]">Monthly goal vs collections</p>
            </div>
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-2 py-1.5 text-xs text-[var(--foreground-secondary)] outline-none"
            >
              <option>June 2026</option>
              <option>May 2026</option>
              <option>April 2026</option>
            </select>
          </div>

          <div className="mb-6 flex items-center gap-6">
            <div>
              <div className="text-3xl font-bold text-[var(--foreground)]">Rs. {totalCollection.toLocaleString()}</div>
              <div className="mt-1 flex items-center gap-1 text-xs text-[var(--muted)]">
                <TrendingUp className="h-3.5 w-3.5 text-[var(--success)]" />
                <span>
                  Target: <b>Rs. {targetCollection.toLocaleString()}</b>
                </span>
              </div>
            </div>

            <div className="relative flex h-14 w-14 shrink-0 items-center justify-center">
              <svg className="h-full w-full -rotate-90">
                <circle cx="28" cy="28" r="23" stroke="var(--background-secondary)" strokeWidth="3.5" fill="transparent" />
                <circle
                  cx="28"
                  cy="28"
                  r="23"
                  stroke="var(--accent)"
                  strokeWidth="3.5"
                  fill="transparent"
                  strokeDasharray={2 * Math.PI * 23}
                  strokeDashoffset={2 * Math.PI * 23 * (1 - percentOfTarget / 100)}
                  strokeLinecap="round"
                />
              </svg>
              <span className="absolute text-xs font-semibold text-[var(--foreground)]">{percentOfTarget}%</span>
            </div>
          </div>
        </div>

        <div className="mt-2 h-40 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={displayChartData} margin={{ top: 5, right: 5, left: -25, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis dataKey="date" tickLine={false} tick={{ fontSize: 10, fill: "var(--muted)" }} />
              <YAxis tickLine={false} tick={{ fontSize: 10, fill: "var(--muted)" }} />
              <Tooltip content={<ChartTooltip />} />
              <Line
                type="monotone"
                dataKey="amount"
                stroke="var(--accent)"
                strokeWidth={3}
                dot={{ r: 4, stroke: "var(--accent)", strokeWidth: 2, fill: "var(--card)" }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className={`${cardClass} flex flex-col justify-between`}>
        <div>
          <h3 className="mb-1 text-sm font-semibold text-[var(--foreground-secondary)]">Dues Overview</h3>
          <p className="mb-4 text-[11px] text-[var(--muted)]">Outstanding balance tracker</p>

          <div className="mb-4 grid grid-cols-2 gap-4">
            <div className="rounded-xl border p-3" style={{ borderColor: "color-mix(in srgb, var(--error) 24%, var(--border))", backgroundColor: "color-mix(in srgb, var(--error) 8%, var(--card))" }}>
              <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--error)]">Due Amount</div>
              <div className="mt-0.5 text-lg font-bold text-[var(--error)]">Rs. {dueAmount.toLocaleString()}</div>
            </div>
            <div className="rounded-xl border p-3" style={{ borderColor: "color-mix(in srgb, var(--warning) 28%, var(--border))", backgroundColor: "color-mix(in srgb, var(--warning) 10%, var(--card))" }}>
              <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--warning)]">Students Due</div>
              <div className="mt-0.5 text-lg font-bold text-[var(--warning)]">{studentsDueCount} Students</div>
            </div>
          </div>
        </div>

        <div className="scrollbar-thin mb-2 flex max-h-[140px] min-h-[120px] flex-1 flex-col space-y-1.5 overflow-y-auto">
          {overdueStudents.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-xs text-[var(--muted)]">
              <AlertCircle className="mb-1.5 h-5 w-5 text-[var(--success)]" />
              <span>All dues cleared this month.</span>
            </div>
          ) : (
            overdueStudents.map((student) => (
              <div
                key={student.id}
                className="flex items-center justify-between rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-2 transition hover:border-[var(--border-hover)]"
              >
                <div>
                  <div className="text-xs font-semibold text-[var(--foreground)]">{student.name}</div>
                  <div className="text-[10px] text-[var(--muted)]">Room {student.room}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold text-[var(--error)]">Rs. {student.due.toLocaleString()}</div>
                  <Link href={`/payments?studentId=${student.id}`} className="text-[9px] font-bold text-[var(--accent)] hover:underline">
                    Collect
                  </Link>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className={`${cardClass} flex flex-col justify-between`}>
        <div>
          <h3 className="mb-1 text-sm font-semibold text-[var(--foreground-secondary)]">Bed Summary</h3>
          <p className="mb-4 text-[11px] text-[var(--muted)]">Realtime occupancy breakdown</p>

          <div className="mb-4 flex items-center justify-between gap-4">
            <div className="h-24 w-24 shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={bedChartData} cx="50%" cy="50%" innerRadius={30} outerRadius={45} paddingAngle={3} dataKey="value">
                    {bedChartData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="flex-1 space-y-1.5">
              {bedChartData.map((item) => (
                <div key={item.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1.5 text-[var(--foreground-secondary)]">
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />
                    <span>{item.name}</span>
                  </div>
                  <span className="font-bold text-[var(--foreground)]">{item.value}</span>
                </div>
              ))}
              <div className="flex items-center justify-between border-t border-[var(--border)] pt-1.5 text-xs font-semibold text-[var(--foreground-secondary)]">
                <span>Total Beds</span>
                <span>{totalBeds}</span>
              </div>
            </div>
          </div>
        </div>

        <Link
          href="/rooms"
          className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] py-2.5 text-xs font-semibold text-[var(--foreground-secondary)] transition hover:border-[var(--border-hover)] hover:text-[var(--foreground)]"
        >
          <span>View Details</span>
          <ChevronRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}
