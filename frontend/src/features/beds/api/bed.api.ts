import { apiFetch } from "@/shared/api/apiClient";
import { offlineWrite } from "@/shared/api/offlineWrite";
import type { Bed, BedAssignment, Block, Floor, Room } from "../types/bed.types";

export type { Bed, BedAssignment, Block, Floor, Room };

export function getBlocks(params?: { search?: string }) {
  const q = new URLSearchParams();
  if (params?.search) q.set("search", params.search);
  const qs = q.toString() ? `?${q.toString()}` : "";
  return apiFetch<Block[]>(`/rooms/blocks/${qs}`);
}

export function createBlock(payload: Partial<Block>) {
  return apiFetch<Block>("/rooms/blocks/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getFloors(params?: { block?: string; search?: string }) {
  const q = new URLSearchParams();
  if (params?.block) q.set("block", params.block);
  if (params?.search) q.set("search", params.search);
  const qs = q.toString() ? `?${q.toString()}` : "";
  return apiFetch<Floor[]>(`/rooms/floors/${qs}`);
}

export function createFloor(payload: Partial<Floor>) {
  return apiFetch<Floor>("/rooms/floors/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getRooms(params?: { search?: string; ordering?: string }) {
  const q = new URLSearchParams();
  if (params?.search) q.set("search", params.search);
  if (params?.ordering) q.set("ordering", params.ordering);
  const qs = q.toString() ? `?${q.toString()}` : "";
  return apiFetch<Room[]>(`/rooms/rooms/${qs}`);
}

export function createRoom(payload: Partial<Room>) {
  return apiFetch<Room>("/rooms/rooms/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getBeds(params?: { search?: string; status?: string; ordering?: string }) {
  const q = new URLSearchParams();
  if (params?.search) q.set("search", params.search);
  if (params?.status) q.set("status", params.status);
  if (params?.ordering) q.set("ordering", params.ordering);
  const qs = q.toString() ? `?${q.toString()}` : "";
  return apiFetch<Bed[]>(`/rooms/beds/${qs}`);
}

export function createBed(payload: Partial<Bed>) {
  return apiFetch<Bed>("/rooms/beds/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getActiveAssignments(params?: { ordering?: string }) {
  const q = new URLSearchParams();
  q.set("is_active", "true");
  q.set("ordering", params?.ordering ?? "-start_date");
  return apiFetch<BedAssignment[]>(`/rooms/bed-assignments/?${q.toString()}`);
}

export async function getActiveAssignmentByStudent(studentId: string) {
  const q = new URLSearchParams();
  q.set("student", String(studentId));
  q.set("is_active", "true");
  const res = await apiFetch<BedAssignment[]>(`/rooms/bed-assignments/?${q.toString()}`);
  return res?.[0] ?? null;
}

export async function getActiveAssignmentByBed(bedId: string) {
  const q = new URLSearchParams();
  q.set("bed", String(bedId));
  q.set("is_active", "true");
  const res = await apiFetch<BedAssignment[]>(`/rooms/bed-assignments/?${q.toString()}`);
  return res?.[0] ?? null;
}

export function createBedAssignment(
  payload: Pick<BedAssignment, "student" | "bed" | "is_active" | "start_date">
) {
  // Offline-capable room allocation. The conditional unique constraint on active
  // assignments + the idempotency key prevent a double-booked bed on replay.
  return offlineWrite<BedAssignment>("/rooms/bed-assignments/", payload, {
    label: "Allocate room / bed",
    entity: "bed_assignment",
  });
}

export function endBedAssignment(assignmentId: string, payload: { is_active: false; end_date: string }) {
  return apiFetch<BedAssignment>(`/rooms/bed-assignments/${assignmentId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
