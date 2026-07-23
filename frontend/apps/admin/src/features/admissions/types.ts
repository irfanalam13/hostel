// Mirrors backend/apps/admissions/models.py (AdmissionRequest + AdmissionDocument)

export type AdmissionStatus =
  | "PENDING"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "WAITLISTED";

export type AdmissionSource = "INTERNAL" | "PUBLIC" | "WALK_IN" | "WEBSITE" | "REFERRAL";
export type Gender = "MALE" | "FEMALE" | "OTHER";
export type EducationLevel = "SEE" | "PLUS2" | "BACHELOR" | "MASTER" | "OTHER";
export type ClassTiming = "MORNING" | "DAY" | "EVENING";
export type FoodPreference = "VEGETARIAN" | "EGGITARIAN" | "NON_VEGETARIAN";
export type BloodGroup = "A+" | "A-" | "B+" | "B-" | "AB+" | "AB-" | "O+" | "O-" | "UNKNOWN";
export type MaritalStatus = "SINGLE" | "MARRIED" | "OTHER";
export type RoomType = "SINGLE" | "DOUBLE" | "TRIPLE" | "FOUR_SHARING";
export type PaymentStatus = "PAID" | "PENDING" | "PARTIAL";

export type AdmissionDocType =
  | "passport_photo"
  | "citizenship_front"
  | "citizenship_back"
  | "birth_certificate"
  | "guardian_citizenship"
  | "academic_certificate"
  | "migration_certificate"
  | "character_certificate"
  | "medical_report"
  | "other_documents";

export interface AdmissionDocument {
  id: string;
  doc_type: AdmissionDocType;
  file: string;
  uploaded_at: string;
}

export interface AdmissionRequest {
  id: string;

  // Section 1: Application Information
  application_number: string;
  application_date: string;
  application_fee: string | number;
  form_number?: string;
  source: AdmissionSource;

  // Section 2: Student Profile
  full_name: string;
  name_nepali?: string;
  date_of_birth?: string | null;
  gender: Gender;
  phone: string;
  alternate_phone?: string;
  email?: string;
  photo?: string | null;

  // Permanent address
  province?: string;
  district?: string;
  municipality?: string;
  ward_number?: string;
  street_tole?: string;

  // Temporary address
  temp_province?: string;
  temp_district?: string;
  temp_municipality?: string;
  temp_ward_number?: string;
  temp_street_tole?: string;

  // Identity
  citizenship_number?: string;
  citizenship_issue_date?: string | null;
  citizenship_issue_district?: string;
  nationality?: string;
  religion?: string;
  blood_group: BloodGroup;
  marital_status: MaritalStatus;

  // Health
  medical_condition?: string;
  disability?: string;

  // Emergency contact
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  emergency_contact_relation?: string;

  // Section 3: Education
  educational_institute?: string;
  current_level: EducationLevel;
  faculty?: string;
  roll_number?: string;
  class_timing: ClassTiming;
  hostel_stay_duration?: number;
  expected_checkout_date?: string | null;

  // Section 4: Food preference
  food_preference: FoodPreference;
  food_allergy?: string;
  special_diet?: string;

  // Section 5: Guardian information
  father_name?: string;
  father_phone?: string;
  father_occupation?: string;
  mother_name?: string;
  mother_phone?: string;
  mother_occupation?: string;
  spouse_name?: string;
  spouse_phone?: string;
  spouse_occupation?: string;
  local_guardian_name?: string;
  local_guardian_phone?: string;
  local_guardian_address?: string;
  local_guardian_occupation?: string;
  local_guardian_relation?: string;
  guardian_citizenship?: string;
  guardian_email?: string;

  // Section 6: Hostel allocation
  preferred_room_type: RoomType;
  preferred_floor?: string;
  preferred_room?: string | null;
  preferred_bed?: string | null;
  preferred_bed_code?: string;
  requested_bed?: string | null;
  requested_bed_code?: string;
  approved_bed?: string | null;
  approved_bed_code?: string;
  assigned_by?: number | null;
  assigned_date?: string | null;

  student?: string | null;
  student_name?: string;

  // Section 7: Admission decision
  status: AdmissionStatus;
  rejection_reason?: string;
  notes?: string;
  decision_note?: string;
  decided_by?: number | null;
  decided_at?: string | null;

