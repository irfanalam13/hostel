"""Staff lifecycle services — account creation, employee-ID allocation, default
role seeding, and status transitions.

Account creation mirrors the workspace team-invite flow
(``apps.tenants.manage_views.TeamView``): a login account
(``accounts.User`` + ``accounts.UserHostel``) is created with a one-time
temporary password, alongside the :class:`StaffProfile` HR record. Unlike that
flow, staff creation enforces the ``max_staff`` plan quota.
"""
import secrets

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import Role, StaffProfile

# Base (portal-level) account roles a staff account may hold. These gate portal
# access and coarse defaults; fine-grained access comes from the assigned
# custom Role. Kept in sync with accounts.ROLE_CHOICES staff roles.
ACCOUNT_ROLES = {
    "ADMIN", "MANAGER", "RECEPTIONIST", "ACCOUNTANT", "WARDEN", "STAFF", "READ_ONLY",
}

# System roles seeded once per workspace. Each is a preset over the
# apps.common.rbac catalog; owners can tune the grants or add their own roles.
DEFAULT_ROLES = [
    ("Manager", "Full operational access across the workspace", [
        "residents.*", "billing.*", "payments.*", "rooms.*", "beds.*",
        "attendance.*", "admissions.*", "complaints.*", "notices.*", "reports.*",
        "exports.*", "operations.*", "notifications.*", "analytics.view",
        "staff.view", "staff.create", "staff.edit", "staff.invite", "finance.*",
        "accounting.*",
    ]),
    ("Receptionist", "Front-desk: admissions, residents and enquiries", [
        "residents.view", "residents.create", "residents.edit", "admissions.*",
        "rooms.view", "beds.view", "complaints.view", "complaints.create",
        "notices.view",
    ]),
    ("Accountant", "Finance & accounting: billing, ledgers and reports", [
        "billing.*", "payments.*", "reports.*", "exports.*", "finance.*",
        "accounting.*", "residents.view", "rooms.view", "notices.view",
        "analytics.view",
    ]),
    ("Warden", "Resident welfare, rooms and operations", [
        "residents.*", "rooms.*", "beds.*", "attendance.*", "complaints.*",
        "notices.*", "operations.*", "admissions.view", "reports.view",
    ]),
    ("Supervisor", "Oversees day-to-day operations and staff activity", [
        "residents.view", "rooms.view", "beds.view", "attendance.*",
        "operations.*", "complaints.*", "notices.view", "staff.view",
    ]),
    ("HR", "Manages staff records, roles and departments", [
        "staff.*", "reports.view",
    ]),
    ("Security Guard", "Gate, visitors and incident reporting", [
        "operations.view", "complaints.view", "complaints.create", "notices.view",
    ]),
    ("Maintenance", "Facilities upkeep and maintenance tasks", [
        "operations.view", "complaints.view", "complaints.create", "notices.view",
    ]),
    ("Cook", "Kitchen and mess operations", ["notices.view"]),
    ("Cleaner", "Housekeeping and cleanliness", ["notices.view"]),
]


def ensure_default_roles(hostel):
    """Seed the workspace's system roles once (idempotent)."""
    if Role.objects.filter(hostel=hostel, is_system=True).exists():
        return
    from django.utils.text import slugify

    Role.objects.bulk_create(
        [
            Role(
                hostel=hostel,
                name=name,
                slug=slugify(name)[:90] or "role",
                description=desc,
                permissions=perms,
                is_system=True,
                is_active=True,
            )
            for (name, desc, perms) in DEFAULT_ROLES
        ]
    )


def generate_employee_id(hostel) -> str:
    """Next ``EMP-####`` id for the workspace. The unique constraint is the real
    guard; this just picks a sensible free number."""
    n = StaffProfile.objects.filter(hostel=hostel).count() + 1
    while StaffProfile.objects.filter(hostel=hostel, employee_id=f"EMP-{n:04d}").exists():
        n += 1
    return f"EMP-{n:04d}"


def _temp_password() -> str:
    return secrets.token_urlsafe(9)


