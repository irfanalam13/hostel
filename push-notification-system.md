# Push Notification System

A complete, tenant-aware Web Push notification system for the Hostel Management
System. The Django app `apps.notifications` is the backend half; it pairs with
the already-built frontend (`frontend/packages/pwa/src/push.ts` + the service
worker `push`/`notificationclick` handlers) — see `frontend/Documentation/PWA.md`.

---

## 1. Overview

| Capability | Where |
| --- | --- |
| Django push app | `backend/apps/notifications/` |
| VAPID key generation | `python manage.py vapid_keys` |
| `pywebpush` integration | `services.send_web_push()` |
| Subscription database | `PushSubscription` model |
| Subscribe API | `POST /api/push/subscribe/` |
| Unsubscribe API | `POST /api/push/unsubscribe/` |
| Notification API | `/api/notifications/` (inbox, send, history, read) |
| Admin panel | `admin.py` (4 models + "Dispatch now" action) |
| Scheduled notifications | `scheduled_at` + beat task `send_scheduled_notifications` |
| Celery integration | `tasks.py` + `CELERY_BEAT_SCHEDULE` |
| Firebase / Web Push compatibility | Standard VAPID Web Push (covers FCM/Apple/Mozilla) |
| Tenant-aware notifications | `Notification` is hostel-scoped; recipients from `UserHostel` |
| User targeting | `audience=USER` + `user_ids` |
| Role-based notifications | `audience=ROLE` + `target_roles` |
| Notification history | `NotificationRecipient` (inbox) + `/sent/` (staff) |
| Retry mechanism | `NotificationDelivery` + `retry_failed_deliveries` (backoff) |
| Delivery tracking | `NotificationDelivery` + denormalised counters |
| Read/Unread status | `NotificationRecipient.is_read` + `read`/`read_all`/`unread_count` |
| Security | Auth + hostel membership + staff-only send; private key server-side |

---

## 2. Data model (`models.py`)

```
PushSubscription      one Web Push endpoint per user/device (VAPID keys)
Notification          one logical notification (content + targeting + schedule
                      + status + denormalised delivery counters)  [hostel-scoped]
NotificationRecipient per-user fan-out row → the user's inbox + read state
NotificationDelivery  per-subscription push attempt → retries + delivery tracking
```

**Tenant isolation.** `Notification` is a `HostelScopedModel`. Recipients are
*always* resolved from active `UserHostel` memberships of that hostel
(`services.resolve_recipient_user_ids`), so a notification can never reach a user
outside its tenant — even with explicit `user_ids` (they're intersected with
members). The inbox API filters by `notification__hostel == request.hostel`.

**Enums.** `NotificationCategory` (the 10 hostel events + `GENERAL`),
`NotificationPriority` (`NORMAL/HIGH/URGENT`; HIGH+URGENT set
`requireInteraction`), `AudienceType` (`ALL/ROLE/USER`), `NotificationStatus`
(`DRAFT/SCHEDULED/SENDING/SENT/FAILED/CANCELED`), `DeliveryStatus`
(`PENDING/SENT/FAILED/EXPIRED`).

---

## 3. VAPID key generation

```bash
cd backend
python manage.py vapid_keys
```

Prints:

```
NEXT_PUBLIC_VAPID_PUBLIC_KEY=<b64url uncompressed P-256 point>   # frontend
VAPID_PRIVATE_KEY=<b64url DER PKCS8>                             # backend only
VAPID_SUBJECT=mailto:admin@yourdomain.com
```

Add all three to `.env` (see `.env.example`). The **public** key is also inlined
into the browser bundle as `NEXT_PUBLIC_VAPID_PUBLIC_KEY`; the **private** key
stays on the backend. Push delivery is a safe no-op until `VAPID_PRIVATE_KEY` and
`VAPID_SUBJECT` are set (`services.push_enabled()`), so the app runs fine without
keys configured.

Settings (`config/settings.py`):

