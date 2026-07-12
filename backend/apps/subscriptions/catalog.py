"""The default feature / category / limit catalog.

This is the *seed* data for the database-driven subscription system. It is
deliberately re-runnable and non-destructive: seeding uses ``get_or_create`` by
``key`` so re-running never clobbers Super-Admin edits — it only adds anything
new. Called from both a data migration (fresh deploys) and the
``seed_subscription_catalog`` management command (manual re-seed).

Nothing here is authoritative at runtime beyond being the initial rows; once
seeded, the Super Admin owns every value from the panel.
"""
from apps.subscriptions.models import (
    Feature,
    FeatureCategory,
    FeatureDependency,
    LimitDefinition,
    ReleaseStage,
)

# --------------------------------------------------------------------------- #
# Categories: (key, name, icon, color, description)
# --------------------------------------------------------------------------- #
CATEGORIES = [
    ("general", "General", "layout-grid", "#64748b", "Core, cross-cutting capabilities"),
    ("student", "Student", "graduation-cap", "#2563eb", "Student lifecycle & records"),
    ("staff", "Staff", "users", "#7c3aed", "Staff, roles & payroll"),
    ("accommodation", "Accommodation", "bed", "#0891b2", "Rooms, beds & bookings"),
    ("finance", "Finance", "wallet", "#16a34a", "Billing, accounting & payments"),
    ("communication", "Communication", "message-square", "#db2777", "SMS, email, WhatsApp & push"),
    ("operations", "Operations", "settings-2", "#ea580c", "Day-to-day hostel operations"),
    ("ai", "AI", "sparkles", "#9333ea", "AI insights & assistants"),
    ("analytics", "Analytics", "bar-chart-3", "#0ea5e9", "Dashboards & reporting"),
    ("integrations", "Integrations", "plug", "#0d9488", "APIs, webhooks & external systems"),
    ("security", "Security", "shield-check", "#dc2626", "Audit, access & compliance"),
    ("branding", "Branding", "palette", "#c026d3", "White-label & custom domains"),
    ("developer", "Developer", "code", "#475569", "Developer platform"),
    ("enterprise", "Enterprise", "building-2", "#1d4ed8", "Multi-branch & enterprise scale"),
    ("support", "Support", "life-buoy", "#f59e0b", "Support tiers"),
    ("settings", "Settings", "sliders", "#6b7280", "Configuration & preferences"),
]

# --------------------------------------------------------------------------- #
# Features: (key, name, category_key, default_enabled, enterprise_only, stage)
# --------------------------------------------------------------------------- #
_STABLE = ReleaseStage.STABLE
_BETA = ReleaseStage.BETA

