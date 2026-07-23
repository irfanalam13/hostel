"""Analytics aggregation pipeline (Phase 8).

Turns the raw ``AnalyticsEvent`` stream into durable ``EventDailyRollup`` rows,
then serves daily/weekly/monthly trends from those aggregates instead of
scanning the transactional table. The daily task recomputes recent days
idempotently, so a re-run (or a late-arriving event) simply refreshes the row.
"""
from __future__ import annotations

import datetime as dt

from django.db.models import Count, Sum
from django.utils import timezone

from .models import AnalyticsEvent, EventDailyRollup


def aggregate_day(day: dt.date) -> int:
    """(Re)compute rollups for a single day. Returns number of rollup rows written."""
    grouped = (
        AnalyticsEvent.objects.filter(created_at__date=day)
        .values("hostel_id", "event_type")
        .annotate(
            count=Count("id"),
            value_sum=Sum("value"),
            unique_users=Count("user", distinct=True),
        )
    )

    written = 0
    seen = set()
    for row in grouped:
        EventDailyRollup.objects.update_or_create(
            date=day,
            hostel_id=row["hostel_id"],
            event_type=row["event_type"],
            defaults={
                "count": row["count"],
                "value_sum": row["value_sum"] or 0,
                "unique_users": row["unique_users"],
            },
        )
        seen.add((row["hostel_id"], row["event_type"]))
        written += 1

    # Drop stale rollups whose underlying events no longer exist this day
    # (e.g. after a data correction), so the aggregate never overstates.
    for rollup in EventDailyRollup.objects.filter(date=day):
        if (rollup.hostel_id, rollup.event_type) not in seen:
            rollup.delete()

    return written


def aggregate_range(start: dt.date, end: dt.date) -> int:
    """Recompute rollups for every day in [start, end] inclusive."""
    total = 0
    day = start
    while day <= end:
        total += aggregate_day(day)
        day += dt.timedelta(days=1)
    return total


def rollup_recent(days: int = 2) -> int:
    """Refresh rollups for the last ``days`` days (today + look-back)."""
    today = timezone.localdate()
    return aggregate_range(today - dt.timedelta(days=days - 1), today)


# --------------------------------------------------------------------------- #
# Pipeline-backed trends (served from rollups, not raw events)
# --------------------------------------------------------------------------- #
def _bucket_key(day: dt.date, granularity: str) -> str:
    if granularity == "month":
        return day.strftime("%Y-%m")
    if granularity == "week":
        iso = day.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    return day.isoformat()


def build_trends(hostel, days: int = 90, granularity: str = "day") -> dict:
    """Time-series of event counts per bucket, from the durable rollup table."""
    if granularity not in ("day", "week", "month"):
        granularity = "day"

    since = timezone.localdate() - dt.timedelta(days=days)
    qs = EventDailyRollup.objects.filter(date__gte=since)
    if hostel is not None:
        qs = qs.filter(hostel=hostel)

    # bucket -> event_type -> count
    series: dict[str, dict[str, int]] = {}
    totals: dict[str, int] = {}
    for row in qs.values("date", "event_type", "count", "value_sum"):
        bucket = _bucket_key(row["date"], granularity)
        series.setdefault(bucket, {})
        series[bucket][row["event_type"]] = series[bucket].get(row["event_type"], 0) + row["count"]
        totals[row["event_type"]] = totals.get(row["event_type"], 0) + row["count"]

    ordered = sorted(series.keys())
    return {
        "granularity": granularity,
        "window_days": days,
        "source": "rollup",
        "buckets": ordered,
        "series": {bucket: series[bucket] for bucket in ordered},
        "totals": totals,
    }
