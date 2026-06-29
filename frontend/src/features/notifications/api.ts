import { api } from "@/shared/api/apiClient";
import type {
  InboxNotification,
  SendNotificationPayload,
  SentNotification,
} from "./types";

type Paginated<T> = { results: T[] } | T[];

function asArray<T>(data: Paginated<T>): T[] {
  return Array.isArray(data) ? data : data.results ?? [];
}

export async function listInbox(params?: { is_read?: boolean; category?: string }) {
  const res = await api.get<Paginated<InboxNotification>>("/notifications/", {
    params: {
      is_read: params?.is_read === undefined ? undefined : String(params.is_read),
      category: params?.category,
    },
  });
  return asArray(res.data);
}

export async function getUnreadCount() {
  const res = await api.get<{ unread: number }>("/notifications/unread_count/");
  return res.data.unread;
}

export async function markRead(recipientId: string) {
  await api.post(`/notifications/${recipientId}/read/`);
}

export async function markAllRead() {
  const res = await api.post<{ marked_read: number }>("/notifications/read_all/");
  return res.data.marked_read;
}

export async function sendNotification(payload: SendNotificationPayload) {
  const res = await api.post<SentNotification>("/notifications/send/", payload);
  return res.data;
}

export async function listSent(params?: { category?: string }) {
  const res = await api.get<Paginated<SentNotification>>("/notifications/sent/", { params });
  return asArray(res.data);
}
