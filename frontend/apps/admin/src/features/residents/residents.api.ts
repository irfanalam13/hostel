import { api } from "@hostel/api";
import type { Resident, Stay } from "./residents.types";

export async function listResidents(params?: { search?: string; status?: string }) {
  const res = await api.get<Resident[]>("/residents/", { params });
  return res.data;
}

export async function createResident(payload: Partial<Resident>) {
  const res = await api.post<Resident>("/residents/", payload);
  return res.data;
}

export async function listStays(params?: { resident?: string; is_active?: boolean }) {
  const res = await api.get<Stay[]>("/residents/stays/", { params });
  return res.data;
}

export async function createStay(payload: Partial<Stay>) {
  const res = await api.post<Stay>("/residents/stays/", payload);
  return res.data;
}
