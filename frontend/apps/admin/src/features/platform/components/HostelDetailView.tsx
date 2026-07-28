"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ChevronDown, ChevronRight } from "lucide-react";
import { EmptyState, Table, useToast } from "@hostel/ui";
import { platformApi } from "../api/platform.api";
import type {
  HostelDetail,
  HostelRoomRow,
  HostelStaffRow,
  HostelStudentDue,
  HostelStudentRow,
} from "../types/platform.types";
import { Badge, Tabs } from "./primitives";

const STATUS_TONE: Record<string, string> = {
  active: "var(--success)",
  trial: "var(--info)",
  expired: "var(--warning)",
  suspended: "var(--error)",
  pending: "var(--muted)",
};

type TabId = "overview" | "students" | "staff" | "rooms";

/** Super-admin, read-only drill-down into a single hostel — its own business
 * numbers, roster, staff and room occupancy. Every tab lazy-loads on first
 * visit and is cached for the rest of the session. */
export function HostelDetailView({ id }: { id: string }) {
  const toast = useToast();
  const [tab, setTab] = useState<TabId>("overview");

  const [detail, setDetail] = useState<HostelDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(true);

  const [students, setStudents] = useState<HostelStudentRow[] | null>(null);
  const [studentsLoading, setStudentsLoading] = useState(false);

  const [staff, setStaff] = useState<HostelStaffRow[] | null>(null);
  const [staffLoading, setStaffLoading] = useState(false);

  const [rooms, setRooms] = useState<HostelRoomRow[] | null>(null);
  const [roomsLoading, setRoomsLoading] = useState(false);

  useEffect(() => {
    setDetailLoading(true);
    platformApi.hostel
      .detail(id)
      .then(setDetail)
      .catch((e) => toast.error((e as Error).message))
      .finally(() => setDetailLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (tab === "students" && students === null && !studentsLoading) {
      setStudentsLoading(true);
      platformApi.hostel
        .students(id)
        .then(setStudents)
        .catch((e) => toast.error((e as Error).message))
        .finally(() => setStudentsLoading(false));
    }
    if (tab === "staff" && staff === null && !staffLoading) {
      setStaffLoading(true);
      platformApi.hostel
        .staff(id)
        .then(setStaff)
        .catch((e) => toast.error((e as Error).message))
        .finally(() => setStaffLoading(false));
    }
    if (tab === "rooms" && rooms === null && !roomsLoading) {
      setRoomsLoading(true);
      platformApi.hostel
        .rooms(id)
        .then(setRooms)
        .catch((e) => toast.error((e as Error).message))
        .finally(() => setRoomsLoading(false));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, id]);

  return (
    <div className="space-y-5">
      <Link
        href="/platform/hostels"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--muted)] hover:text-[var(--foreground)] transition"
      >
        <ArrowLeft className="h-4 w-4" />
        All hostels
      </Link>

      {detailLoading ? (
        <div className="text-sm text-[var(--muted)]">Loading hostel…</div>
      ) : !detail ? (
        <EmptyState title="Hostel not found" description="It may have been deleted." />
      ) : (
        <>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold text-[var(--foreground)]">{detail.name}</h2>
                <Badge color={STATUS_TONE[detail.status] || "var(--muted)"}>{detail.status}</Badge>
              </div>
              <div className="mt-0.5 text-xs text-[var(--muted)]">
                {detail.code} · {detail.owner_name || "—"}
                {detail.owner_email ? ` (${detail.owner_email})` : ""}
              </div>
            </div>
          </div>

          <Tabs
            tabs={[
              { id: "overview", label: "Overview" },
              { id: "students", label: "Students", count: students?.length },
              { id: "staff", label: "Staff", count: staff?.length },
              { id: "rooms", label: "Rooms", count: rooms?.length },
            ]}
            active={tab}
            onChange={(t) => setTab(t as TabId)}
          />

          {tab === "overview" && <OverviewTab detail={detail} />}
          {tab === "students" && (
            <StudentsTab hostelId={id} students={students} loading={studentsLoading} />
          )}
          {tab === "staff" && <StaffTab staff={staff} loading={staffLoading} />}
          {tab === "rooms" && <RoomsTab rooms={rooms} loading={roomsLoading} />}
        </>
      )}
    </div>
  );
}

