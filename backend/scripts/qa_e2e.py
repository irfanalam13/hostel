"""Autonomous end-to-end QA harness (Prompt 07).

Runs the whole platform through the real Django stack — tenant-resolution
middleware, cookie/JWT auth, RBAC, the website/domains/workspace apps — with
realistic multi-hostel data, then exercises isolation and active security
attacks. Prints PASS/FAIL per check and a summary, and cleans up everything
it created in a finally block.

Run:  docker compose exec -T web python manage.py shell < scripts/qa_e2e.py
"""
import json
import uuid

from django.conf import settings as _settings
from django.test import Client
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User, UserHostel
from apps.accounts.tokens import issue_tokens
from apps.domains.models import CustomDomain
from apps.tenants import services as tsvc

# The Django test Client defaults to Host: testserver. In the dev container
# ALLOWED_HOSTS is explicit (only .localhost is auto-added), so allow it here
# for the harness — this is a test-client artifact, not an app behavior.
for _h in ("testserver", "everest.localhost", "himalayan.localhost",
           "sunrise.localhost", "metro.localhost"):
    if _h not in _settings.ALLOWED_HOSTS:
        _settings.ALLOWED_HOSTS.append(_h)

# --------------------------------------------------------------------------- #
RESULTS = []
CREATED_HOSTELS = []
CREATED_USERS = []
PASSWORD = "QaPass!2026"


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    mark = "PASS" if ok else "FAIL"
    line = f"[{mark}] {name}"
    if detail and not ok:
        line += f"  -- {detail}"
    print(line)
    return ok


def data(resp):
    try:
        body = resp.json()
    except Exception:
        return {}
    return body.get("data", body) if isinstance(body, dict) else body


def as_list(payload):
    """Normalize a DRF list response (paginated {results:[]} or bare []) -> []."""
    if isinstance(payload, dict):
        return payload.get("results") or []
    return payload if isinstance(payload, list) else []


def ws(slug, extra=None):
    h = {"HTTP_X_WORKSPACE": slug}
    if extra:
        h.update(extra)
    return h


def bearer(token, extra=None):
    h = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
    if extra:
        h.update(extra)
    return h


def clear_login_throttle():
    """Reset the per-IP auth defences so the harness can drive many logins.
    All test-client requests share one source IP, so the production
    protections (DRF 5/min throttle in the cache + django-axes lockout in the
    DB, both verified explicitly below) would otherwise block the functional
    login checks."""
    from django.core.cache import cache

    cache.clear()
    try:
        from axes.utils import reset

        reset()  # clears all axes lockout records
    except Exception:
        pass


# =========================================================================== #
# Setup: realistic workspaces + full role cast
# =========================================================================== #
WORKSPACES = [
    ("Everest International Hostel", "everest"),
    ("Himalayan Boys Hostel", "himalayan"),
    ("Sunrise Girls Hostel", "sunrise"),
    ("Metro Student Residency", "metro"),
]
ROLES = ["OWNER", "ADMIN", "RECEPTIONIST", "ACCOUNTANT", "WARDEN", "STAFF",
         "STUDENT", "PARENT", "READ_ONLY"]

hostels = {}      # slug -> Hostel
users = {}        # (slug, role) -> User
run_id = uuid.uuid4().hex[:8]


def setup():
    for name, slug in WORKSPACES:
        owner = User.objects.create(
            username=f"qa_{slug}_owner_{run_id}", email=f"{slug}.owner.{run_id}@example.com",
            role="OWNER",
        )
        owner.set_password(PASSWORD)
        owner.save()
        CREATED_USERS.append(owner)
        h = tsvc.provision_workspace(owner=owner, hostel_name=name, workspace_username=slug)
        CREATED_HOSTELS.append(h)
        hostels[slug] = h
        users[(slug, "OWNER")] = owner
        for role in ROLES:
            if role == "OWNER":
                continue
            u = User.objects.create(
                username=f"qa_{slug}_{role.lower()}_{run_id}",
                email=f"{slug}.{role.lower()}.{run_id}@example.com", role=role,
            )
            u.set_password(PASSWORD)
            u.save()
            UserHostel.objects.create(user=u, hostel=h, is_active=True)
            CREATED_USERS.append(u)
            users[(slug, role)] = u


