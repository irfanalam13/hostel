"""Namespaced workspace settings (Prompt 04).

All owner-configurable workspace configuration lives under
``Hostel.settings["workspace"][<namespace>]`` — one JSON document per
concern, each with a schema of defaults declared here. Reads overlay the
stored values on the defaults (new keys appear without data migrations);
writes are validated key-by-key against the schema (unknown keys rejected,
scalar types enforced, sizes capped).

Namespaces:
  profile        — public-facing identity (display fields, contacts, socials)
  business       — legal/registration information
  regional       — timezone/locale/format preferences
  notifications  — per-module notification toggles (email now; sms/push/
                   whatsapp are future-ready flags)
  security       — workspace security policy (stored policy; enforcement of
                   individual knobs lands with their features)
  preferences    — operational toggles (public website, portals, inquiry …)
  branding       — platform-level branding (login pages, dashboards, emails);
                   the *public website's* branding stays in apps.website
"""
import copy

from django.core.exceptions import ValidationError

_MAX_STRING = 500
_MAX_LIST = 50

WORKSPACE_SETTING_NAMESPACES: dict[str, dict] = {
    "profile": {
        "legal_name": "",
        "registration_number": "",
        "hostel_type": "",           # boys | girls | co-ed | students | workers
        "established_year": 0,
        "description": "",
        "motto": "",
        "contact_email": "",
        "contact_phone": "",
        "emergency_contact": "",
        "website": "",
        "social_links": {"facebook": "", "instagram": "", "linkedin": "",
                         "youtube": "", "tiktok": "", "x": "", "whatsapp": ""},
    },
    "business": {
        "business_name": "",
        "owner_name": "",
        "pan_vat_number": "",
        "registration_number": "",
        "address": "",
        "country": "Nepal",
        "province": "",
        "district": "",
        "city": "",
        "postal_code": "",
        # Future: multiple addresses append here.
        "additional_addresses": [],
    },
    "regional": {
        "timezone": "Asia/Kathmandu",
        "currency": "NPR",
        "date_format": "YYYY-MM-DD",
        "time_format": "24h",        # 24h | 12h
        "number_format": "1,234.56",
        "language": "en",
        "first_day_of_week": "sunday",
    },
    "notifications": {
        # Channels (email works today; the rest are future-ready flags).
        "email_enabled": True,
        "sms_enabled": False,
        "push_enabled": False,
        "whatsapp_enabled": False,
        # Per-module toggles.
        "modules": {
            "admission": True, "fees": True, "attendance": True,
            "notices": True, "complaints": True, "maintenance": True,
            "visitors": True, "subscription": True, "security": True,
        },
    },
    "security": {
        "password_min_length": 8,
        "password_expiry_days": 0,        # 0 = never
        "session_timeout_minutes": 0,     # 0 = platform default
        "idle_timeout_minutes": 0,
        "max_login_attempts": 5,
        "lockout_minutes": 15,
        "login_alerts": False,
        "mfa_required": False,            # MFA prep (Prompt 02)
    },
    "preferences": {
        "enable_public_website": True,
        "maintenance_mode": False,
        "allow_student_registration": False,
        "allow_parent_portal": True,
        "enable_online_inquiry": True,
        "enable_blog": False,
        "enable_gallery": True,
        "enable_events": True,
        "enable_public_notices": True,
    },
    "branding": {
        "logo": "",
        "dark_logo": "",
        "square_logo": "",
        "favicon": "",
        "cover_image": "",
        "login_background": "",
        "dashboard_banner": "",
        "workspace_icon": "",
    },
    # White-label (Prompt 05): present the platform as the hostel's own
    # system. Applied to the public site, login pages, dashboards, emails and
    # PDF exports (via apps.tenants.branding helpers).
    "white_label": {
        "enabled": False,
        "platform_name": "",          # replaces the SaaS name in UI copy
        "browser_title": "",          # <title> override on tenant surfaces
        "footer_text": "",
        "email_sender_name": "",      # From: display name on tenant emails
        "loading_screen_text": "",
        "hide_platform_branding": False,  # drop "powered by" everywhere
    },
}


def namespace_defaults(namespace: str) -> dict:
    if namespace not in WORKSPACE_SETTING_NAMESPACES:
        raise ValidationError({"namespace": f"Unknown settings namespace '{namespace}'."})
    return copy.deepcopy(WORKSPACE_SETTING_NAMESPACES[namespace])


