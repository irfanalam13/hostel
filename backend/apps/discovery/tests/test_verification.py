"""Residency verification matching — the phone-match auto-publish path and
the ambiguous/no-match fall-to-manual-review path."""
import datetime as dt

import pytest

from apps.discovery.models import Review
from apps.discovery.services import (
    MAX_VERIFICATION_ATTEMPTS,
    apply_verification,
    find_residency_matches,
    normalize_phone,
    verification_attempts_exhausted,
    verification_attempts_used,
)
from apps.students.models import Student
from conftest import ResidentFactory

pytestmark = pytest.mark.django_db


def test_normalize_phone_absorbs_formatting_differences():
    assert normalize_phone("+977-980-001-1122") == normalize_phone("9800011122")
    assert normalize_phone("") == ""
    assert normalize_phone(None) == ""


def _review(hostel, author):
    return Review.objects.create(hostel=hostel, author=author, rating=5, body="Great place.")


def test_exact_phone_match_against_resident_auto_publishes(hostel, consumer_user):
    resident = ResidentFactory(hostel=hostel, phone="9800011122", full_name="Aashish Karki")
    review = _review(hostel, consumer_user)

    verified = apply_verification(review, "9800011122")

    assert verified is True
    review.refresh_from_db()
    assert review.status == Review.Status.PUBLISHED
    assert review.verification_method == Review.VerificationMethod.AUTO_PHONE_MATCH
    assert review.source_resident_id == resident.id
    assert review.resident_name_snapshot == "Aashish Karki"
    assert review.verified_at is not None


def test_exact_phone_match_against_student(hostel, consumer_user):
    Student.objects.create(
        hostel=hostel, full_name="Bimala Thapa", phone="9811122233",
        join_date=dt.date(2024, 1, 1), status="LEFT",
    )
    review = _review(hostel, consumer_user)

    verified = apply_verification(review, "9811122233")

    assert verified is True
    review.refresh_from_db()
    assert review.status == Review.Status.PUBLISHED
    assert review.source_student is not None


def test_no_match_leaves_review_pending(hostel, consumer_user):
    review = _review(hostel, consumer_user)
    verified = apply_verification(review, "9999999999")

    assert verified is False
    review.refresh_from_db()
    assert review.status == Review.Status.PENDING
    assert review.verification_method == ""


def test_blank_phone_never_matches(hostel, consumer_user):
    ResidentFactory(hostel=hostel, phone="", full_name="No Phone Resident")
    review = _review(hostel, consumer_user)

    assert apply_verification(review, "") is False
    review.refresh_from_db()
    assert review.status == Review.Status.PENDING


def test_ambiguous_multi_match_falls_to_manual_review(hostel, consumer_user):
    ResidentFactory(hostel=hostel, phone="9800011122", full_name="Resident One")
    ResidentFactory(hostel=hostel, phone="9800011122", full_name="Resident Two")
    review = _review(hostel, consumer_user)

    assert apply_verification(review, "9800011122") is False
    review.refresh_from_db()
    assert review.status == Review.Status.PENDING


def test_match_is_scoped_to_the_specific_hostel(hostel, other_hostel, consumer_user):
    ResidentFactory(hostel=other_hostel, phone="9800011122", full_name="Wrong Hostel Resident")
    review = _review(hostel, consumer_user)

    assert apply_verification(review, "9800011122") is False
    review.refresh_from_db()
    assert review.status == Review.Status.PENDING


def test_past_resident_with_leave_date_still_verifies(hostel, consumer_user):
    """Past AND current residents both count — no status/leave_date filter."""
    resident = ResidentFactory(
        hostel=hostel, phone="9800011122", full_name="Former Resident", status="left",
    )
    resident.leave_date = dt.date(2025, 1, 1)
    resident.save(update_fields=["leave_date"])
    review = _review(hostel, consumer_user)

    assert apply_verification(review, "9800011122") is True
    review.refresh_from_db()
    assert review.stay_end == dt.date(2025, 1, 1)


def test_find_residency_matches_returns_empty_for_blank_phone(hostel):
    assert find_residency_matches(hostel, "") == []


# --- Per-(user, hostel) verification-attempt cap --------------------------- #
def test_failed_attempt_increments_the_per_hostel_counter(hostel, consumer_user):
    review = _review(hostel, consumer_user)

    assert apply_verification(review, "9999999999") is False

    assert verification_attempts_used(consumer_user.id, hostel.id) == 1
    assert verification_attempts_exhausted(consumer_user.id, hostel.id) is False


def test_cap_is_enforced_once_the_sixth_attempt_would_occur(hostel, consumer_user):
    review = _review(hostel, consumer_user)

    # Simulate MAX_VERIFICATION_ATTEMPTS failed phone-match attempts against
    # the same (author, hostel) pair (a real reviewer would delete + resubmit
    # between each; the cap is keyed on the pair, not the Review row, so a
    # single row is enough to exercise it here).
    for _ in range(MAX_VERIFICATION_ATTEMPTS):
        assert apply_verification(review, "0000000000") is False

    assert verification_attempts_used(consumer_user.id, hostel.id) == MAX_VERIFICATION_ATTEMPTS
    # The pair is now capped — a 6th attempt is what ReviewCreateSerializer.
    # validate() rejects up front (see apps.discovery.serializers) before ever
    # calling apply_verification again.
    assert verification_attempts_exhausted(consumer_user.id, hostel.id) is True


def test_successful_auto_match_does_not_count_against_the_cap(hostel, consumer_user):
    """A successful auto-match must not count against the cap — it exists to
    bound phone-number guessing by an unverified reviewer, not to penalize a
    genuine resident who happened to get verified (see apply_verification's
    docstring for the rationale)."""
    ResidentFactory(hostel=hostel, phone="9800011122", full_name="Aashish Karki")
    review = _review(hostel, consumer_user)

    assert apply_verification(review, "9800011122") is True

    assert verification_attempts_used(consumer_user.id, hostel.id) == 0
    assert verification_attempts_exhausted(consumer_user.id, hostel.id) is False


def test_attempt_cap_is_scoped_per_hostel(hostel, other_hostel, consumer_user):
    """A cap against one hostel must not block verification attempts against
    a different hostel for the same reviewer."""
    review = _review(hostel, consumer_user)
    for _ in range(MAX_VERIFICATION_ATTEMPTS):
        apply_verification(review, "0000000000")
    assert verification_attempts_exhausted(consumer_user.id, hostel.id) is True

    assert verification_attempts_exhausted(consumer_user.id, other_hostel.id) is False
