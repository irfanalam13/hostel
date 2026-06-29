"use client";

import { useCallback, useEffect, useState } from "react";
import {
  listInbox,
  listSent,
  markAllRead,
  markRead,
  sendNotification,
} from "@/features/notifications/api";
import type {
  AudienceType,
  InboxNotification,
  NotificationCategory,
  NotificationPriority,
  SentNotification,
} from "@/features/notifications/types";
import {
  AUDIENCE_OPTIONS,
  CATEGORY_OPTIONS,
  PRIORITY_OPTIONS,
} from "@/features/notifications/types";
import { useAuth } from "@/shared/auth/AuthProvider";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { EmptyState } from "@/shared/ui/EmptyState";
import { Input } from "@/shared/ui/Input";
import { Select } from "@/shared/ui/Select";
import { Spinner } from "@/shared/ui/Spinner";
import { Table } from "@/shared/ui/Table";
import { Textarea } from "@/shared/ui/Textarea";
import { Topbar } from "@/shared/ui/Topbar";
import { useToast } from "@/shared/ui/toast/ToastProvider";

const STAFF_ROLES = ["ADMIN", "OWNER", "MANAGER", "ACCOUNTANT", "WARDEN", "STAFF"];

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function NotificationsPage() {
  const toast = useToast();
  const { role } = useAuth();
  const isStaff = !!role && STAFF_ROLES.includes(role);

  const [tab, setTab] = useState<"inbox" | "send" | "sent">("inbox");
  const [inbox, setInbox] = useState<InboxNotification[]>([]);
  const [sent, setSent] = useState<SentNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [onlyUnread, setOnlyUnread] = useState(false);

  const refreshInbox = useCallback(async () => {
    setLoading(true);
    try {
      setInbox(await listInbox(onlyUnread ? { is_read: false } : undefined));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load notifications.");
    } finally {
      setLoading(false);
    }
  }, [onlyUnread, toast]);

  const refreshSent = useCallback(async () => {
    setLoading(true);
    try {
      setSent(await listSent());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load history.");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (tab === "inbox") refreshInbox();
    else if (tab === "sent") refreshSent();
  }, [tab, refreshInbox, refreshSent]);

  async function onRead(n: InboxNotification) {
    if (n.is_read) return;
    try {
      await markRead(n.recipient_id);
      setInbox((prev) => prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)));
    } catch {
      /* ignore */
    }
  }

  async function onReadAll() {
    try {
      const n = await markAllRead();
      toast.success(`Marked ${n} as read.`);
      refreshInbox();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed.");
    }
  }

  const tabs: ("inbox" | "send" | "sent")[] = isStaff ? ["inbox", "send", "sent"] : ["inbox"];

  return (
    <div>
      <Topbar title="Notifications" />
      <div className="px-4 py-4 sm:px-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex gap-1 rounded-xl bg-[var(--background-secondary)] p-1 text-sm">
            {tabs.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`rounded-lg px-4 py-1.5 font-medium capitalize transition ${
                  tab === t ? "bg-[var(--accent)] text-white" : "text-[var(--foreground-secondary)]"
                }`}
              >
                {t === "send" ? "Send" : t}
              </button>
            ))}
          </div>
          {tab === "inbox" && (
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1.5 text-sm text-[var(--foreground-secondary)]">
                <input type="checkbox" checked={onlyUnread} onChange={(e) => setOnlyUnread(e.target.checked)} />
                Unread only
              </label>
              <Button variant="secondary" size="sm" onClick={onReadAll}>
                Mark all read
              </Button>
            </div>
          )}
        </div>

        {loading && tab !== "send" ? (
          <div className="grid place-items-center py-16">
            <Spinner />
          </div>
        ) : tab === "inbox" ? (
          <Inbox inbox={inbox} onRead={onRead} />
        ) : tab === "send" ? (
          <SendForm onSent={() => toast.success("Notification queued / sent.")} />
        ) : (
          <SentHistory sent={sent} />
        )}
      </div>
    </div>
  );
}

