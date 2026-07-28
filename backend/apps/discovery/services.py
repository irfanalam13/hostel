"""Domain services: residency verification matching + directory profile sync."""
import logging
import re

from django.core.cache import cache
from django.utils import timezone

from .models import Review

logger = logging.getLogger(__name__)

# Per-(user, hostel) cap on FAILED phone-match verification attempts. Reviews
# can be deleted and resubmitted (see ReviewViewSet's docstring), so without a
# cap tied to (author, hostel) rather than to a single Review row, this
# endpoint would be a phone-number-guessing oracle for fraudulently claiming
# someone else's residency. Cache-backed (the project's default django.core.
# cache.cache — Redis-backed, see CACHES in settings — the same cache DRF's
# throttle classes read/write) so the counter needs no migration and is
# shared across workers.
MAX_VERIFICATION_ATTEMPTS = 5
_VERIFICATION_ATTEMPT_CACHE_TTL = 60 * 60 * 24  # rolling 24h window per pair


def _verification_attempts_cache_key(user_id, hostel_id) -> str:
    return f"discovery:verification-attempts:{user_id}:{hostel_id}"


def verification_attempts_used(user_id, hostel_id) -> int:
    """Current failed-attempt count for this (user, hostel) pair."""
    return cache.get(_verification_attempts_cache_key(user_id, hostel_id), 0)


def verification_attempts_exhausted(user_id, hostel_id) -> bool:
    """Whether this (user, hostel) pair has hit the failed-attempt cap —
    checked by ReviewCreateSerializer.validate() so a capped pair is rejected
    up front, before a Review row is even created, with an error distinct
    from (and enforced independently of) the endpoint's throttle budget."""
    return verification_attempts_used(user_id, hostel_id) >= MAX_VERIFICATION_ATTEMPTS


def _record_failed_verification_attempt(user_id, hostel_id) -> None:
    key = _verification_attempts_cache_key(user_id, hostel_id)
    cache.set(key, verification_attempts_used(user_id, hostel_id) + 1, _VERIFICATION_ATTEMPT_CACHE_TTL)


def normalize_phone(raw: str) -> str:
    """Digits only, keeping at most the last 10 — absorbs +977/leading-0
    formatting differences between how staff entered a resident's phone and
    how a reviewer types their own."""
    digits = re.sub(r"\D", "", raw or "")
    return digits[-10:] if len(digits) > 10 else digits


def find_residency_matches(hostel, phone: str) -> list:
    """Every Resident/Student row at this hostel whose phone matches the given
    phone (normalized). Blank phones never match. Past AND current residents
    both count — no status/leave_date filter, per the "verified past or
    current resident" requirement. Returns a list of ("resident"|"student",
    obj) tuples; more than one match is ambiguous and the caller should treat
    it the same as zero matches (fall to manual review) rather than silently
    picking one."""
    from apps.residents.models import Resident
    from apps.students.models import Student

    normalized = normalize_phone(phone)
    if not normalized:
        return []

    matches = []
    for resident in Resident.objects.filter(hostel=hostel).exclude(phone=""):
        if normalize_phone(resident.phone) == normalized:
            matches.append(("resident", resident))
    for student in Student.objects.filter(hostel=hostel).exclude(phone=""):
        if normalize_phone(student.phone) == normalized:
            matches.append(("student", student))
    return matches


def apply_verification(review: Review, phone: str) -> bool:
    """Attempt auto-verification for a freshly created (PENDING) review via
    phone match. Exactly one match -> verifies + publishes the review in
    place. Zero or ambiguous (>1) matches -> left PENDING for hostel staff to
    manually approve/reject. Returns whether it was auto-verified.

    Every non-match (zero or ambiguous) counts against the (author, hostel)
    pair's verification-attempt cap (see verification_attempts_exhausted) — a
    successful auto-match deliberately does NOT count against it, since the
    cap exists to bound phone-number guessing, not to penalize a genuine
    resident who simply got verified."""
    matches = find_residency_matches(review.hostel, phone)
    if len(matches) != 1:
        if len(matches) > 1:
            logger.warning(
                "ambiguous residency match for hostel=%s (%d candidates) — routing review %s to manual review",
                review.hostel_id, len(matches), review.pk,
            )
        _record_failed_verification_attempt(review.author_id, review.hostel_id)
        return False

    kind, obj = matches[0]
    review.verification_method = Review.VerificationMethod.AUTO_PHONE_MATCH
    review.verified_at = timezone.now()
    review.resident_name_snapshot = obj.full_name
    review.stay_start = obj.join_date
    if kind == "resident":
        review.source_resident = obj
        review.stay_end = obj.leave_date
    else:
        review.source_student = obj
        # Student has no leave_date field, only a status flag — the exact
        # departure date is unknown, so this stays null (open-ended stay).
        review.stay_end = None
    review.status = Review.Status.PUBLISHED
    review.save()
    return True


def visible_hostels_queryset():
    """Hostels eligible for the public discovery directory (and reviewable):
    not deleted/inactive, never the hidden platform workspace, published
    website, and not platform-kill-switched. Uses denormalized
    HostelDiscoveryProfile fields so it stays one indexed query across every
    hostel instead of a per-row Python check (contrast
    apps.website.services.is_publicly_visible, which checks one hostel at a
    time)."""
    from apps.tenants.models import Hostel

    return (
        Hostel.objects.filter(
            is_deleted=False,
            is_active=True,
            is_platform_workspace=False,
            website__is_published=True,
            discovery_profile__is_listed=True,
            discovery_profile__enable_public_website=True,
        )
        .select_related("discovery_profile", "website")
    )


def sync_discovery_profile(hostel):
    """Create/refresh a hostel's HostelDiscoveryProfile denormalized fields
    (city/district/hostel_type/enable_public_website) from its current
    Hostel.settings workspace-settings. Called on Hostel creation and on
    workspace-settings save (business/profile/preferences namespaces) so
    directory filtering stays a single indexed SQL query instead of loading
    every hostel's JSON settings blob in application code."""
    from apps.tenants.workspace_settings import get_workspace_settings

    from .models import HostelDiscoveryProfile

    business = get_workspace_settings(hostel, "business")
    profile = get_workspace_settings(hostel, "profile")
    preferences = get_workspace_settings(hostel, "preferences")

    defaults = {
        "city": (business.get("city") or "").strip().lower(),
        "district": (business.get("district") or "").strip().lower(),
        "hostel_type": (profile.get("hostel_type") or "").strip().lower(),
        "enable_public_website": bool(preferences.get("enable_public_website", True)),
    }
    obj, _ = HostelDiscoveryProfile.objects.update_or_create(hostel=hostel, defaults=defaults)
    return obj
