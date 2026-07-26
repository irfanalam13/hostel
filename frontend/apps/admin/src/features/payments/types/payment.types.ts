export interface Receipt {
  id: string;
  payment: string;
  receipt_no: string;
}

export interface PaymentAllocation {
  id: string;
  payment: string;
  ledger: string;
  amount: string;
}

export interface Payment {
  id: string;
  student: string;
  amount: string;
  date: string;
  method: string;
  reference_no?: string;
  created_at?: string;
  allocations?: PaymentAllocation[];
  receipt?: Receipt | null;
}

export type PaymentCreateAllocationInput = {
  ledger_id: string;
  amount: string;
};

export interface PaymentCreateInput {
  student: string;
  amount: string;
  date: string;
  method: string;
  reference_no?: string;
  allocations: PaymentCreateAllocationInput[];
}

export interface StudentDuesSummary {
  student: string;
  total_due: string;
  total_paid: string;
  balance: string;
}
