export type ComplaintStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";
export type ComplaintPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";

export type Complaint = {
  id: string;
  resident?: string | null;
  resident_name?: string;
  student?: string | null;
  student_name?: string;
  title: string;
  description?: string;
  category: string;
  priority: ComplaintPriority;
  status: ComplaintStatus;
  assigned_to?: string | null;
  assigned_to_name?: string;
  created_at?: string;
  resolved_at?: string | null;
};
