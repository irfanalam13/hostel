export type ResidentStatus = "active" | "went_home" | "left";

export type Resident = {
  id: string;
  full_name: string;
  phone?: string;
  guardian_phone?: string;
  address?: string;
  join_date: string;
  leave_date?: string | null;
  status: ResidentStatus;
  current_bed?: string | null;
  monthly_fee: string;
  security_deposit: string;
  created_at?: string;
};

export type Stay = {
  id: string;
  resident: string;
  bed?: string | null;
  check_in: string;
  check_out?: string | null;
  is_active: boolean;
};
