export type Plan = {
  id: string;
  name: string;
  price_monthly?: string | number;
  max_rooms?: number;
  max_students?: number;
  [key: string]: any;
};

export type Hostel = {
  id: string;
  name: string;
  code: string;
  phone?: string;
  address?: string;

  plan_name?: string | null;
  subscription_active_until?: string | null; // ISO date
  is_active: boolean;
  settings?: HostelSettings;
  created_at: string; // ISO datetime
};

/** Free-form JSON on Hostel.settings; these keys are read by the backend. */
export type HostelSettings = {
  default_application_fee?: number;
  max_upload_size_mb?: number;
  [key: string]: unknown;
};

export type HostelCreateInput = {
  name: string;
  code?: string;
  phone?: string;
  address?: string;
  is_active?: boolean;
  settings?: HostelSettings;
};

export type Subscription = {
  id: string;
  hostel: string;         // FK id
  plan: string;           // FK id
  start_date: string;     // yyyy-mm-dd
  end_date?: string | null;       // yyyy-mm-dd
  is_active?: boolean;
  created_at?: string;
  [key: string]: any;
};

export type SubscriptionCreateInput = Omit<Subscription, "id" | "created_at">;