@transaction.atomic
def create_staff(*, hostel, actor, validated: dict):
    """Create a staff login account + HR profile in ``hostel``.

    ``validated`` is the StaffProfile serializer's validated data plus the
    account fields ``username``/``email``/``account_role``. Returns
    ``(profile, temp_password)``.
    """
    from apps.accounts.models import User, UserHostel

    username = str(validated.pop("username", "") or "").strip()
    email = str(validated.pop("email", "") or "").strip()
    account_role = str(validated.pop("account_role", "") or "STAFF").strip().upper()

    if account_role not in ACCOUNT_ROLES:
        raise ValidationError(
            {"account_role": f"Must be one of: {', '.join(sorted(ACCOUNT_ROLES))}."}
        )

    # Derive a username when the caller didn't supply one.
    if not username:
        base = (email.split("@")[0] if email else "") or "staff"
        base = "".join(ch for ch in base if ch.isalnum() or ch in "._-") or "staff"
        username = base
        suffix = 1
        while User.objects.filter(username__iexact=username).exists():
            suffix += 1
            username = f"{base}{suffix}"
    elif User.objects.filter(username__iexact=username).exists():
        raise ValidationError({"username": "This username is already taken."})

    # Email uniqueness is scoped to THIS workspace (the same address may be
    # reused across tenants; login is by username).
    if email:
        clash = (
            UserHostel.objects.filter(hostel=hostel, user__email__iexact=email)
            .exists()
        )
        if clash:
            raise ValidationError({"email": "A member with this email already exists in this workspace."})

    temp_password = _temp_password()
    # Provisioned with a temporary password — force a change on first login.
    user = User(username=username, email=email, role=account_role, must_change_password=True)
    if validated.get("first_name"):
        user.first_name = validated["first_name"][:150]
    if validated.get("last_name"):
        user.last_name = validated["last_name"][:150]
    user.set_password(temp_password)
    user.save()
    UserHostel.objects.create(user=user, hostel=hostel, is_active=True)

    profile = StaffProfile(
        hostel=hostel,
        user=user,
        employee_id=validated.pop("employee_id", "") or generate_employee_id(hostel),
        must_change_password=True,
        **validated,
    )
    profile.save()
    return profile, temp_password


def send_invite_email(hostel, *, username, email, temp_password, role_label="Staff"):
    """Best-effort tenant-branded staff invite email (never raises)."""
    if not email:
        return
    try:
        from apps.common.emails import send_account_welcome, welcome_context_from_branding
        from apps.tenants.branding import email_branding

        brand = email_branding(hostel)
        context = welcome_context_from_branding(brand)
        context.update({
            "recipient_name": username,
            "workspace_name": hostel.name,
            "hostel_code": hostel.code,
            "login_identity": email or username,
            "role_label": role_label,
            "credential_note": (
                f"Your temporary password is: {temp_password}\n"
                "You'll be asked to set a new password the first time you sign in."
            ),
            "first_login_note": (
                f"Sign in with your email ({email}) or username ({username}) and the "
                "temporary password above."
            ),
        })
        send_account_welcome(
            to=email,
            subject=f"You've been added to {brand['sender_name']}",
            from_email=brand["from_email"],
            context=context,
            fail_silently=True,
        )
    except Exception:
        pass


# Lifecycle status -> whether the workspace membership stays active. Suspend /
# disable / lock all revoke access (the account survives); active restores it.
_STATUS_ACTIVE = {
    StaffProfile.Status.ACTIVE: True,
    StaffProfile.Status.INVITED: True,
    StaffProfile.Status.SUSPENDED: False,
    StaffProfile.Status.DISABLED: False,
    StaffProfile.Status.LOCKED: False,
}


@transaction.atomic
def set_status(profile: StaffProfile, status: str):
    """Move a staff member to a lifecycle status and sync account access."""
    from apps.accounts.models import UserHostel

    profile.status = status
    profile.save(update_fields=["status", "updated_at"])
    active = _STATUS_ACTIVE.get(status, True)
    UserHostel.objects.filter(hostel=profile.hostel, user=profile.user).update(is_active=active)
    return profile


@transaction.atomic
def reset_password(profile: StaffProfile, *, force_change: bool = True) -> str:
    """Set a fresh temporary password on the staff account. Returns it once."""
    temp = _temp_password()
    profile.user.set_password(temp)
    # Mirror the force-change flag onto the User account — the login gate reads
    # User.must_change_password (works for every role), not the staff profile.
    profile.user.must_change_password = bool(force_change)
    profile.user.save(update_fields=["password", "must_change_password"])
    if force_change and not profile.must_change_password:
        profile.must_change_password = True
        profile.save(update_fields=["must_change_password", "updated_at"])
    elif not force_change and profile.must_change_password:
        profile.must_change_password = False
        profile.save(update_fields=["must_change_password", "updated_at"])
    return temp