```python
VAPID_PUBLIC_KEY = env("NEXT_PUBLIC_VAPID_PUBLIC_KEY", default="")
VAPID_PRIVATE_KEY = env("VAPID_PRIVATE_KEY", default="")
VAPID_SUBJECT = env("VAPID_SUBJECT", default="")
NOTIFICATIONS_MAX_RETRIES = env.int("NOTIFICATIONS_MAX_RETRIES", default=3)
```

---

## 4. `pywebpush` integration (`services.py`)

`send_web_push(subscription, payload_json)` wraps `pywebpush.webpush` with the
VAPID private key and never raises — it returns a `PushResult` classifying the
outcome:

- **ok** → mark delivered, reset `failure_count`.
- **expired** (404/410) → subscription is gone → deactivate it.
- **retryable** (429/5xx/timeout/network) → schedule a retry with backoff.
- **permanent** (400/401/403/413) → fail without retry.

`pywebpush` is imported lazily, so a missing dependency degrades gracefully
instead of breaking app startup.

### Firebase / Web Push compatibility
This uses the **standard Web Push protocol with VAPID**, which Chrome/Edge
(Google FCM endpoints), Firefox (Mozilla autopush) and Safari/iOS 16.4+ (Apple
Push) all speak — no vendor-specific code or FCM server key required. The same
JSON payload is rendered by the service worker for every browser.

---

## 5. APIs

### Subscribe / Unsubscribe (consumed by the frontend automatically)
```
POST /api/push/subscribe/     { subscription: <PushSubscription JSON>, user_agent }
POST /api/push/unsubscribe/   { endpoint }
```
Auth + hostel membership required. Subscribe upserts by `endpoint` (idempotent);
unsubscribe only removes the caller's own subscription.

### Notifications
```
GET  /api/notifications/                  inbox for the current user + hostel
        ?is_read=true|false  ?category=FEE_DUE
GET  /api/notifications/unread_count/      { "unread": N }
POST /api/notifications/{recipient_id}/read/
POST /api/notifications/read_all/
POST /api/notifications/send/              (staff) create + dispatch/schedule
GET  /api/notifications/sent/             (staff) history with delivery stats
```

**Send body:**
```json
{
  "title": "Water cut",
  "body": "No water 2–4pm today",
  "category": "STAFF_NOTICE",
  "priority": "HIGH",
  "url": "/notices",
  "audience": "ROLE",          // ALL | ROLE | USER
  "target_roles": ["WARDEN"],  // when audience=ROLE
  "user_ids": [12, 34],        // when audience=USER
  "scheduled_at": "2026-07-01T09:00:00Z"  // optional → schedules instead of sending now
}
```
Staff = superuser or role in `{ADMIN, OWNER, MANAGER, ACCOUNTANT, WARDEN, STAFF}`.

---

## 6. Domain event helpers (`events.py`)

Call these from anywhere to fire the right notification without wiring details:

```python
from apps.notifications import events

events.admission_approved(hostel, student_user, "Asha Gurung")
events.fee_due_reminder(hostel, user, amount=5000, due_date="2026-07-05")
events.rent_overdue(hostel, user, amount=5000, days_overdue=3)
events.visitor_approval(hostel, host_user, "Ram (visitor)")
events.room_changed(hostel, user, old_room="A-101", new_room="B-204")
events.maintenance_completed(hostel, user, "ceiling fan")
events.complaint_resolved(hostel, user, "WiFi not working")
events.emergency_announcement(hostel, "Evacuate via Exit B", created_by=admin)  # URGENT, all
events.staff_notice(hostel, "Shift change", "Night shift starts at 8pm")        # staff roles
events.inventory_alert(hostel, "rice", detail="Only 5kg left")                  # managers
```

Each returns the created `Notification` (or `None` for a user-targeted event with
no user). Dispatch is handed to Celery (or runs inline when eager), so these are
safe to call inside a request.

---

## 7. Celery integration (`tasks.py`)

