import { api } from "@/shared/api/apiClient";

export async function uploadDocument(data: FormData) {
  const res = await api.post("/students/student-documents/", data);
  return res.data;
}
