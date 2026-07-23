export type StudentStatus = "active" | "vacated";

export type Student = {
  id: string;
  fullName: string;
  phone?: string;
  guardianName?: string;
  guardianPhone?: string;
  address?: string;

  roomId?: string; // reference Room.id
  bedId?: string;  // reference Bed.id

  monthlyFee: number;
  joinedAt: string; // ISO date
  status: StudentStatus;
};

export type Room = {
  id: string;
  label: string; // e.g. "101"
  floor?: string; // e.g. "1st"
};

export type Bed = {
  id: string;
  roomId: string;
  label: string; // e.g. "B1"
};

export type ExpenseCategory =
  | "Food"
  | "Electricity"
  | "Water"
  | "Internet"
  | "Repair"
  | "Salary"
  | "Other";

export type Expense = {
  id: string;
  date: string; // ISO date
  category: ExpenseCategory;
  amount: number;
  note?: string;
};

export type Payment = {
  id: string;
  date: string; // ISO date
  studentId: string;
  amount: number;
  note?: string; // partial/advance/etc
};

export type AuditAction =
  | "STUDENT_CREATED"
  | "STUDENT_UPDATED"
  | "STUDENT_VACATED"
  | "ROOM_CREATED"
  | "ROOM_UPDATED"
  | "BED_CREATED"
  | "BED_UPDATED"
  | "BED_ASSIGNED"
  | "BED_UNASSIGNED"
  | "PAYMENT_ADDED"
  | "EXPENSE_ADDED"
  | "EXPENSE_UPDATED"
  | "EXPENSE_DELETED"
  | "BACKUP_EXPORTED"
  | "BACKUP_IMPORTED"
  | "SETTINGS_UPDATED";

export type AuditLog = {
  id: string;
  at: string; // ISO datetime
  action: AuditAction;
  message: string;
};

export type Settings = {
  hostelName: string;
  totalBeds: number; // quick stat; can be derived later too
};

export type HostelState = {
  settings: Settings;

  rooms: Room[];
  beds: Bed[];

  students: Student[];
  expenses: Expense[];
  payments: Payment[];

  audit: AuditLog[];
};