def get_workspace_settings(hostel, namespace: str) -> dict:
    """Effective settings: defaults overlaid with the stored values."""
    defaults = namespace_defaults(namespace)
    stored = ((hostel.settings or {}).get("workspace", {}) or {}).get(namespace, {}) or {}
    merged = {**defaults, **{k: v for k, v in stored.items() if k in defaults}}
    # One level of nested-dict merging (social_links, modules, …).
    for key, default_value in defaults.items():
        if isinstance(default_value, dict):
            stored_value = stored.get(key) or {}
            merged[key] = {**default_value,
                           **{k: v for k, v in stored_value.items() if k in default_value}}
    return merged


def _validate_value(key: str, value, default) -> object:
    """Type-check a scalar/list/dict value against its default's shape."""
    if isinstance(default, bool):
        if not isinstance(value, bool):
            raise ValidationError({key: "Must be true or false."})
        return value
    if isinstance(default, int) and not isinstance(default, bool):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 10_000_000:
            raise ValidationError({key: "Must be a non-negative number."})
        return value
    if isinstance(default, str):
        if not isinstance(value, str):
            raise ValidationError({key: "Must be text."})
        if len(value) > _MAX_STRING:
            raise ValidationError({key: f"Must be at most {_MAX_STRING} characters."})
        return value.strip()
    if isinstance(default, list):
        if not isinstance(value, list) or len(value) > _MAX_LIST:
            raise ValidationError({key: f"Must be a list of at most {_MAX_LIST} items."})
        return value
    if isinstance(default, dict):
        if not isinstance(value, dict):
            raise ValidationError({key: "Must be an object."})
        cleaned = {}
        for sub_key, sub_default in default.items():
            if sub_key in value:
                cleaned[sub_key] = _validate_value(f"{key}.{sub_key}", value[sub_key], sub_default)
        unknown = set(value) - set(default)
        if unknown:
            raise ValidationError({key: f"Unknown keys: {', '.join(sorted(unknown))}"})
        return cleaned


def update_workspace_settings(hostel, namespace: str, data: dict, actor=None) -> dict:
    """Validate + persist a partial update to one namespace. Audited."""
    defaults = namespace_defaults(namespace)
    if not isinstance(data, dict):
        raise ValidationError({"detail": "Expected an object of settings."})
    unknown = set(data) - set(defaults)
    if unknown:
        raise ValidationError({"detail": f"Unknown settings: {', '.join(sorted(unknown))}"})

    current_stored = ((hostel.settings or {}).get("workspace", {}) or {}).get(namespace, {}) or {}
    updated = dict(current_stored)
    for key, value in data.items():
        cleaned = _validate_value(key, value, defaults[key])
        if isinstance(defaults[key], dict):
            # Merge nested dicts so partial sub-updates don't wipe siblings.
            updated[key] = {**(current_stored.get(key) or {}), **cleaned}
        else:
            updated[key] = cleaned

    settings_blob = dict(hostel.settings or {})
    workspace_blob = dict(settings_blob.get("workspace", {}) or {})
    workspace_blob[namespace] = updated
    settings_blob["workspace"] = workspace_blob
    hostel.settings = settings_blob
    hostel.save(update_fields=["settings", "updated_at"])  # signal invalidates caches

    try:
        from apps.auditlog.models import AuditEvent

        AuditEvent.objects.create(
            hostel_id=hostel.pk,
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            action=AuditEvent.Action.UPDATE,
            entity_type="workspace_settings",
            entity_id=str(hostel.pk),
            message=f"Workspace {namespace} settings updated",
            meta={"namespace": namespace, "fields": sorted(data.keys())},
        )
    except Exception:
        pass
    return get_workspace_settings(hostel, namespace)


def reset_workspace_settings(hostel, namespace: str, actor=None) -> dict:
    """Danger-zone reset: drop the stored namespace back to defaults."""
    namespace_defaults(namespace)  # validates the name
    settings_blob = dict(hostel.settings or {})
    workspace_blob = dict(settings_blob.get("workspace", {}) or {})
    workspace_blob.pop(namespace, None)
    settings_blob["workspace"] = workspace_blob
    hostel.settings = settings_blob
    hostel.save(update_fields=["settings", "updated_at"])
    try:
        from apps.auditlog.models import AuditEvent

        AuditEvent.objects.create(
            hostel_id=hostel.pk,
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            action=AuditEvent.Action.UPDATE,
            entity_type="workspace_settings",
            entity_id=str(hostel.pk),
            message=f"Workspace {namespace} settings reset to defaults",
            meta={"namespace": namespace},
        )
    except Exception:
        pass
    return get_workspace_settings(hostel, namespace)
