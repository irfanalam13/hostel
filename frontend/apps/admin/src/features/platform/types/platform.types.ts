/**
 * Types for the Super-Admin platform (subscription/plan) surface. Mirrors the
 * backend `/api/platform/` serializers (apps.subscriptions.platform_serializers).
 */

export type PlanVisibility = "public" | "private" | "hidden";

export type Plan = {
  id: string;
  name: string;
  slug: string;
  description: string;
  notes: string;
  version: number;
  price_monthly: string;
  price_yearly: string;
  price_lifetime: string;
  discounted_price: string;
  currency: string;
  period: string;
  billing_interval: string;
  trial_days: number;
  grace_period_days: number;
  tax_percent: string;
  max_students: number;
  max_rooms: number;
  badge: string;
  theme_color: string;
  visibility: PlanVisibility;
  is_recommended: boolean;
  is_active: boolean;
  is_archived: boolean;
  is_featured: boolean;
  is_public: boolean;
  sort_order: number;
  features: string[];
  cta_label: string;
  cta_href: string;
  discount_active: boolean;
  discount_percent: string;
  discount_label: string;
  discount_until: string | null;
  feature_count: number;
  created_at: string;
  updated_at: string;
};

export type PlanFeatureRow = {
  feature: string;
  key: string;
  name: string;
  category_key: string;
  category_name: string;
  release_stage: string;
  is_enterprise_only: boolean;
  is_beta: boolean;
  enabled: boolean;
  requires: string[];
};

export type PlanLimitRow = {
  limit: string;
  key: string;
  name: string;
  unit: string;
  allow_unlimited: boolean;
  value: number | null;
  is_unlimited: boolean;
  default_value: number;
};

export type FeatureCategory = {
  id: string;
  key: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  sort_order: number;
  is_active: boolean;
  feature_count: number;
};

export type Feature = {
  id: string;
  key: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  category_key: string;
  category_name: string;
  icon: string;
  sort_order: number;
  default_enabled: boolean;
  release_stage: string;
  is_beta: boolean;
  is_enterprise_only: boolean;
  is_active: boolean;
  requires: string[];
};

export type LimitDefinition = {
  id: string;
  key: string;
  name: string;
  description: string;
  unit: string;
  category: string | null;
  category_key: string | null;
  default_value: number;
  allow_unlimited: boolean;
  sort_order: number;
  is_active: boolean;
};

export type FeatureOverride = {
  id: string;
  hostel: string;
  hostel_name: string;
  feature: string;
  feature_key: string;
  feature_name: string;
  is_enabled: boolean;
  reason: string;
  expires_at: string | null;
  is_live: boolean;
  created_at: string;
};

export type LimitOverride = {
  id: string;
  hostel: string;
  hostel_name: string;
  limit: string;
  limit_key: string;
  limit_name: string;
  value: number;
  is_unlimited: boolean;
  reason: string;
  expires_at: string | null;
  is_live: boolean;
  created_at: string;
};

export type ComparisonPlan = {
  id: string;
  name: string;
  slug: string;
  price_monthly: string;
  billing_interval: string;
  is_recommended: boolean;
  is_featured: boolean;
  badge: string;
};

export type Comparison = {
  plans: ComparisonPlan[];
  features: {
    key: string;
    name: string;
    category_key: string;
    category_name: string;
    values: Record<string, boolean>;
  }[];
  limits: {
    key: string;
    name: string;
    unit: string;
    values: Record<string, number | null>;
  }[];
};

export type DependencyViolation = {
  feature: string;
  feature_name: string;
  requires: string;
  requires_name: string;
};

export type HostelSubscription = {
  id: string;
  name: string;
  code: string;
  status: string;
  plan: string | null;
  plan_name: string | null;
  mrr: string;
  trial_ends_at: string | null;
  subscription_active_until: string | null;
};

/** Each hostel's OWN business numbers (students, occupancy, revenue, dues) —
 * distinct from HostelSubscription's platform-billing MRR. Super-admin only. */
export type HostelOverviewRow = {
  id: string;
  name: string;
  code: string;
  status: string;
  owner_name: string;
  plan_name: string | null;
  active_students: number;
  beds_total: number;
  beds_occupied: number;
  month_revenue: string;
  month_due: string;
  due_count: number;
};

