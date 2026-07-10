"""Enterprise RBAC: roles, portals, and the permission registry.

Three layers, all tenant-aware:

1. **Roles** — a user's ``role`` (accounts.User.role) inside a workspace.
   Platform staff are ``is_superuser`` (not a role choice) and bypass checks.
2. **Portals** — login surfaces (/admin, /login, /student, /parent). Each
   portal admits a fixed set of roles; portal login never escalates a role.
3. **Permissions** — ``module.action`` strings (e.g. ``residents.create``)
   granted per role. Defaults live here; individual workspaces can override
   per role via ``Hostel.settings["permissions"]["roles"]`` (configurable
   RBAC without code changes). Wildcards: ``*`` (everything) and
   ``module.*`` (every action in a module).

Lookups are cached per (workspace, role) in Redis and memoized per request —
the target is <10ms, and in practice a warm lookup is a dict hit.
"""
from django.conf import settings as django_settings
from django.core.cache import cache
from rest_framework.permissions import BasePermission

# --------------------------------------------------------------------------- #
# Roles
# --------------------------------------------------------------------------- #
# Kept in sync with accounts.ROLE_CHOICES (single source there for the model).
ROLE_OWNER = "OWNER"
ROLE_ADMIN = "ADMIN"           # hostel admin
ROLE_MANAGER = "MANAGER"
ROLE_RECEPTIONIST = "RECEPTIONIST"
ROLE_ACCOUNTANT = "ACCOUNTANT"
ROLE_WARDEN = "WARDEN"
ROLE_STAFF = "STAFF"
ROLE_STUDENT = "STUDENT"
ROLE_PARENT = "PARENT"
ROLE_RESIDENT = "RESIDENT"     # legacy pre-portal role (student-equivalent)
ROLE_READ_ONLY = "READ_ONLY"

STAFF_PORTAL_ROLES = {
    ROLE_MANAGER, ROLE_RECEPTIONIST, ROLE_ACCOUNTANT, ROLE_WARDEN, ROLE_STAFF,
    ROLE_READ_ONLY,
}
ADMIN_PORTAL_ROLES = {ROLE_OWNER, ROLE_ADMIN}
STUDENT_PORTAL_ROLES = {ROLE_STUDENT, ROLE_RESIDENT}
PARENT_PORTAL_ROLES = {ROLE_PARENT}

# Portal key -> roles allowed to authenticate through it. Admin roles may also
# use the staff portal (an owner signing in at /login is fine); the reverse —
# a staff/student role entering /admin — is never allowed.
PORTALS = {
    "admin": ADMIN_PORTAL_ROLES,
    "staff": STAFF_PORTAL_ROLES | ADMIN_PORTAL_ROLES,
    "student": STUDENT_PORTAL_ROLES,
    "parent": PARENT_PORTAL_ROLES,
}

# Role -> the dashboard a successful login should land on. New portals only
# add entries here; no routing architecture changes needed.
DEFAULT_ROUTE_BY_ROLE = {
    ROLE_OWNER: "/dashboard",
    ROLE_ADMIN: "/dashboard",
    ROLE_MANAGER: "/dashboard",
    ROLE_RECEPTIONIST: "/dashboard",
    ROLE_ACCOUNTANT: "/dashboard",
    ROLE_WARDEN: "/dashboard",
    ROLE_STAFF: "/dashboard",
    ROLE_READ_ONLY: "/dashboard",
    ROLE_STUDENT: "/student/dashboard",
    ROLE_RESIDENT: "/student/dashboard",
    ROLE_PARENT: "/parent/dashboard",
}


def portal_allows_role(portal: str, role: str) -> bool:
    """Whether a role may authenticate through the given portal.
    Unknown portal -> False (fail closed)."""
    return role in PORTALS.get(portal, set())


def default_route_for_role(role: str) -> str:
    return DEFAULT_ROUTE_BY_ROLE.get(role, "/dashboard")


# --------------------------------------------------------------------------- #
# Permission registry
# --------------------------------------------------------------------------- #
# Modules cover the app's feature areas; actions are CRUD + module-specific
# feature verbs. A permission string is "<module>.<action>".
MODULES = [
    "residents", "billing", "payments", "rooms", "beds", "attendance",
    "admissions", "complaints", "notices", "reports", "exports", "operations",
    "backups", "notifications", "analytics", "accounts", "workspace",
    "website",
]
CRUD = ["view", "create", "edit", "delete"]

# Extra feature permissions that don't fit plain CRUD.
FEATURE_PERMISSIONS = [
    "billing.collect", "billing.waive",
    "reports.export",
    "backups.restore",
    "workspace.manage",       # lifecycle, branding, settings
    "workspace.billing",      # subscription/plan management
    "accounts.invite",        # create staff users
    "notices.publish",
    "website.publish",
]


def all_permissions() -> set:
    perms = {f"{m}.{a}" for m in MODULES for a in CRUD}
    perms.update(FEATURE_PERMISSIONS)
    return perms