FEATURES = [
    # General
    ("notice_board", "Notice Board", "general", True, False, _STABLE),
    ("events", "Events", "general", True, False, _STABLE),
    ("task_management", "Task Management", "general", False, False, _STABLE),
    ("document_management", "Document Management", "general", False, False, _STABLE),
    ("global_search", "Global Search", "general", True, False, _STABLE),
    ("advanced_search", "Advanced Search", "general", False, False, _STABLE),
    ("dark_mode", "Dark Mode", "general", True, False, _STABLE),
    ("activity_timeline", "Activity Timeline", "general", False, False, _STABLE),
    ("import", "Import", "general", False, False, _STABLE),
    ("export", "Export", "general", True, False, _STABLE),
    ("backup", "Backup", "general", False, False, _STABLE),
    ("restore", "Restore", "general", False, False, _STABLE),
    # Student
    ("student_management", "Student Management", "student", True, False, _STABLE),
    ("admissions", "Admissions", "student", True, False, _STABLE),
    ("attendance", "Attendance", "student", True, False, _STABLE),
    ("qr_checkin", "QR Check-in", "student", False, False, _STABLE),
    ("biometric_integration", "Biometric Integration", "student", False, True, _STABLE),
    # Staff
    ("staff_management", "Staff Management", "staff", True, False, _STABLE),
    ("role_management", "Role Management", "staff", True, False, _STABLE),
    ("payroll", "Payroll", "staff", False, False, _STABLE),
    ("leave_management", "Leave Management", "staff", False, False, _STABLE),
    # Accommodation
    ("room_management", "Room Management", "accommodation", True, False, _STABLE),
    ("bed_management", "Bed Management", "accommodation", True, False, _STABLE),
    ("booking", "Booking", "accommodation", True, False, _STABLE),
    ("visitors", "Visitors", "accommodation", False, False, _STABLE),
    ("maintenance", "Maintenance", "accommodation", False, False, _STABLE),
    # Finance
    ("finance", "Finance", "finance", True, False, _STABLE),
    ("accounting", "Accounting", "finance", False, False, _STABLE),
    ("expenses", "Expenses", "finance", False, False, _STABLE),
    ("income", "Income", "finance", False, False, _STABLE),
    ("payment_gateway", "Payment Gateway", "finance", False, False, _STABLE),
    ("multi_currency", "Multi Currency", "finance", False, True, _STABLE),
    # Communication
    ("sms", "SMS", "communication", False, False, _STABLE),
    ("email", "Email", "communication", True, False, _STABLE),
    ("whatsapp", "WhatsApp", "communication", False, False, _BETA),
    ("push_notification", "Push Notification", "communication", True, False, _STABLE),
    # Operations
    ("inventory", "Inventory", "operations", False, False, _STABLE),
    ("laundry", "Laundry", "operations", False, False, _STABLE),
    ("mess_management", "Mess Management", "operations", False, False, _STABLE),
    # AI
    ("ai_dashboard", "AI Dashboard", "ai", False, False, _BETA),
    ("ai_reports", "AI Reports", "ai", False, False, _BETA),
    ("ai_chat", "AI Chat", "ai", False, False, _BETA),
    ("ai_assistant", "AI Assistant", "ai", False, True, _BETA),
    # Analytics
    ("analytics_dashboard", "Analytics Dashboard", "analytics", True, False, _STABLE),
    ("hostel_reports", "Hostel Reports", "analytics", True, False, _STABLE),
    # Integrations
    ("api_access", "API Access", "integrations", False, False, _STABLE),
    ("webhook", "Webhook", "integrations", False, False, _STABLE),
    ("mobile_app", "Mobile App", "integrations", True, False, _STABLE),
    # Security
    ("audit_logs", "Audit Logs", "security", False, False, _STABLE),
    # Branding
    ("custom_branding", "Custom Branding", "branding", False, False, _STABLE),
    ("white_label", "White Label", "branding", False, True, _STABLE),
    ("custom_domain", "Custom Domain", "branding", False, False, _STABLE),
    # Developer
    ("developer_api", "Developer API", "developer", False, False, _STABLE),
    ("developer_webhooks", "Developer Webhooks", "developer", False, False, _STABLE),
    ("developer_tokens", "Developer Tokens", "developer", False, False, _STABLE),
    # Enterprise
    ("multi_branch", "Multi Branch", "enterprise", False, True, _STABLE),
    # Support
    ("priority_support", "Priority Support", "support", False, True, _STABLE),
]

# --------------------------------------------------------------------------- #
# Feature dependencies: (feature_key, requires_key)  — Module 8
# --------------------------------------------------------------------------- #
DEPENDENCIES = [
    ("ai_reports", "analytics_dashboard"),
    ("ai_chat", "ai_dashboard"),
    ("ai_assistant", "ai_dashboard"),
    ("api_access", "developer_api"),
    ("white_label", "custom_domain"),
    ("webhook", "developer_api"),
]