/** Overview tab of the hostel drill-down: plan, revenue, usage & limits. */
export type HostelDetail = {
  id: string;
  name: string;
  code: string;
  status: string;
  owner_name: string;
  owner_email: string;
  phone: string;
  address: string;
  timezone: string;
  currency: string;
  created_at: string;
  trial_ends_at: string | null;
  plan: {
    id: string;
    name: string;
    slug: string;
    price_monthly: string;
    billing_interval: string;
  } | null;
  plan_name: string | null;
  subscription_active_until: string | null;
  mrr: string;
  revenue_summary: {
    month_revenue: string;
    month_due: string;
    due_count: number;
  };
  usage: {
    active_students: number;
    beds_total: number;
    beds_occupied: number;
    staff_count: number;
  };
  plan_limits: PlanLimitRow[];
};

/** Students tab row: roster + current room/bed + this-month due status. */
export type HostelStudentRow = {
  id: string;
  full_name: string;
  phone: string;
  status: string;
  join_date: string;
  gender: string;
  room_no: string | null;
  bed_no: string | null;
  current_month_status: string | null;
  current_month_due: string;
  total_outstanding: string;
};

export type HostelStudentDue = {
  month: string;
  amount: string;
  discount: string;
  fine: string;
  net_due: string;
  status: string;
  notes: string;
};

/** Staff tab row: read-only staff directory. */
export type HostelStaffRow = {
  id: string;
  employee_id: string;
  full_name: string;
  email: string;
  username: string;
  phone: string;
  account_role: string;
  department_name: string | null;
  designation_title: string | null;
  role_name: string | null;
  employment_type: string;
  status: string;
  joining_date: string;
};

/** Rooms tab row: room/bed occupancy breakdown. */
export type HostelRoomRow = {
  id: string;
  room_no: string;
  block_name: string | null;
  floor: string;
  room_type: string;
  capacity: number;
  rent: string;
  status: string;
  gender_type: string;
  beds_total: number;
  beds_occupied: number;
  beds: { id: string; bed_no: string; status: string }[];
};

export type SubscriptionEvent = {
  id: string;
  hostel: string;
  from_plan: string | null;
  from_plan_name: string | null;
  to_plan: string | null;
  to_plan_name: string | null;
  kind: string;
  status_after: string;
  mrr_amount: string;
  reason: string;
  actor_name: string | null;
  created_at: string;
};

export type FeatureDependency = {
  id: string;
  feature: string;
  feature_key: string;
  requires: string;
  requires_key: string;
};

export type AccountMembership = {
  hostel_id: string;
  hostel_name: string;
  hostel_code: string;
  hostel_status: string;
  plan_id: string | null;
  plan_name: string | null;
  subscription_active_until: string | null;
};

export type PlatformAccount = {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_superuser: boolean;
  last_login: string | null;
  date_joined: string;
  memberships: AccountMembership[];
};

export type PlatformAccountsPage = {
  count: number;
  accounts: PlatformAccount[];
};

export type AuditEvent = {
  id: string;
  sequence: number;
  created_at: string;
  action: string;
  result: string;
  status_code: number | null;
  duration_ms: number | null;
  actor: string | null;
  actor_label: string | null;
  hostel_id: string | null;
  branch_id: string | null;
  entity_type: string;
  entity_id: string;
  message: string;
  reason: string;
  changes: { old?: unknown; new?: unknown } | null;
  meta: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string;
  request_id: string | null;
  prev_hash: string;
  content_hash: string;
};

export type Analytics = {
  currency: string;
  mrr: string;
  arr: string;
  hostels: {
    total: number;
    active: number;
    trial: number;
    expired: number;
    suspended: number;
    no_plan: number;
  };
  plans: { total: number; active: number; public: number };
  plan_distribution: { plan: string; name: string; hostels: number; mrr: string }[];
  feature_adoption: { key: string; name: string; plans_enabled: number; plan_percent: number }[];
  most_used_features: { key: string; name: string; plans_enabled: number; plan_percent: number }[];
  unused_features: { key: string; name: string }[];
};
