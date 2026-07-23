export type MonthlyDue = {
  id: string;
  resident: string;
  year: number;
  month: number;
  amount: string;
  paid_amount: string;
  remaining: string;
  created_at: string;
};

export type BillingPayment = {
  id: string;
  resident: string;
  due?: string | null;
  amount: string;
  method: string;
  note?: string;
  received_at: string;
  created_at: string;
};

export type BillingSummary = {
  month: number;
  year: number;
  total_due: string | number;
  total_paid: string | number;
  pending: string | number;
  active_residents: number;
};

export type Invoice = MonthlyDue;
export type LedgerEntry = BillingPayment;
export type VacateRequest = {
  id: string;
  resident: string;
  requested_date: string;
  approved_date?: string | null;
  status: "pending" | "approved" | "rejected";
  remarks?: string;
  created_at?: string;
};