# --------------------------------------------------------------------------- #
# Limit definitions: (key, name, unit, category_key, default_value, allow_unlimited)
# --------------------------------------------------------------------------- #
LIMITS = [
    ("max_students", "Maximum Students", "students", "student", 200, True),
    ("max_staff", "Maximum Staff", "staff", "staff", 10, True),
    ("max_admins", "Maximum Admins", "admins", "staff", 2, True),
    ("max_receptionists", "Maximum Receptionists", "receptionists", "staff", 2, True),
    ("max_wardens", "Maximum Wardens", "wardens", "staff", 5, True),
    ("max_parents", "Maximum Parents", "parents", "student", 0, True),
    ("max_guardians", "Maximum Guardians", "guardians", "student", 0, True),
    ("max_rooms", "Maximum Rooms", "rooms", "accommodation", 50, True),
    ("max_beds", "Maximum Beds", "beds", "accommodation", 200, True),
    ("max_bookings", "Maximum Bookings", "bookings", "accommodation", 0, True),
    ("max_buildings", "Maximum Hostel Buildings", "buildings", "accommodation", 1, True),
    ("max_branches", "Maximum Branches", "branches", "enterprise", 1, True),
    ("max_departments", "Maximum Departments", "departments", "staff", 5, True),
    ("max_storage_mb", "Maximum Storage", "MB", "general", 1024, True),
    ("max_monthly_emails", "Maximum Monthly Emails", "emails/mo", "communication", 1000, True),
    ("max_sms", "Maximum SMS", "sms/mo", "communication", 0, True),
    ("max_whatsapp", "Maximum WhatsApp Messages", "msgs/mo", "communication", 0, True),
    ("max_push", "Maximum Push Notifications", "push/mo", "communication", 5000, True),
    ("max_api_requests", "Maximum API Requests", "req/mo", "integrations", 0, True),
    ("max_ai_requests", "Maximum AI Requests", "req/mo", "ai", 0, True),
    ("max_reports", "Maximum Reports", "reports", "analytics", 50, True),
    ("max_daily_backups", "Maximum Daily Backups", "backups/day", "general", 1, True),
    ("max_integrations", "Maximum Integrations", "integrations", "integrations", 1, True),
    ("max_custom_fields", "Maximum Custom Fields", "fields", "general", 10, True),
    ("max_visitors", "Maximum Visitors", "visitors", "accommodation", 0, True),
    ("max_notices", "Maximum Notices", "notices", "communication", 0, True),
    ("max_events", "Maximum Events", "events", "general", 0, True),
    ("max_payroll_records", "Maximum Payroll Records", "records", "staff", 0, True),
    ("max_inventory_items", "Maximum Inventory Items", "items", "operations", 0, True),
]


def seed_catalog(*, apps=None, stdout=None):
    """Create any missing categories, features, dependencies and limits.

    Idempotent and non-destructive. Returns a dict of created counts.

    ``apps`` — when called from a data migration, pass the migration's
    historical app registry so DB writes go through the frozen model state.
    When ``None`` (management command), the live models are used.
    """
    if apps is not None:
        FeatureCategory_ = apps.get_model("subscriptions", "FeatureCategory")
        Feature_ = apps.get_model("subscriptions", "Feature")
        FeatureDependency_ = apps.get_model("subscriptions", "FeatureDependency")
        LimitDefinition_ = apps.get_model("subscriptions", "LimitDefinition")
    else:
        FeatureCategory_ = FeatureCategory
        Feature_ = Feature
        FeatureDependency_ = FeatureDependency
        LimitDefinition_ = LimitDefinition

    def _log(msg):
        if stdout is not None:
            stdout.write(msg)

    created = {"categories": 0, "features": 0, "dependencies": 0, "limits": 0}

    cat_by_key = {}
    for order, (key, name, icon, color, desc) in enumerate(CATEGORIES):
        obj, was_created = FeatureCategory_.objects.get_or_create(
            key=key,
            defaults={
                "name": name,
                "icon": icon,
                "color": color,
                "description": desc,
                "sort_order": order,
            },
        )
        cat_by_key[key] = obj
        created["categories"] += int(was_created)

    feat_by_key = {}
    for order, (key, name, cat_key, default_on, ent_only, stage) in enumerate(FEATURES):
        obj, was_created = Feature_.objects.get_or_create(
            key=key,
            defaults={
                "name": name,
                "display_name": name,
                "category": cat_by_key[cat_key],
                "default_enabled": default_on,
                "is_enterprise_only": ent_only,
                "is_beta": str(stage) == ReleaseStage.BETA,
                "release_stage": str(stage),
                "sort_order": order,
            },
        )
        feat_by_key[key] = obj
        created["features"] += int(was_created)

    for feat_key, req_key in DEPENDENCIES:
        feat = feat_by_key.get(feat_key)
        req = feat_by_key.get(req_key)
        if not feat or not req:
            continue
        _, was_created = FeatureDependency_.objects.get_or_create(feature=feat, requires=req)
        created["dependencies"] += int(was_created)

    for order, (key, name, unit, cat_key, default_value, allow_unlimited) in enumerate(LIMITS):
        _, was_created = LimitDefinition_.objects.get_or_create(
            key=key,
            defaults={
                "name": name,
                "unit": unit,
                "category": cat_by_key.get(cat_key),
                "default_value": default_value,
                "allow_unlimited": allow_unlimited,
                "sort_order": order,
            },
        )
        created["limits"] += int(was_created)

    _log(
        "Seeded catalog: "
        + ", ".join(f"{v} {k}" for k, v in created.items())
        + " (new rows; existing rows left untouched)."
    )
    return created