# Defaults per role. Workspaces override per role via
# Hostel.settings["permissions"]["roles"][ROLE] = ["module.action", "module.*"].
DEFAULT_ROLE_PERMISSIONS = {
    ROLE_OWNER: ["*"],
    ROLE_ADMIN: ["*"],
    ROLE_MANAGER: [
        "residents.*", "billing.*", "payments.*", "rooms.*", "beds.*",
        "attendance.*", "admissions.*", "complaints.*", "notices.*",
        "reports.*", "exports.*", "operations.*", "notifications.*",
        "analytics.view", "accounts.view", "accounts.invite", "website.*",
    ],
    ROLE_RECEPTIONIST: [
        "residents.view", "residents.create", "residents.edit",
        "admissions.*", "rooms.view", "beds.view", "attendance.*",
        "complaints.view", "complaints.create", "notices.view",
    ],
    ROLE_ACCOUNTANT: [
        "billing.*", "payments.*", "reports.*", "exports.*",
        "residents.view", "rooms.view", "notices.view", "analytics.view",
    ],
    ROLE_WARDEN: [
        "residents.*", "rooms.*", "beds.*", "attendance.*", "complaints.*",
        "notices.*", "operations.*", "admissions.view", "reports.view",
        "billing.view", "payments.view",
    ],
    ROLE_STAFF: [
        "residents.view", "rooms.view", "beds.view", "attendance.view",
        "attendance.create", "complaints.view", "complaints.create",
        "notices.view", "operations.view",
    ],
    ROLE_STUDENT: [
        "billing.view", "payments.view", "attendance.view",
        "complaints.view", "complaints.create", "notices.view",
    ],
    ROLE_RESIDENT: [  # legacy — same surface as STUDENT
        "billing.view", "payments.view", "attendance.view",
        "complaints.view", "complaints.create", "notices.view",
    ],
    ROLE_PARENT: [
        "billing.view", "payments.view", "attendance.view", "notices.view",
    ],
    ROLE_READ_ONLY: [f"{m}.view" for m in MODULES],
}

_PERMS_KEY = "perms:v1:{hostel_id}:{role}"


def _perms_ttl() -> int:
    return int(getattr(django_settings, "PERMISSIONS_CACHE_TTL", 300))


def _expand(grants) -> frozenset:
    """Expand a grant list (may contain wildcards) into concrete permissions."""
    result = set()
    catalog = all_permissions()
    for grant in grants or []:
        grant = str(grant).strip()
        if not grant:
            continue
        if grant == "*":
            return frozenset(catalog)
        if grant.endswith(".*"):
            module = grant[:-2]
            result.update(p for p in catalog if p.startswith(module + "."))
        elif grant in catalog:
            result.add(grant)
    return frozenset(result)


def invalidate_permissions_cache(hostel_id, role=None) -> None:
    """Drop cached permission sets for a workspace (all roles, or one)."""
    roles = [role] if role else list(DEFAULT_ROLE_PERMISSIONS)
    try:
        cache.delete_many([_PERMS_KEY.format(hostel_id=hostel_id, role=r) for r in roles])
    except Exception:
        pass  # TTL bounds staleness


def role_permissions(role: str, hostel=None) -> frozenset:
    """Effective permissions for a role in a workspace (defaults + workspace
    override), Redis-cached per (workspace, role)."""
    hostel_id = str(getattr(hostel, "pk", "")) or "-"
    key = _PERMS_KEY.format(hostel_id=hostel_id, role=role)
    try:
        hit = cache.get(key)
    except Exception:
        hit = None
    if hit is not None:
        return frozenset(hit)

    grants = DEFAULT_ROLE_PERMISSIONS.get(role, [])
    if hostel is not None:
        overrides = (
            (getattr(hostel, "settings", None) or {})
            .get("permissions", {})
            .get("roles", {})
        )
        if isinstance(overrides, dict) and role in overrides:
            grants = overrides[role]
    perms = _expand(grants)
    try:
        cache.set(key, list(perms), _perms_ttl())
    except Exception:
        pass
    return perms


def user_permissions(user, hostel, request=None) -> frozenset:
    """Effective permissions for a user in a workspace. Superusers get all.
    Memoized on the request so repeated checks in one request are free."""
    if not user or not getattr(user, "is_authenticated", False):
        return frozenset()
    if user.is_superuser:
        return frozenset(all_permissions())

    base = getattr(request, "_request", request) if request is not None else None
    memo_key = (user.pk, str(getattr(hostel, "pk", "-")))
    if base is not None:
        memo = getattr(base, "_perms_memo", None)
        if memo is not None and memo_key in memo:
            return memo[memo_key]

    perms = role_permissions(getattr(user, "role", ""), hostel)
    if base is not None:
        if getattr(base, "_perms_memo", None) is None:
            base._perms_memo = {}
        base._perms_memo[memo_key] = perms
    return perms


def user_has_permission(user, hostel, permission: str, request=None) -> bool:
    return permission in user_permissions(user, hostel, request=request)


# --------------------------------------------------------------------------- #
# DRF integration
# --------------------------------------------------------------------------- #
def RequirePermission(*permissions: str):
    """DRF permission-class factory: the caller must hold EVERY listed
    permission in the resolved workspace.

        permission_classes = [IsAuthenticated, RequirePermission("residents.create")]

    Viewsets can vary by action with ``permission_map``:

        class ResidentViewSet(...):
            permission_map = {"create": ["residents.create"], ...}
    """

    class _HasPermissions(BasePermission):
        message = "You do not have permission to perform this action."
        required = permissions

        def has_permission(self, request, view):
            hostel = getattr(request, "hostel", None)
            return all(
                user_has_permission(request.user, hostel, p, request=request)
                for p in self.required
            )

    _HasPermissions.__name__ = f"RequirePermission({', '.join(permissions)})"
    return _HasPermissions


class ActionPermissions(BasePermission):
    """Reads the view's ``permission_map`` ({action or HTTP method: [perms]})
    and enforces it against the resolved workspace. Actions/methods missing
    from the map are allowed through (compose with role classes as needed)."""

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        perm_map = getattr(view, "permission_map", None) or {}
        key = getattr(view, "action", None) or request.method.lower()
        needed = perm_map.get(key, [])
        hostel = getattr(request, "hostel", None)
        return all(
            user_has_permission(request.user, hostel, p, request=request) for p in needed
        )
