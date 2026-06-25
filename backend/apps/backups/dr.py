"""Disaster-recovery mode control (system-wide maintenance / emergency).

Modes:
  * normal      — system operates normally.
  * maintenance — read-only; writes are rejected (used during restore).
  * emergency   — full lock; only DR admins may access (used for emergency
                  restore of a wiped system).

Mode is a singleton (:class:`DRState`). Changing it is always audited.
"""

import logging

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event

from .models import DRMode, DRState

logger = logging.getLogger("apps.backups")


def get_mode() -> str:
    return DRState.get_solo().mode


def is_normal() -> bool:
    return get_mode() == DRMode.NORMAL


def set_mode(mode: str, *, reason: str = "", user=None, request=None) -> DRState:
    """Switch the system DR mode and record an audit event."""
    if mode not in DRMode.values:
        raise ValueError(f"Invalid DR mode {mode!r}")
    previous = get_mode()
    state = DRState.set_mode(mode, reason=reason, user=user)
    logger.warning("DR mode changed: %s -> %s (%s)", previous, mode, reason)
    record_event(
        request,
        action=AuditEvent.Action.MAINTENANCE,
        actor=user,
        entity_type="dr.state",
        entity_id="1",
        message=f"DR mode {previous} -> {mode}: {reason}"[:255],
        meta={"previous": previous, "mode": mode, "reason": reason},
    )
    return state


class maintenance_window:
    """Context manager that puts the system in maintenance mode for a restore
    and always returns it to its previous mode afterwards.

        with maintenance_window(reason="restore X", user=admin):
            ... restore ...
    """

    def __init__(self, *, reason="", user=None, mode=DRMode.MAINTENANCE):
        self.reason = reason
        self.user = user
        self.mode = mode
        self._previous = None

    def __enter__(self):
        self._previous = get_mode()
        set_mode(self.mode, reason=self.reason, user=self.user)
        return self

    def __exit__(self, exc_type, exc, tb):
        restore_reason = "restore finished" if exc is None else f"restore aborted: {exc}"
        set_mode(self._previous or DRMode.NORMAL, reason=restore_reason, user=self.user)
        return False  # never suppress exceptions