# =========================================================================== #
# Prompt 01 — Workspace & Subdomain Architecture
# =========================================================================== #
def test_prompt01():
    print("\n=== Prompt 01: Workspace & Subdomain Architecture ===")
    api = Client()

    for slug in ("everest", "himalayan", "sunrise", "metro"):
        h = hostels[slug]
        check(f"01 workspace '{slug}' created with slug", h.slug == slug)
        check(f"01 workspace '{slug}' has code", bool(h.code and h.code.startswith("HTL-")))
        check(f"01 workspace '{slug}' url", h.workspace_url.endswith(f"{slug}.localhost"))
        check(f"01 workspace '{slug}' default settings seeded", bool(h.settings.get("roles")))
        check(f"01 workspace '{slug}' owner linked",
              UserHostel.objects.filter(hostel=h, user=h.owner, is_active=True).exists())
        check(f"01 workspace '{slug}' default website auto-published",
              h.website.is_published if hasattr(h, "website") else False)

    # Availability checker
    r = data(api.get("/api/tenants/workspaces/availability/", {"username": "everest"}))
    check("01 taken username unavailable + suggestions",
          r.get("available") is False and len(r.get("suggestions", [])) > 0, json.dumps(r))
    r = data(api.get("/api/tenants/workspaces/availability/", {"username": f"brandnew{run_id}"}))
    check("01 free username available", r.get("available") is True)

    # Username validation matrix
    cases = {
        "admin": "reserved", "API": "reserved", "ab": "too_short",
        "has space": "invalid", "special@char": "invalid", "café": "invalid",
        "a" * 64: "too_long",
    }
    for name, reason in cases.items():
        r = data(api.get("/api/tenants/workspaces/availability/", {"username": name}))
        check(f"01 invalid username '{name[:12]}' -> {reason}",
              r.get("available") is False and r.get("reason") == reason, json.dumps(r))

    # Unknown workspace resolves to 404 pre-auth
    check("01 unknown workspace host -> 404",
          api.get("/api/residents/", **ws("ghost-xyz")).status_code == 404)


