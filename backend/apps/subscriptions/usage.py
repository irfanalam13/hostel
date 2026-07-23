"""Live usage counters for quantifiable limits (Module 11).

Maps a limit key to a callable that counts a hostel's *current* consumption.
Only quotas backed by a concrete, countable resource are registered here;
metered quotas (SMS/email/API per month) are tracked separately by the usage
metering system in a later phase and are absent from this map (their limit is
resolved but not enforced at create-time).

Counters are imported lazily inside each function to avoid import cycles
(these apps import subscriptions, not the other way around).
"""


def _count_residents(hostel) -> int:
    from apps.residents.models import Resident

    # Occupancy count: residents who have left don't consume a seat.
    return Resident.objects.filter(hostel=hostel).exclude(status="left").count()


def _count_rooms(hostel) -> int:
    from apps.rooms.models import Room

    return Room.objects.filter(hostel=hostel).count()


def _count_beds(hostel) -> int:
    from apps.rooms.models import Bed

    return Bed.objects.filter(hostel=hostel).count()


def _count_staff(hostel) -> int:
    from apps.accounts.models import UserHostel

    return UserHostel.objects.filter(hostel=hostel, is_active=True).count()


# limit key -> counter. Only keys present here are enforced at create time.
USAGE_COUNTERS = {
    "max_students": _count_residents,
    "max_rooms": _count_rooms,
    "max_beds": _count_beds,
    "max_staff": _count_staff,
}


def current_usage(hostel, limit_key: str):
    """Live consumption for a limit, or ``None`` if the key isn't countable."""
    counter = USAGE_COUNTERS.get(limit_key)
    if counter is None or hostel is None:
        return None
    try:
        return int(counter(hostel))
    except Exception:
        return None
