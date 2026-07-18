"""Dispatch Celery tasks off the request cycle — even without a worker.

The app is deployed as a single web service with no Celery worker, so tasks run
eagerly (``CELERY_TASK_ALWAYS_EAGER``). Running a slow task (an SMTP send takes
seconds) *inline* would block the HTTP response long enough to trip the SPA's
request timeout and gunicorn's worker timeout. ``dispatch_task`` keeps the
response fast by handing such a task to a short-lived daemon thread instead,
mirroring what a real worker would do — while leaving every call site and the
Celery task definitions unchanged so a worker can be reintroduced later.
"""
import logging
import threading

from django.conf import settings

logger = logging.getLogger("apps.common")


def dispatch_task(task, *args, **kwargs):
    """Run ``task`` off the request cycle.

    * Worker present (``CELERY_TASK_ALWAYS_EAGER`` False) → ``task.delay`` as
      before: the broker/worker own it.
    * No worker + ``EMAIL_SEND_IN_THREAD`` → run it in a daemon thread so a slow
      send never blocks the response. Fire-and-forget: failures are logged (the
      task also logs its own), matching the async-worker contract where the HTTP
      response can't report a delivery outcome.
    * No worker, not threaded (tests) → run inline and raise on failure so
      callers can still surface it (e.g. the OTP views' 502).
    """
    if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        return task.delay(*args, **kwargs)

    if getattr(settings, "EMAIL_SEND_IN_THREAD", False):
        def _run():
            try:
                task.apply(args=args, kwargs=kwargs)
            except Exception:  # daemon thread — nothing else will see this
                logger.warning("background task %s failed", task.name, exc_info=True)

        threading.Thread(target=_run, name=f"task:{task.name}", daemon=True).start()
        return None

    # Inline, synchronous — raise on failure (deterministic for tests).
    return task.apply(args=args, kwargs=kwargs, throw=True)
