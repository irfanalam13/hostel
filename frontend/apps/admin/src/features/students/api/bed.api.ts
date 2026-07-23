import { api } from "@hostel/api";
import type { BedLite } from "@/features/students/types/student.types";

export async function getBeds(): Promise<BedLite[]> {
  const res = await api.get<BedLite[]>("/rooms/beds/");
  return res.data;
}
