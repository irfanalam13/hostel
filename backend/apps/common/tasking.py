"""Dispatch Celery tasks off the request cycle — via a worker, a thread, or inline.

Some tasks are latency-sensitive and reliability-critical (transactional OTP /
password-reset email). In the split deployment — Django on Render, a Celery
worker on a free Oracle VM — those emails must stay on the *web* host: their
delivery can't depend on a separate free-tier worker being up, and running them
inline would block the HTTP response past the SPA/gunicorn timeout (the ~41s
request-otp incident). Heavy, infrequent work (backups, AI ingestion, push
fan-out) is what rides the broker to the Oracle worker instead.

``dispatch_task`` implements that policy for the email tasks:

    * Keep-local (``EMAIL_TASKS_STAY_LOCAL`` True, e.g. Render + remote worker) →
      run on THIS process, off-request: a daemon thread when
      ``EMAIL_SEND_IN_THREAD`` is on, else inline. Never touches the broker, so
      OTP delivery is independent of the worker.
    * Worker present (``CELERY_TASK_ALWAYS_EAGER`` False) and NOT kept local →
      ``task.delay`` as before: the broker/worker own it.
    * No worker (``CELERY_TASK_ALWAYS_EAGER`` True) → the same local path: a
      daemon thread when ``EMAIL_SEND_IN_THREAD``, else inline (deterministic
      for tests, and it re-raises so callers like the OTP views can 502).

Every call site and the Celery task definitions stay unchanged, so the routing
is a pure configuration decision.
"""
import logging
import threading

from django.conf import settings

logger = logging.getLogger("apps.common")


def _run_local(task, args, kwargs):
    """Run ``task`` on this process, off the request cycle, without the broker.

    A daemon thread keeps a slow send off the HTTP response (fire-and-forget:
    failures are logged, matching the async-worker contract where the response
    can't report a delivery outcome). Without threading — tests/dev — it runs
    inline and re-raises so the caller can still surface the failure.

    ``task.apply()`` always executes locally regardless of
    ``CELERY_TASK_ALWAYS_EAGER``, so this path is deterministic even when the
    global eager flag is off because a worker exists for *other* tasks.
    """
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


def dispatch_task(task, *args, **kwargs):
    """Run ``task`` off the request cycle, per the module-level policy."""
    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    stay_local = getattr(settings, "EMAIL_TASKS_STAY_LOCAL", False)

    # Offload to the broker/worker only when a worker is expected (eager off)
    # AND we haven't been told to keep these user-facing emails on the web host.
    if not eager and not stay_local:
        return task.delay(*args, **kwargs)

    return _run_local(task, args, kwargs)