function Inbox({ inbox, onRead }: { inbox: InboxNotification[]; onRead: (n: InboxNotification) => void }) {
  if (!inbox.length) {
    return <EmptyState title="No notifications" description="You're all caught up." icon="🔔" />;
  }
  return (
    <div className="space-y-2">
      {inbox.map((n) => (
        <div
          key={n.id}
          onClick={() => onRead(n)}
          className={`cursor-pointer rounded-2xl border p-4 transition ${
            n.is_read
              ? "border-[var(--border)] bg-[var(--card)]"
              : "border-[var(--accent)]/30 bg-[var(--accent-soft)]"
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                {!n.is_read && <span className="h-2 w-2 rounded-full bg-[var(--accent)]" />}
                <span className="font-medium text-[var(--foreground)]">{n.title}</span>
                {n.priority !== "NORMAL" && (
                  <span className="rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-semibold text-red-600">
                    {n.priority}
                  </span>
                )}
              </div>
              {n.body && <p className="mt-1 text-sm text-[var(--foreground-secondary)]">{n.body}</p>}
            </div>
            <span className="shrink-0 text-xs text-[var(--muted)]">{timeAgo(n.created_at)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function SendForm({ onSent }: { onSent: () => void }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    title: "",
    body: "",
    category: "GENERAL" as NotificationCategory,
    priority: "NORMAL" as NotificationPriority,
    audience: "ALL" as AudienceType,
    target_roles: "",
    user_ids: "",
    scheduled_at: "",
  });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) return toast.warning("Title is required.");
    setSaving(true);
    try {
      await sendNotification({
        title: form.title,
        body: form.body,
        category: form.category,
        priority: form.priority,
        audience: form.audience,
        target_roles:
          form.audience === "ROLE"
            ? form.target_roles.split(",").map((r) => r.trim().toUpperCase()).filter(Boolean)
            : [],
        user_ids:
          form.audience === "USER"
            ? form.user_ids.split(",").map((u) => Number(u.trim())).filter((n) => !Number.isNaN(n))
            : [],
        scheduled_at: form.scheduled_at ? new Date(form.scheduled_at).toISOString() : null,
      });
      onSent();
      setForm((f) => ({ ...f, title: "", body: "", target_roles: "", user_ids: "", scheduled_at: "" }));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Send failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <form onSubmit={submit} className="grid gap-3 md:grid-cols-2">
        <div className="md:col-span-2">
          <Input
            label="Title"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
          />
        </div>
        <div className="md:col-span-2">
          <Textarea label="Body" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
        </div>
        <Select
          label="Category"
          options={CATEGORY_OPTIONS}
          value={form.category}
          onChange={(e) => setForm({ ...form, category: e.target.value as NotificationCategory })}
        />
        <Select
          label="Priority"
          options={PRIORITY_OPTIONS}
          value={form.priority}
          onChange={(e) => setForm({ ...form, priority: e.target.value as NotificationPriority })}
        />
        <Select
          label="Audience"
          options={AUDIENCE_OPTIONS}
          value={form.audience}
          onChange={(e) => setForm({ ...form, audience: e.target.value as AudienceType })}
        />
        <Input
          label="Schedule for (optional)"
          type="datetime-local"
          value={form.scheduled_at}
          onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })}
        />
        {form.audience === "ROLE" && (
          <div className="md:col-span-2">
            <Input
              label="Target roles (comma separated, e.g. WARDEN,STAFF)"
              value={form.target_roles}
              onChange={(e) => setForm({ ...form, target_roles: e.target.value })}
            />
          </div>
        )}
        {form.audience === "USER" && (
          <div className="md:col-span-2">
            <Input
              label="User IDs (comma separated)"
              value={form.user_ids}
              onChange={(e) => setForm({ ...form, user_ids: e.target.value })}
            />
          </div>
        )}
        <div className="md:col-span-2 flex justify-end">
          <Button type="submit" loading={saving}>
            {form.scheduled_at ? "Schedule" : "Send now"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function SentHistory({ sent }: { sent: SentNotification[] }) {
  if (!sent.length) {
    return <EmptyState title="Nothing sent yet" description="Notifications you send appear here." icon="📤" />;
  }
  return (
    <Table>
      <thead>
        <tr className="border-b text-left">
          <th className="p-3">Title</th>
          <th className="p-3">Audience</th>
          <th className="p-3">Status</th>
          <th className="p-3">Recipients</th>
          <th className="p-3">Delivered</th>
          <th className="p-3">Read</th>
          <th className="p-3">By</th>
        </tr>
      </thead>
      <tbody>
        {sent.map((n) => (
          <tr key={n.id} className="border-b">
            <td className="p-3">
              <div className="font-medium">{n.title}</div>
              <div className="text-xs text-[var(--muted)]">{n.category}</div>
            </td>
            <td className="p-3 text-sm">
              {n.audience}
              {n.target_roles?.length ? ` (${n.target_roles.join(", ")})` : ""}
            </td>
            <td className="p-3 text-sm">{n.status}</td>
            <td className="p-3 text-sm">{n.recipients_count}</td>
            <td className="p-3 text-sm">
              {n.delivered_count}
              {n.failed_count ? <span className="text-red-500"> / {n.failed_count} failed</span> : ""}
            </td>
            <td className="p-3 text-sm">{n.read_count}</td>
            <td className="p-3 text-sm">{n.created_by_name}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