| Task | Trigger | Purpose |
| --- | --- | --- |
| `dispatch_notification_task` | on send (async) | fan out one notification |
| `send_scheduled_notifications` | beat, every minute | dispatch due `SCHEDULED` notifications |
| `retry_failed_deliveries` | beat, every 5 min | re-attempt failed pushes (backoff `1,5,30` min) |
| `prune_expired_subscriptions` | beat, daily 04:30 | drop dead/stale subscriptions |

Registered in `CELERY_BEAT_SCHEDULE` (settings). In tests / when no broker is
present, dispatch runs **inline** so results are observable synchronously.

**Retry mechanism.** Each `NotificationDelivery` tracks `attempts`,
`last_error`, `last_attempt_at`, `next_retry_at`. Retryable failures get an
exponential-ish backoff; after `NOTIFICATIONS_MAX_RETRIES` they stop and count as
failed. `recompute_counts()` keeps the `Notification` counters
(`recipients/delivered/failed/read`) accurate.

---

## 8. Admin panel (`admin.py`)

- **PushSubscription** — by user/hostel/active, failure count, last used.
- **Notification** — status + all delivery counters, filter by category/priority/
  audience/hostel, inline recipient list, **"Dispatch selected now"** action.
- **NotificationDelivery** — per-attempt status, attempts, last error, next retry.

---

## 9. Security

- Subscribe/unsubscribe and the inbox require authentication **and** hostel
  membership (`HasHostelContext`); a spoofed `X-Hostel-Code` can't read another
  tenant's notifications.
- Sending is **staff-only**.
- The VAPID **private key never leaves the backend**; only the public key reaches
  the browser.
- Recipients are constrained to active hostel members → no cross-tenant leakage.
- Users can only delete their own subscriptions.

---

## 10. Example notifications (all supported)

| Event | Helper | Category | Priority | Audience |
| --- | --- | --- | --- | --- |
| Student admission approved | `admission_approved` | `ADMISSION_APPROVED` | NORMAL | the student |
| Fee due reminder | `fee_due_reminder` | `FEE_DUE` | NORMAL | the user |
| Rent overdue | `rent_overdue` | `RENT_OVERDUE` | HIGH | the user |
| Visitor approval | `visitor_approval` | `VISITOR_APPROVAL` | HIGH | the host |
| Room changed | `room_changed` | `ROOM_CHANGED` | NORMAL | the user |
| Maintenance completed | `maintenance_completed` | `MAINTENANCE_COMPLETED` | NORMAL | the user |
| Complaint resolved | `complaint_resolved` | `COMPLAINT_RESOLVED` | NORMAL | the user |
| Emergency announcement | `emergency_announcement` | `EMERGENCY` | URGENT | all members |
| Staff notice | `staff_notice` | `STAFF_NOTICE` | NORMAL | staff roles |
| Inventory alert | `inventory_alert` | `INVENTORY_ALERT` | HIGH | managers |

---

## 11. Setup checklist

```bash
# 1. Install dependency (already in requirements.txt)
pip install pywebpush

# 2. Generate VAPID keys and put them in .env
python manage.py vapid_keys

# 3. Apply migrations
python manage.py migrate notifications

# 4. Run Celery worker + beat (for async/scheduled/retry)
celery -A config worker -l info
celery -A config beat -l info
```

The frontend already calls `/api/push/subscribe/` from the Settings → "Push
notifications" toggle once `NEXT_PUBLIC_VAPID_PUBLIC_KEY` is set.

---

## 12. Tests

`apps/notifications/tests.py` (16 tests, all passing) covers: subscribe/idempotent/
unsubscribe/validation, staff send to ALL/ROLE/USER, non-staff forbidden, inbox +
read + read_all + unread_count, **tenant isolation**, scheduling, the event
helpers, and that dispatch never crashes when VAPID is unconfigured.

```bash
cd backend && pytest apps/notifications/tests.py
```

> Note: the wider repo currently has unrelated pre-existing test failures from
> in-progress, unmigrated model edits in `admissions`/`students` — these are
> independent of this notification system.
