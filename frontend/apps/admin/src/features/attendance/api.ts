import { api } from "@hostel/api";
import { offlineWrite } from "@hostel/api";

export type AttendanceStatus = "present" | "absent" | "went_home";

export type Attendance = {
  id: number;
  resident: string;
  date: string;
  status: AttendanceStatus;
  note?: string;
};

export type MarkAttendanceInput = {
  resident: string;
  date: string;
  status: AttendanceStatus;
  note?: string;
};

export async function listAttendance(params?: { date?: string }) {
  const res = await api.get<Attendance[]>("/attendance/", { params });
  return res.data;
}

export function markAttendance(payload: MarkAttendanceInput) {
  // Offline-capable. The backend's unique (resident, date) constraint + the
  // idempotency key keep replays from creating a second row for the same day.
  return offlineWrite<Attendance>("/attendance/", payload, {
    label: `Attendance ${payload.status} (${payload.date})`,
    entity: "attendance",
  });
}
