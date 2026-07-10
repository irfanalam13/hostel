export type LeaveRequest = {
  id: string;
  resident?: string | null;
  resident_name?: string;
  student?: string | null;
  student_name?: string;
  start_date: string;
  end_date: string;
  reason?: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  decision_note?: string;
  created_at?: string;
};

export type VisitorLog = {
  id: string;
  resident?: string | null;
  resident_name?: string;
  student?: string | null;
  student_name?: string;
  visitor_name: string;
  visitor_phone?: string;
  relation?: string;
  purpose?: string;
  id_proof?: string;
  check_in_at?: string;
  check_out_at?: string | null;
  notes?: string;
};

export type EntryExitLog = {
  id: string;
  resident?: string | null;
  resident_name?: string;
  student?: string | null;
  student_name?: string;
  direction: "IN" | "OUT";
  event_at?: string;
  purpose?: string;
  note?: string;
};
