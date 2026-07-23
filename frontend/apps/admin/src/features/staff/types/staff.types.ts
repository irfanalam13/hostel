/** Staff Management domain types — mirror of the `apps.staff` DRF serializers. */

export type StaffStatus = "active" | "invited" | "suspended" | "disabled" | "locked";

export type EmploymentType =
  | "full_time"
  | "part_time"
  | "contract"
  | "temporary"
  | "internship";

export type SalaryType = "monthly" | "hourly" | "daily" | "contract";

export interface Role {
  id: string;
  name: string;
  slug: string;
  description: string;
  permissions: string[];
  is_system: boolean;
  is_active: boolean;
  staff_count: number;
  created_at: string;
  updated_at: string;
}

export interface Department {
  id: string;
  name: string;
  code: string;
  description: string;
  head: string | null;
  head_name: string | null;
  is_active: boolean;
  staff_count: number;
  created_at: string;
  updated_at: string;
}

export interface Designation {
  id: string;
  title: string;
  department: string | null;
  department_name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StaffDocument {
  id: string;
  staff: string;
  doc_type: string;
  doc_type_display: string;
  title: string;
  file: string;
  expiry_date: string | null;
  uploaded_by: number | null;
  created_at: string;
}

export interface StaffProfile {
  id: string;
  employee_id: string;
  user: number;
  username: string;
  email: string;
  account_role: string;
  account_active: boolean;
  last_login: string | null;
  full_name: string;
  status: StaffStatus;
  status_display: string;
  must_change_password: boolean;

  role_name: string | null;
  department_name: string | null;
  designation_title: string | null;
  reporting_manager_name: string | null;
  documents: StaffDocument[];

  // Personal
  first_name: string;
  middle_name: string;
  last_name: string;
  photo: string | null;
  gender: string;
  date_of_birth: string | null;
  nationality: string;
  citizenship_number: string;
  passport_number: string;
  marital_status: string;

  // Contact
  phone: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;

  // Address
  country: string;
  province: string;
  district: string;
  city: string;
  ward: string;
  street: string;
  postal_code: string;

  // Employment
  role: string | null;
  department: string | null;
  designation: string | null;
  reporting_manager: string | null;
  joining_date: string | null;
  employment_type: EmploymentType;
  work_location: string;
  shift: string;

  // Salary
  salary_type: SalaryType;
  basic_salary: string;
  allowances: string;
  tax_percentage: string;
  payment_method: string;
  bank_name: string;
  bank_account: string;
  pan_number: string;

  notes: string;
  created_at: string;
  updated_at: string;
}

/** The extra field only present on the create response (shown once). */
export interface StaffCreateResult extends StaffProfile {
  temporary_password?: string;
}

export interface CreateStaffPayload {
  username?: string;
  email?: string;
  account_role?: string;
  first_name?: string;
  middle_name?: string;
  last_name?: string;
  phone?: string;
  role?: string | null;
  department?: string | null;
  designation?: string | null;
  reporting_manager?: string | null;
  joining_date?: string | null;
  employment_type?: EmploymentType;
  work_location?: string;
  shift?: string;
  salary_type?: SalaryType;
  basic_salary?: string;
  [key: string]: unknown;
}

export interface PermissionCatalog {
  modules: { module: string; permissions: string[] }[];
}