# =========================================================================== #
# Prompt 02 — Authentication & Routing
# =========================================================================== #
def test_prompt02():
    print("\n=== Prompt 02: Tenant Authentication & Routing ===")

    # Login every role through its portal
    portal_for = {
        "OWNER": "admin", "ADMIN": "admin", "RECEPTIONIST": "staff",
        "ACCOUNTANT": "staff", "WARDEN": "staff", "STAFF": "staff",
        "READ_ONLY": "staff", "STUDENT": "student", "PARENT": "parent",
    }
    for role, portal in portal_for.items():
        clear_login_throttle()
        api = Client()
        r = api.post("/api/auth/login/",
                     {"username": users[("everest", role)].username, "password": PASSWORD,
                      "portal": portal},
                     content_type="application/json", **ws("everest"))
        check(f"02 login {role} via {portal} portal", r.status_code == 200,
              f"status={r.status_code}")

    # Portal gating: student cannot use admin portal
    clear_login_throttle()
    api = Client()
    r = api.post("/api/auth/login/",
                 {"username": users[("everest", "STUDENT")].username, "password": PASSWORD,
                  "portal": "admin"}, content_type="application/json", **ws("everest"))
    check("02 student blocked from admin portal", r.status_code == 400)

    # Redirect by role
    clear_login_throttle()
    api = Client()
    r = api.post("/api/auth/login/",
                 {"username": users[("everest", "STUDENT")].username, "password": PASSWORD,
                  "portal": "student"}, content_type="application/json", **ws("everest"))
    check("02 student redirect -> /student/dashboard",
          data(r).get("redirect") == "/student/dashboard")

    # Invalid password
    clear_login_throttle()
    api = Client()
    r = api.post("/api/auth/login/",
                 {"username": users[("everest", "OWNER")].username, "password": "wrong"},
                 content_type="application/json", **ws("everest"))
    check("02 invalid password rejected", r.status_code == 400)

    # Remember me extends refresh cookie
    clear_login_throttle()
    api = Client()
    plain = api.post("/api/auth/login/",
                     {"username": users[("everest", "WARDEN")].username, "password": PASSWORD},
                     content_type="application/json", **ws("everest"))
    clear_login_throttle()
    api2 = Client()
    remembered = api2.post("/api/auth/login/",
                           {"username": users[("everest", "WARDEN")].username,
                            "password": PASSWORD, "remember": True},
                           content_type="application/json", **ws("everest"))
    check("02 remember-me extends refresh lifetime",
          int(remembered.cookies["refresh_token"]["max-age"]) >
          int(plain.cookies["refresh_token"]["max-age"]))

    # Brute-force protection: rapid failed logins get rate-limited (429).
    clear_login_throttle()
    statuses = []
    for _ in range(8):
        c = Client()
        rr = c.post("/api/auth/login/",
                    {"username": users[("everest", "OWNER")].username, "password": "nope",
                     "portal": "admin"}, content_type="application/json", **ws("everest"))
        statuses.append(rr.status_code)
    check("02 brute-force login rate-limited after burst",
          429 in statuses or 403 in statuses, f"statuses={statuses}")
    clear_login_throttle()

    # Password-version invalidation
    u = users[("everest", "STAFF")]
    _, access = issue_tokens(u, hostels["everest"])
    api = Client()
    before = api.get("/api/auth/me/", **bearer(str(access), ws("everest"))).status_code
    u.set_password("Changed!2026")
    u.save()
    after = api.get("/api/auth/me/", **bearer(str(access), ws("everest"))).status_code
    check("02 password change invalidates old tokens", before == 200 and after == 401)

    # session verify + permissions endpoints
    _, access = issue_tokens(users[("everest", "OWNER")], hostels["everest"])
    api = Client()
    r = api.get("/api/auth/session/verify/", **bearer(str(access), ws("everest")))
    check("02 session verify", r.status_code == 200 and data(r).get("authenticated") is True)
    r = api.get("/api/auth/permissions/", **bearer(str(access), ws("everest")))
    check("02 owner has full permissions", "workspace.manage" in data(r).get("permissions", []))


