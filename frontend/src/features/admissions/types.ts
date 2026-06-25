export type AdmissionStatus = "PENDING" | "APPROVED" | "REJECTED";

export type AdmissionRequest = {
  id: string;
  full_name: string;
  phone: string;
  email?: string;
  address?: string;
  guardian_name?: string;
  guardian_phone?: string;
  emergency_contact?: string;
  preferred_join_date?: string | null;
  requested_bed?: string | null;
  requested_bed_code?: string;
  approved_bed?: string | null;
  approved_bed_code?: string;
  student?: string | null;
  student_name?: string;
  source: "INTERNAL" | "PUBLIC";
  status: AdmissionStatus;
  notes?: string;
  decision_note?: string;
  created_at?: string;
};
