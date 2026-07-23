// Mirrors backend/apps/notifications/{models,serializers}.py

export type NotificationCategory =
  | "GENERAL"
  | "ADMISSION_APPROVED"
  | "FEE_DUE"
  | "RENT_OVERDUE"
  | "VISITOR_APPROVAL"
  | "ROOM_CHANGED"
  | "MAINTENANCE_COMPLETED"
  | "COMPLAINT_RESOLVED"
  | "EMERGENCY"
  | "STAFF_NOTICE"
  | "INVENTORY_ALERT";

export type NotificationPriority = "NORMAL" | "HIGH" | "URGENT";
export type AudienceType = "ALL" | "ROLE" | "USER";
export type NotificationStatus = "DRAFT" | "SCHEDULED" | "SENDING" | "SENT" | "FAILED" | "CANCELED";

/** A recipient's inbox entry (InboxNotificationSerializer). */
export interface InboxNotification {
  id: string; // notification id
  recipient_id: string; // NotificationRecipient id (used for read endpoint)
  category: NotificationCategory;
  priority: NotificationPriority;
  title: string;
  body: string;
  url: string;
  data: Record<string, unknown>;
  is_read: boolean;
  read_at: string | null;
  delivered: boolean;
  created_at: string;
}

/** Staff "sent" history with delivery stats (NotificationAdminSerializer). */
export interface SentNotification {
  id: string;
  category: NotificationCategory;
  priority: NotificationPriority;
  title: string;
  body: string;
  url: string;
  audience: AudienceType;
  target_roles: string[];
  status: NotificationStatus;
  scheduled_at: string | null;
  sent_at: string | null;
  recipients_count: number;
  delivered_count: number;
  failed_count: number;
  read_count: number;
  created_by: number | null;
  created_by_name: string;
  created_at: string;
}

export interface SendNotificationPayload {
  title: string;
  body?: string;
  category?: NotificationCategory;
  priority?: NotificationPriority;
  url?: string;
  audience?: AudienceType;
  target_roles?: string[];
  user_ids?: number[];
  scheduled_at?: string | null;
}

export const CATEGORY_OPTIONS: { value: NotificationCategory; label: string }[] = [
  { value: "GENERAL", label: "General" },
  { value: "ADMISSION_APPROVED", label: "Admission approved" },
  { value: "FEE_DUE", label: "Fee due reminder" },
  { value: "RENT_OVERDUE", label: "Rent overdue" },
  { value: "VISITOR_APPROVAL", label: "Visitor approval" },
  { value: "ROOM_CHANGED", label: "Room changed" },
  { value: "MAINTENANCE_COMPLETED", label: "Maintenance completed" },
  { value: "COMPLAINT_RESOLVED", label: "Complaint resolved" },
  { value: "EMERGENCY", label: "Emergency announcement" },
  { value: "STAFF_NOTICE", label: "Staff notice" },
  { value: "INVENTORY_ALERT", label: "Inventory alert" },
];

export const PRIORITY_OPTIONS: { value: NotificationPriority; label: string }[] = [
  { value: "NORMAL", label: "Normal" },
  { value: "HIGH", label: "High" },
  { value: "URGENT", label: "Urgent" },
];

export const AUDIENCE_OPTIONS: { value: AudienceType; label: string }[] = [
  { value: "ALL", label: "All hostel members" },
  { value: "ROLE", label: "Specific roles" },
  { value: "USER", label: "Specific users" },
];