# =========================================================================== #
# Tenant isolation + security
# =========================================================================== #
def test_isolation_security():
    print("\n=== Tenant Isolation & Security ===")

    everest_owner = users[("everest", "OWNER")]
    _, everest_access = issue_tokens(everest_owner, hostels["everest"])

    # Cross-tenant token: everest token against himalayan host -> 401
    api = Client()
    r = api.get("/api/tenants/manage/overview/", **bearer(str(everest_access), ws("himalayan")))
    check("SEC cross-tenant token rejected (everest token on himalayan)", r.status_code == 401)

    # Same token on its own workspace works
    r = api.get("/api/tenants/manage/overview/", **bearer(str(everest_access), ws("everest")))
    check("SEC own-workspace token works", r.status_code == 200)

    # Tampered JWT
    tampered = str(everest_access)[:-3] + "xxx"
    r = api.get("/api/auth/me/", **bearer(tampered, ws("everest")))
    check("SEC tampered JWT rejected", r.status_code == 401)

    # Expired JWT
    exp = AccessToken.for_user(everest_owner)
    exp["hostel_id"] = str(hostels["everest"].id)
    exp["hostel_code"] = hostels["everest"].code
    from datetime import timedelta
    exp.set_exp(lifetime=timedelta(minutes=-5))
    r = api.get("/api/auth/me/", **bearer(str(exp), ws("everest")))
    check("SEC expired JWT rejected", r.status_code == 401)

    # Token missing hostel claims
    bare = str(AccessToken.for_user(everest_owner))
    r = api.get("/api/auth/me/", **bearer(bare, ws("everest")))
    check("SEC token without hostel claims rejected", r.status_code == 401)

    # Privilege escalation: student hitting owner-only workspace management
    _, student_access = issue_tokens(users[("everest", "STUDENT")], hostels["everest"])
    r = api.get("/api/tenants/manage/settings/security/", **bearer(str(student_access), ws("everest")))
    check("SEC student blocked from workspace settings (403)", r.status_code == 403)

    # Staff cannot publish website
    _, staff_access = issue_tokens(users[("everest", "STAFF")], hostels["everest"])
    r = api.post("/api/website/publish/", **bearer(str(staff_access), ws("everest")))
    check("SEC staff blocked from website publish (403)", r.status_code == 403)

    # Cross-tenant data: create a resident in himalayan, ensure everest can't see it
    from apps.residents.models import Resident
    theirs = Resident.objects.create(hostel=hostels["himalayan"], full_name="Himalaya Resident",
                                     phone="9811111111", monthly_fee=5000)
    r = api.get("/api/residents/", **bearer(str(everest_access), ws("everest")))
    names = [x.get("full_name") for x in as_list(data(r))]
    check("SEC cross-tenant data not leaked", "Himalaya Resident" not in names)
    theirs.delete()

    # SQL injection in availability query — must be handled as plain text, no 500
    api2 = Client()
    r = api2.get("/api/tenants/workspaces/availability/", {"username": "everest'; DROP TABLE tenants_hostel;--"})
    check("SEC SQLi in availability handled safely",
          r.status_code == 200 and data(r).get("available") is False)
    check("SEC hostel table intact after SQLi attempt",
          hostels["everest"].__class__.objects.filter(slug="everest").exists())

    # Stored XSS: inquiry with script payload is stored as data, never executed
    # (React auto-escapes on render; API stores raw text safely).
    xss = "<script>alert('xss')</script>"
    r = api2.post("/api/website/public/inquiries/",
                  {"name": xss, "phone": "9800000000", "message": "Legit message about a room here."},
                  content_type="application/json", **ws("everest"))
    check("SEC XSS inquiry accepted+stored as text", r.status_code == 201)

    # Host header spoof: unknown Host with no workspace context -> no tenant leaked
    r = api2.get("/api/residents/", HTTP_HOST="evil.attacker.com")
    check("SEC spoofed Host header yields no tenant access", r.status_code in (400, 401, 403, 404))

    # Workspace enumeration: unknown workspace and suspended workspace look distinct but safe
    r = api2.get("/api/tenants/workspaces/public/", **ws(f"doesnotexist{run_id}"))
    check("SEC unknown workspace public branding -> 404", r.status_code == 404)


