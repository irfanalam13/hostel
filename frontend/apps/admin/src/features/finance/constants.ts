import type {
  AwardType,
  DiscountReason,
  DiscountType,
  ExpenseRecurrence,
  IncomeSource,
  LateFineType,
  PaymentMethod,
  Recurrence,
  RefundType,
  ScholarshipType,
} from "./types/finance.types";

type Opt<T extends string> = { value: T; label: string };

export const PAYMENT_METHODS: Opt<PaymentMethod>[] = [
  { value: "cash", label: "Cash" },
  { value: "bank_transfer", label: "Bank Transfer" },
  { value: "mobile_banking", label: "Mobile Banking" },
  { value: "qr", label: "QR" },
  { value: "card", label: "Card" },
  { value: "online", label: "Online" },
  { value: "upi", label: "UPI" },
  { value: "wallet", label: "Wallet" },
  { value: "cheque", label: "Cheque" },
  { value: "other", label: "Other" },
];

export const FEE_RECURRENCES: Opt<Recurrence>[] = [
  { value: "one_time", label: "One-time" },
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "semester", label: "Semester" },
  { value: "annual", label: "Annual" },
];

export const LATE_FINE_TYPES: Opt<LateFineType>[] = [
  { value: "none", label: "None" },
  { value: "fixed", label: "Fixed" },
  { value: "percentage", label: "Percentage" },
];

export const EXPENSE_RECURRENCES: Opt<ExpenseRecurrence>[] = [
  { value: "none", label: "None" },
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "annual", label: "Annual" },
];

export const INCOME_SOURCES: Opt<IncomeSource>[] = [
  { value: "student_fees", label: "Student Fees" },
  { value: "room_booking", label: "Room Booking" },
  { value: "security_deposit", label: "Security Deposit" },
  { value: "cafeteria", label: "Cafeteria" },
  { value: "laundry", label: "Laundry" },
  { value: "transport", label: "Transport" },
  { value: "internet", label: "Internet" },
  { value: "extra_services", label: "Extra Services" },
  { value: "commission", label: "Commission" },
  { value: "interest", label: "Interest" },
  { value: "donation", label: "Donation" },
  { value: "other", label: "Other" },
];

export const REFUND_TYPES: Opt<RefundType>[] = [
  { value: "security_deposit", label: "Security Deposit" },
  { value: "admission_cancellation", label: "Admission Cancellation" },
  { value: "overpayment", label: "Overpayment" },
  { value: "scholarship_adjustment", label: "Scholarship Adjustment" },
  { value: "duplicate_payment", label: "Duplicate Payment" },
  { value: "withdrawal", label: "Withdrawal" },
  { value: "custom", label: "Custom" },
];

export const DISCOUNT_TYPES: Opt<DiscountType>[] = [
  { value: "percentage", label: "Percentage" },
  { value: "fixed", label: "Fixed" },
];

export const DISCOUNT_REASONS: Opt<DiscountReason>[] = [
  { value: "seasonal", label: "Seasonal" },
  { value: "promotional", label: "Promotional" },
  { value: "early_payment", label: "Early Payment" },
  { value: "sibling", label: "Sibling" },
  { value: "merit", label: "Merit" },
  { value: "staff", label: "Staff" },
  { value: "custom", label: "Custom" },
];

export const SCHOLARSHIP_TYPES: Opt<ScholarshipType>[] = [
  { value: "merit", label: "Merit" },
  { value: "need_based", label: "Need-based" },
  { value: "sports", label: "Sports" },
  { value: "government", label: "Government" },
  { value: "ngo", label: "NGO" },
  { value: "internal", label: "Internal" },
  { value: "custom", label: "Custom" },
];

export const AWARD_TYPES: Opt<AwardType>[] = [
  { value: "percentage", label: "Percentage" },
  { value: "fixed", label: "Fixed" },
];

export const methodLabel = (m: string) =>
  m.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
