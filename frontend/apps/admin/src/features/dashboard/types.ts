export type OwnerDashboardResponse = {
  total_residents: number;
  today_collection: number;
  month_collection: number;
  this_month: string;
  total_due_this_month: number;
  due_students_this_month: number;
  pending_complaints: number;
  pending_admissions: number;
  today_entries: number;
  pending_leave_requests: number;
  beds: {
    total: number;
    occupied: number;
    available: number;
    occupancy_percent: number;
  };
};