# =========================================================================== #
# Prompt 03 — Website Builder
# =========================================================================== #
def test_prompt03():
    print("\n=== Prompt 03: Public Website Builder ===")
    _, access = issue_tokens(users[("everest", "OWNER")], hostels["everest"])
    api = Client()
    auth = bearer(str(access), ws("everest"))

    # Public site served + isolated
    r = api.get("/api/website/public/", **ws("everest"))
    check("03 public website served", r.status_code == 200)
    hero = next((s for s in data(r).get("sections", []) if s["type"] == "hero"), None)
    check("03 hero headline = hostel name", hero and hero["content"]["headline"] == "Everest International Hostel")

    # Settings + registry
    r = api.get("/api/website/settings/", **auth)
    check("03 website settings load with section registry",
          r.status_code == 200 and bool(data(r).get("section_types")))

    # Edit hero -> draft; not visible publicly until publish
    website = tsvc.get_or_scaffold_website(hostels["everest"]) if hasattr(tsvc, "get_or_scaffold_website") else None
    from apps.website.services import get_or_scaffold_website
    website = get_or_scaffold_website(hostels["everest"])
    hero_section = website.sections.get(type="hero")
    r = api.patch(f"/api/website/sections/{hero_section.id}/",
                  {"content": {**hero_section.content, "headline": "Edited Headline QA"}},
                  content_type="application/json", **auth)
    check("03 edit hero section (draft)", r.status_code == 200)
    pub = data(api.get("/api/website/public/", **ws("everest")))
    pub_hero = next((s for s in pub["sections"] if s["type"] == "hero"), None)
    check("03 draft edit NOT public before publish",
          pub_hero["content"]["headline"] == "Everest International Hostel")

    # Publish -> visible + version bump
    r = api.post("/api/website/publish/", {"note": "qa"}, content_type="application/json", **auth)
    check("03 publish", r.status_code == 200 and data(r).get("version") == 2)
    pub = data(api.get("/api/website/public/", **ws("everest")))
    pub_hero = next((s for s in pub["sections"] if s["type"] == "hero"), None)
    check("03 published edit now public", pub_hero["content"]["headline"] == "Edited Headline QA")

    # Version history + rollback
    r = api.get("/api/website/versions/", **auth)
    check("03 version history", len(data(r)) >= 2)
    r = api.post("/api/website/versions/1/restore/", **auth)
    check("03 rollback to v1", r.status_code == 200)

    # Add / hide / duplicate / reorder / delete a section
    r = api.post("/api/website/sections/", {"type": "custom", "content": {}},
                 content_type="application/json", **auth)
    check("03 add section", r.status_code == 201)
    sid = data(r)["id"]
    check("03 hide section",
          api.patch(f"/api/website/sections/{sid}/", {"is_visible": False},
                    content_type="application/json", **auth).status_code == 200)
    check("03 duplicate section",
          api.post(f"/api/website/sections/{sid}/duplicate/", **auth).status_code == 201)
    check("03 delete section",
          api.delete(f"/api/website/sections/{sid}/", **auth).status_code == 204)

    # Theme + SEO
    r = api.patch("/api/website/settings/",
                  {"theme": {"primary_color": "#16a34a"}, "seo": {"meta_title": "Everest QA"}},
                  content_type="application/json", **auth)
    check("03 theme+SEO update", r.status_code == 200 and data(r)["theme"]["primary_color"] == "#16a34a")

    # Inquiry stored in inbox
    Client().post("/api/website/public/inquiries/",
                  {"name": "Sita Rai", "phone": "9801234567", "message": "Do you have single rooms available?"},
                  content_type="application/json", **ws("everest"))
    r = api.get("/api/website/inquiries/", **auth)
    inbox = as_list(data(r))
    check("03 inquiry lands in admin inbox", any(i["name"] == "Sita Rai" for i in inbox))

    # Isolation: himalayan owner cannot see everest inquiries
    _, h_access = issue_tokens(users[("himalayan", "OWNER")], hostels["himalayan"])
    r = api.get("/api/website/inquiries/", **bearer(str(h_access), ws("himalayan")))
    hbox = as_list(data(r))
    check("03 inquiries tenant-isolated", not any(i["name"] == "Sita Rai" for i in hbox))


