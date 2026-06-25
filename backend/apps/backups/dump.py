"""Canonical (Track A) data export.

This module is the single source of truth for *what* a backup contains and the
*order* in which canonical tables must be restored (FK dependencies). Track B
(legacy: students/rooms/fees/payments) is still written into backup files so no
legacy data is lost mid-migration, but it is deliberately excluded from the new
DR restore/validation/integrity logic per the Phase-4 canonical-domain rule.
"""

from collections import namedtuple

from django.apps import apps
from django.utils.timezone import now

from apps.tenants.models import Hostel

# Bump when the canonical dump shape changes. Restores reject incompatible files.
BACKUP_SCHEMA_VERSION = 2
SUPPORTED_SCHEMA_VERSIONS = frozenset({2})

# A canonical section: dump key, "app.Model", and how it is scoped to a hostel
# ("hostel" = direct hostel FK, "resident" = via resident__hostel).
Section = namedtuple("Section", ["key", "model", "scope"])

# Ordered for restore: parents before children (FK dependency order).
CANONICAL_SECTIONS = [
    Section("hostel_rooms", "hostel.Room", "hostel"),
    Section("hostel_beds", "hostel.Bed", "hostel"),
    Section("residents", "residents.Resident", "hostel"),
    Section("bed_assignment_history", "residents.BedAssignmentHistory", "hostel"),
    Section("stays", "residents.Stay", "resident"),
    Section("monthly_dues", "billing.MonthlyDue", "hostel"),
    Section("billing_payments", "billing.Payment", "hostel"),
    Section("invoices", "billing.Invoice", "resident"),
    Section("ledger_entries", "billing.LedgerEntry", "resident"),
    Section("vacate_requests", "billing.VacateRequest", "resident"),
    Section("attendance", "attendance.Attendance", "hostel"),
]

# Required for a backup to be considered valid/restorable (Phase-4 checklist:
# residents, billing, payments, attendance, rooms/beds).
REQUIRED_SECTIONS = (
    "residents",
    "monthly_dues",       # billing
    "billing_payments",   # payments
    "attendance",
    "hostel_rooms",       # rooms
    "hostel_beds",        # beds
)


def get_section_model(section: Section):
    return apps.get_model(section.model)


def section_queryset(section: Section, hostel: Hostel):
    model = get_section_model(section)
    if section.scope == "hostel":
        return model.objects.filter(hostel=hostel)
    if section.scope == "resident":
        return model.objects.filter(resident__hostel=hostel)
    raise ValueError(f"Unknown scope {section.scope!r} for section {section.key!r}")


def _values(queryset):
    return list(queryset.values())


def build_hostel_dump(hostel: Hostel) -> dict:
    """Serialise one hostel's canonical data (plus legacy Track B for safety)."""
    data = {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "hostel": {
            "id": str(hostel.id),
            "name": hostel.name,
            "code": hostel.code,
            "address": hostel.address,
            "phone": hostel.phone,
            "owner_name": hostel.owner_name,
            "plan_name": hostel.plan_name,
        },
    }

    # --- Track A (canonical) ---
    for section in CANONICAL_SECTIONS:
        data[section.key] = _values(section_queryset(section, hostel))

    # --- Track B (legacy) — preserved in the file, excluded from DR restore ---
    from apps.fees.models import FeeLedger, FeePlan, StudentFeePlan
    from apps.payments.models import Payment as LegacyPayment
    from apps.rooms.models import Bed as LegacyBed
    from apps.rooms.models import BedAssignment, Room as LegacyRoom
    from apps.students.models import Student, StudentDocument

    data.update({
        "rooms": _values(LegacyRoom.objects.filter(hostel=hostel)),
        "beds": _values(LegacyBed.objects.filter(hostel=hostel)),
        "bed_assignments": _values(BedAssignment.objects.filter(hostel=hostel)),
        "students": _values(Student.objects.filter(hostel=hostel)),
        "student_documents": _values(StudentDocument.objects.filter(hostel=hostel)),
        "fee_plans": _values(FeePlan.objects.filter(hostel=hostel)),
        "student_fee_plans": _values(StudentFeePlan.objects.filter(hostel=hostel)),
        "fee_ledgers": _values(FeeLedger.objects.filter(hostel=hostel)),
        "payments": _values(LegacyPayment.objects.filter(hostel=hostel)),
    })

    data["generated_at"] = now().isoformat()
    return data


def canonical_counts(hostel: Hostel) -> dict:
    """Live row counts for each canonical section (used by integrity checks)."""
    return {s.key: section_queryset(s, hostel).count() for s in CANONICAL_SECTIONS}