function Tile({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5">
      <div className="text-sm text-[var(--muted)]">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-[var(--foreground)]">{value}</div>
      {sub ? <div className="text-xs text-[var(--muted)]">{sub}</div> : null}
    </div>
  );
}

function OverviewTab({ detail }: { detail: HostelDetail }) {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Tile label="Plan" value={detail.plan_name || "No plan"} sub={detail.plan?.billing_interval} />
        <Tile label="MRR" value={`Rs. ${Number(detail.mrr).toLocaleString()}`} />
        <Tile label="Active students" value={detail.usage.active_students} />
        <Tile
          label="Occupancy"
          value={`${detail.usage.beds_occupied}/${detail.usage.beds_total}`}
          sub="beds occupied"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5">
          <div className="text-sm font-semibold text-[var(--foreground)]">Revenue this month</div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-[var(--foreground)]">
              Rs. {Number(detail.revenue_summary.month_revenue).toLocaleString()}
            </span>
          </div>
          {detail.revenue_summary.due_count > 0 && (
            <div className="mt-1 text-xs text-[var(--warning)]">
              Rs. {detail.revenue_summary.month_due} still due across {detail.revenue_summary.due_count}{" "}
              {detail.revenue_summary.due_count === 1 ? "ledger" : "ledgers"}
            </div>
          )}
        </div>
        <div className="rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5">
          <div className="text-sm font-semibold text-[var(--foreground)]">Contact</div>
          <div className="mt-2 space-y-1 text-sm text-[var(--foreground-secondary)]">
            <div>{detail.phone || "—"}</div>
            <div>{detail.address || "—"}</div>
            <div className="text-xs text-[var(--muted)]">{detail.timezone} · {detail.currency}</div>
          </div>
        </div>
      </div>

      {detail.plan_limits.length > 0 && (
        <div className="rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5">
          <div className="text-sm font-semibold text-[var(--foreground)] mb-3">Plan limits</div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {detail.plan_limits.map((l) => (
              <div key={l.key} className="text-sm">
                <span className="text-[var(--foreground-secondary)]">{l.name}: </span>
                <span className="font-medium text-[var(--foreground)]">
                  {l.is_unlimited ? "Unlimited" : `${l.value ?? l.default_value} ${l.unit}`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StudentsTab({
  hostelId,
  students,
  loading,
}: {
  hostelId: string;
  students: HostelStudentRow[] | null;
  loading: boolean;
}) {
  const toast = useToast();
  const [openId, setOpenId] = useState<string | null>(null);
  const [dues, setDues] = useState<HostelStudentDue[] | null>(null);
  const [duesLoading, setDuesLoading] = useState(false);

  async function toggle(studentId: string) {
    if (openId === studentId) {
      setOpenId(null);
      return;
    }
    setOpenId(studentId);
    setDues(null);
    setDuesLoading(true);
    try {
      setDues(await platformApi.hostel.studentDues(hostelId, studentId));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setDuesLoading(false);
    }
  }

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading students…</div>;
  if (!students || students.length === 0) {
    return <EmptyState title="No students" description="This hostel has no students yet." />;
  }

  return (
    <Table>
      <thead>
        <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
          <th className="px-4 py-3 font-medium"></th>
          <th className="px-4 py-3 font-medium">Student</th>
          <th className="px-4 py-3 font-medium">Room / Bed</th>
          <th className="px-4 py-3 font-medium">Status</th>
          <th className="px-4 py-3 font-medium text-right">This month</th>
          <th className="px-4 py-3 font-medium text-right">Outstanding</th>
        </tr>
      </thead>
      <tbody>
        {students.map((s) => (
          <React.Fragment key={s.id}>
            <tr
              className="cursor-pointer border-b border-[var(--border)] last:border-0 hover:bg-[var(--background-secondary)]"
              onClick={() => toggle(s.id)}
            >
              <td className="px-4 py-3 text-[var(--muted)]">
                {openId === s.id ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </td>
              <td className="px-4 py-3">
                <div className="font-medium text-[var(--foreground)]">{s.full_name}</div>
                <div className="text-xs text-[var(--muted)]">{s.phone}</div>
              </td>
              <td className="px-4 py-3 text-[var(--foreground-secondary)]">
                {s.room_no ? `${s.room_no} / ${s.bed_no}` : "—"}
              </td>
              <td className="px-4 py-3">
                <Badge tone="neutral">{s.status}</Badge>
              </td>
              <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
                {s.current_month_status || "—"}
              </td>
              <td className="px-4 py-3 text-right">
                {Number(s.total_outstanding) > 0 ? (
                  <span className="text-[var(--warning)]">Rs. {s.total_outstanding}</span>
                ) : (
                  "—"
                )}
              </td>
            </tr>
            {openId === s.id && (
              <tr className="border-b border-[var(--border)] last:border-0 bg-[var(--background-secondary)]">
                <td />
                <td colSpan={5} className="px-4 py-3">
                  {duesLoading ? (
                    <span className="text-sm text-[var(--muted)]">Loading dues…</span>
                  ) : !dues || dues.length === 0 ? (
                    <span className="text-sm text-[var(--muted)]">No fee history.</span>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {dues.map((d) => (
                        <div
                          key={d.month}
                          className="rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-1.5 text-xs"
                        >
                          <span className="font-medium text-[var(--foreground)]">{d.month}</span>{" "}
                          <span className="text-[var(--muted)]">·</span>{" "}
                          <span className="text-[var(--foreground-secondary)]">Rs. {d.net_due}</span>{" "}
                          <Badge tone="neutral">{d.status}</Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </td>
              </tr>
            )}
          </React.Fragment>
        ))}
      </tbody>
    </Table>
  );
}

function StaffTab({ staff, loading }: { staff: HostelStaffRow[] | null; loading: boolean }) {
  if (loading) return <div className="text-sm text-[var(--muted)]">Loading staff…</div>;
  if (!staff || staff.length === 0) {
    return <EmptyState title="No staff" description="This hostel has no staff accounts yet." />;
  }
  return (
    <Table>
      <thead>
        <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
          <th className="px-4 py-3 font-medium">Staff</th>
          <th className="px-4 py-3 font-medium">Role</th>
          <th className="px-4 py-3 font-medium">Department</th>
          <th className="px-4 py-3 font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        {staff.map((s) => (
          <tr key={s.id} className="border-b border-[var(--border)] last:border-0">
            <td className="px-4 py-3">
              <div className="font-medium text-[var(--foreground)]">{s.full_name}</div>
              <div className="text-xs text-[var(--muted)]">{s.email || s.username}</div>
            </td>
            <td className="px-4 py-3 text-[var(--foreground-secondary)]">
              {s.role_name || s.account_role || "—"}
            </td>
            <td className="px-4 py-3 text-[var(--foreground-secondary)]">
              {s.department_name || "—"}
            </td>
            <td className="px-4 py-3">
              <Badge tone="neutral">{s.status}</Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function RoomsTab({ rooms, loading }: { rooms: HostelRoomRow[] | null; loading: boolean }) {
  if (loading) return <div className="text-sm text-[var(--muted)]">Loading rooms…</div>;
  if (!rooms || rooms.length === 0) {
    return <EmptyState title="No rooms" description="This hostel has no rooms set up yet." />;
  }
  return (
    <Table>
      <thead>
        <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
          <th className="px-4 py-3 font-medium">Room</th>
          <th className="px-4 py-3 font-medium">Type</th>
          <th className="px-4 py-3 font-medium">Status</th>
          <th className="px-4 py-3 font-medium text-right">Occupancy</th>
        </tr>
      </thead>
      <tbody>
        {rooms.map((r) => (
          <tr key={r.id} className="border-b border-[var(--border)] last:border-0">
            <td className="px-4 py-3">
              <div className="font-medium text-[var(--foreground)]">{r.room_no}</div>
              <div className="text-xs text-[var(--muted)]">
                {r.block_name ? `${r.block_name} · ` : ""}Floor {r.floor}
              </div>
            </td>
            <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.room_type}</td>
            <td className="px-4 py-3">
              <Badge tone="neutral">{r.status}</Badge>
            </td>
            <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
              {r.beds_occupied}/{r.beds_total}
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