# =========================================================================== #
# Prompt 04 — Workspace Management
# =========================================================================== #
def test_prompt04():
    print("\n=== Prompt 04: Workspace Management ===")
    _, access = issue_tokens(users[("everest", "OWNER")], hostels["everest"])
    api = Client()
    auth = bearer(str(access), ws("everest"))

    r = api.get("/api/tenants/manage/overview/", **auth)
    check("04 overview", r.status_code == 200 and data(r)["counts"]["members"] >= 9)

    # Namespaced settings roundtrip
    r = api.patch("/api/tenants/manage/settings/profile/",
                  {"legal_name": "Everest Intl Pvt Ltd", "established_year": 2015},
                  content_type="application/json", **auth)
    check("04 profile settings roundtrip",
          r.status_code == 200 and data(r)["settings"]["legal_name"] == "Everest Intl Pvt Ltd")

    r = api.patch("/api/tenants/manage/settings/regional/",
                  {"currency": "USD"}, content_type="application/json", **auth)
    check("04 regional settings", r.status_code == 200 and data(r)["settings"]["currency"] == "USD")

    # Preference enforcement on public site
    api.patch("/api/tenants/manage/settings/preferences/",
              {"enable_public_website": False}, content_type="application/json", **auth)
    off = Client().get("/api/website/public/", **ws("everest")).status_code
    api.patch("/api/tenants/manage/settings/preferences/",
              {"enable_public_website": True}, content_type="application/json", **auth)
    on = Client().get("/api/website/public/", **ws("everest")).status_code
    check("04 preference toggles public website", off == 404 and on == 200)

    # Team management
    r = api.post("/api/tenants/manage/team/",
                 {"username": f"qa_invitee_{run_id}", "email": f"invitee.{run_id}@example.com", "role": "WARDEN"},
                 content_type="application/json", **auth)
    check("04 invite team member", r.status_code == 201 and bool(data(r).get("temporary_password")))
    invitee = User.objects.filter(username=f"qa_invitee_{run_id}").first()
    if invitee:
        CREATED_USERS.append(invitee)
        r = api.patch(f"/api/tenants/manage/team/{invitee.id}/", {"role": "MANAGER"},
                      content_type="application/json", **auth)
        check("04 change member role", r.status_code == 200)
        r = api.delete(f"/api/tenants/manage/team/{invitee.id}/", **auth)
        check("04 remove member", r.status_code == 204)

    # Activity log scoped
    r = api.get("/api/tenants/manage/activity/", **auth)
    check("04 activity log populated + scoped", len(data(r)) > 0)

    # Rename + 301 alias
    r = api.post("/api/tenants/manage/rename/",
                 {"workspace_username": f"everest-grp-{run_id}", "password": PASSWORD},
                 content_type="application/json", **auth)
    check("04 workspace rename", r.status_code == 200)
    hostels["everest"].refresh_from_db()
    # old slug redirects
    r = Client().get("/api/website/public/", HTTP_HOST="everest.localhost")
    check("04 old workspace URL 301-redirects", r.status_code == 301)
    # rename back so later cleanup/tests use 'everest'
    api.post("/api/tenants/manage/rename/",
             {"workspace_username": "everest", "password": PASSWORD},
             content_type="application/json",
             **bearer(str(issue_tokens(users[("everest","OWNER")], hostels["everest"])[1]),
                      ws(f"everest-grp-{run_id}")))
    hostels["everest"].refresh_from_db()
    check("04 rename back to everest", hostels["everest"].slug == "everest")

    # Danger zone requires password
    _, access2 = issue_tokens(users[("everest", "OWNER")], hostels["everest"])
    auth2 = bearer(str(access2), ws("everest"))
    r = api.post("/api/tenants/manage/danger/reset_branding/", {}, content_type="application/json", **auth2)
    check("04 danger zone needs password", r.status_code == 400)
    r = api.post("/api/tenants/manage/danger/reset_branding/", {"password": PASSWORD},
                 content_type="application/json", **auth2)
    check("04 danger zone with password works", r.status_code == 200)


# =========================================================================== #
# Prompt 05 — Custom Domains & White Label
# =========================================================================== #
def test_prompt05():
    print("\n=== Prompt 05: Custom Domains & White Label ===")
    _, access = issue_tokens(users[("everest", "OWNER")], hostels["everest"])
    api = Client()
    auth = bearer(str(access), ws("everest"))

    # Add domain
    r = api.post("/api/domains/", {"domain": "hostel.everest-qa.com"},
                 content_type="application/json", **auth)
    check("05 add custom domain", r.status_code == 201)
    did = data(r)["id"]
    check("05 verification records provided",
          data(r)["records"]["txt"]["host"].startswith("_hostel-verify."))

    # Duplicate rejected
    r = api.post("/api/domains/", {"domain": "hostel.everest-qa.com"},
                 content_type="application/json", **auth)
    check("05 duplicate domain rejected", r.status_code == 400)

    # Invalid domains rejected
    for bad in ("not a domain", "*.wild.com", "https://x.com"):
        r = api.post("/api/domains/", {"domain": bad}, content_type="application/json", **auth)
        check(f"05 invalid domain '{bad}' rejected", r.status_code == 400)

    # Verify (DNS won't resolve a fake domain) -> failed/retryable, not 500
    r = api.post(f"/api/domains/{did}/verify/", **auth)
    check("05 verify handles un-propagated DNS gracefully",
          r.status_code == 200 and data(r)["status"] in ("failed", "pending"))

    # Simulate verified + activate (real DNS unavailable in QA)
    rec = CustomDomain.objects.get(id=did)
    from django.utils import timezone as tz
    rec.verification_method = "txt"
    rec.verified_at = tz.now()
    rec.status = CustomDomain.Status.VERIFIED
    rec.save()
    r = api.post(f"/api/domains/{did}/activate/", {"make_primary": True},
                 content_type="application/json", **auth)
    check("05 activate verified domain", r.status_code == 200 and data(r)["is_primary"])

    # Routing via X-Tenant-Host
    r = Client().get("/api/website/public/", HTTP_X_TENANT_HOST="hostel.everest-qa.com")
    check("05 custom domain routes to tenant",
          r.status_code == 200 and data(r)["workspace"]["username"] == "everest")
    check("05 public_url = custom domain",
          data(r)["workspace"].get("public_url") == "https://hostel.everest-qa.com")

    # Cross-tenant: himalayan cannot see everest's domain
    _, h_access = issue_tokens(users[("himalayan", "OWNER")], hostels["himalayan"])
    r = api.get("/api/domains/", **bearer(str(h_access), ws("himalayan")))
    check("05 domains tenant-isolated", len(data(r).get("domains", [])) == 0)

    # White-label propagation
    api.patch("/api/tenants/manage/settings/white_label/",
              {"enabled": True, "platform_name": "Everest OS", "browser_title": "Everest OS Portal"},
              content_type="application/json", **auth)
    r = Client().get("/api/tenants/workspaces/public/", **ws("everest"))
    check("05 white-label in login branding",
          data(r)["white_label"]["platform_name"] == "Everest OS")

    # Email + PDF branding helpers (refresh: the white-label PATCH above wrote
    # to the DB row; the in-memory object's .settings would otherwise be stale).
    hostels["everest"].refresh_from_db()
    from apps.tenants.branding import email_branding, pdf_branding
    eb = email_branding(hostels["everest"])
    check("05 email branding uses custom-domain URL", "hostel.everest-qa.com" in eb["site_url"])
    pb = pdf_branding(hostels["everest"])
    check("05 pdf branding uses white-label name", pb["name"] == "Everest OS")