  // Section 8: Official use only
  booking_date?: string | null;
  monthly_fee?: string | number;
  security_deposit?: string | number;
  admission_fee?: string | number;
  discount?: string | number;
  scholarship?: string | number;
  receipt_number?: string;
  payment_status: PaymentStatus;
  remarks?: string;

  documents: AdmissionDocument[];
  created_at?: string;
  updated_at?: string;
}

export interface AdmissionDecisionPayload {
  bed?: string | null;
  join_date?: string;
  decision_note?: string;
  monthly_fee?: number;
  security_deposit?: number;
  admission_fee?: number;
  discount?: number;
  scholarship?: number;
  receipt_number?: string;
  payment_status?: PaymentStatus;
}

export interface AdmissionAnalytics {
  cards: {
    today: number;
    pending: number;
    approved: number;
    rejected: number;
    monthly: number;
    occupancy: number;
    revenue: number;
  };
  recent: AdmissionRequest[];
  charts: {
    food: Record<string, number>;
    education: Record<string, number>;
    district: Record<string, number>;
    status: Record<string, number>;
  };
}

export const ADMISSION_STATUS_LABELS: Record<AdmissionStatus, string> = {
  PENDING: "Pending",
  UNDER_REVIEW: "Under Review",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  WAITLISTED: "Waitlisted",
};

export const SOURCE_OPTIONS: { value: AdmissionSource; label: string }[] = [
  { value: "INTERNAL", label: "Internal" },
  { value: "PUBLIC", label: "Public" },
  { value: "WALK_IN", label: "Walk In" },
  { value: "WEBSITE", label: "Website" },
  { value: "REFERRAL", label: "Referral" },
];

export const GENDER_OPTIONS: { value: Gender; label: string }[] = [
  { value: "MALE", label: "Male" },
  { value: "FEMALE", label: "Female" },
  { value: "OTHER", label: "Other" },
];

export const LEVEL_OPTIONS: { value: EducationLevel; label: string }[] = [
  { value: "SEE", label: "SEE" },
  { value: "PLUS2", label: "+2" },
  { value: "BACHELOR", label: "Bachelor" },
  { value: "MASTER", label: "Master" },
  { value: "OTHER", label: "Other" },
];

export const TIMING_OPTIONS: { value: ClassTiming; label: string }[] = [
  { value: "MORNING", label: "Morning" },
  { value: "DAY", label: "Day" },
  { value: "EVENING", label: "Evening" },
];

export const FOOD_OPTIONS: { value: FoodPreference; label: string }[] = [
  { value: "VEGETARIAN", label: "Vegetarian" },
  { value: "EGGITARIAN", label: "Only Egg" },
  { value: "NON_VEGETARIAN", label: "Non Vegetarian" },
];

export const BLOOD_OPTIONS: BloodGroup[] = [
  "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "UNKNOWN",
];

export const MARITAL_OPTIONS: { value: MaritalStatus; label: string }[] = [
  { value: "SINGLE", label: "Single" },
  { value: "MARRIED", label: "Married" },
  { value: "OTHER", label: "Other" },
];

export const ROOM_TYPE_OPTIONS: { value: RoomType; label: string }[] = [
  { value: "SINGLE", label: "Single" },
  { value: "DOUBLE", label: "Double" },
  { value: "TRIPLE", label: "Triple" },
  { value: "FOUR_SHARING", label: "Four Sharing" },
];

export const PAYMENT_STATUS_OPTIONS: { value: PaymentStatus; label: string }[] = [
  { value: "PENDING", label: "Pending" },
  { value: "PARTIAL", label: "Partial" },
  { value: "PAID", label: "Paid" },
];

export const DOC_TYPE_OPTIONS: { value: AdmissionDocType; label: string }[] = [
  { value: "passport_photo", label: "Passport Photo" },
  { value: "citizenship_front", label: "Citizenship Front" },
  { value: "citizenship_back", label: "Citizenship Back" },
  { value: "birth_certificate", label: "Birth Certificate" },
  { value: "guardian_citizenship", label: "Guardian Citizenship" },
  { value: "academic_certificate", label: "Previous Academic Certificate" },
  { value: "migration_certificate", label: "Migration Certificate" },
  { value: "character_certificate", label: "Character Certificate" },
  { value: "medical_report", label: "Medical Report" },
  { value: "other_documents", label: "Other Documents" },
];
