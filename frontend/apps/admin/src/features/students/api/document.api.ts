import { api } from "@hostel/api";

export async function uploadDocument(data: FormData) {
  const res = await api.post("/students/student-documents/", data);
  return res.data;
}