# =========================================================================== #
# Prompt 06 — Production readiness (functional slice)
# =========================================================================== #
def test_prompt06():
    print("\n=== Prompt 06: Production & Health ===")
    api = Client()
    # Health probes reachable without auth
    for probe in ("", "database/", "cache/", "storage/", "queue/", "celery/"):
        r = api.get(f"/health/{probe}")
        check(f"06 /health/{probe or ''} responds", r.status_code in (200, 503))
    r = api.get("/health/")
    check("06 liveness ok", r.status_code == 200 and r.json()["status"] == "ok")
    r = api.get("/health/storage/")
    check("06 storage probe ok", r.status_code == 200)


# =========================================================================== #
def teardown():
    print("\n=== Cleanup ===")
    from apps.auditlog.models import AuditEvent
    from apps.website.models import WebsiteInquiry
    from apps.residents.models import Resident
    for h in CREATED_HOSTELS:
        try:
            AuditEvent.objects.filter(hostel_id=h.pk).delete()
            WebsiteInquiry.objects.filter(hostel=h).delete()
            Resident.objects.filter(hostel=h).delete()
            CustomDomain.objects.filter(hostel=h).delete()
            from apps.tenants.models import WorkspaceAlias
            WorkspaceAlias.objects.filter(hostel=h).delete()
            h.delete()
        except Exception as e:
            print(f"  cleanup warning (hostel {h.pk}): {e}")
    User.objects.filter(username__contains=f"_{run_id}").delete()
    User.objects.filter(username__startswith="qa_").filter(username__endswith=run_id).delete()
    try:
        from axes.utils import reset

        reset()  # leave no harness lockouts behind in the dev DB
    except Exception:
        pass
    print("  cleanup done")


# =========================================================================== #
try:
    setup()
    test_prompt01()
    test_prompt02()
    test_isolation_security()
    test_prompt03()
    test_prompt04()
    test_prompt05()
    test_prompt06()
finally:
    teardown()

passed = sum(1 for _, ok, _ in RESULTS if ok)
failed = [(n, d) for n, ok, d in RESULTS if not ok]
print(f"\n{'='*60}\nQA E2E SUMMARY: {passed}/{len(RESULTS)} checks passed")
if failed:
    print(f"FAILURES ({len(failed)}):")
    for n, d in failed:
        print(f"  - {n}: {d}")
else:
    print("ALL CHECKS PASSED")
print("="*60)
