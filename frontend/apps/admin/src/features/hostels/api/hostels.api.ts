import { api } from "@hostel/api";
import type { Hostel, Room } from "../types/hostels.types";

export async function listHostels(): Promise<Hostel[]> {
  const res = await api.get<Hostel[]>("/tenants/hostels/");
  return res.data;
}

export async function createHostel(payload: Partial<Hostel>) {
  const res = await api.post<Hostel>("/tenants/hostels/", payload);
  return res.data;
}

export async function listRooms(): Promise<Room[]> {
  const res = await api.get<Room[]>("/hostel/rooms/");
  return res.data;
}

export async function createRoom(payload: Partial<Room>) {
  const res = await api.post<Room>("/hostel/rooms/", payload);
  return res.data;
}
