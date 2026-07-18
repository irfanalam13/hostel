"""Dispatch Celery tasks off the request cycle — via a worker, a thread, or inline.

Transactional email (OTP / password-reset / Hostel-ID) is latency-sensitive and
reliability-critical. In the split deployment — Django on Render (free tier),
a Celery worker on a free Oracle VM — the worker is the *preferred* sender:
Render's free tier blocks outbound SMTP, so a send attempted on the web host
just times out, whereas the Oracle worker's egress can reach the SMTP relay.

``dispatch_task`` implements that policy:

    * Forced local (``local=True``) or no worker (``CELERY_TASK_ALWAYS_EAGER``
      True) or told to keep on this host (``EMAIL_TASKS_STAY_LOCAL`` True) →
      run on THIS process, off-request: a daemon thread when
      ``EMAIL_SEND_IN_THREAD`` is on, else inline (deterministic for tests, and
      it re-raises so callers like the OTP views can 502).
    * Otherwise → **broker-first**: publish to the broker (``apply_async``) so
      the Oracle worker sends it, but fail-fast (``retry=False`` + the broker
      socket timeout in settings) and fall back to the local path if the broker
      is unreachable. So a broker outage degrades to an on-host attempt instead
      of hanging the request for ~20s and 502-ing it (the request-otp incident),
      and delivery automatically moves to the worker the moment the broker is
      healthy — no code change, no flag flip.

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


def dispatch_task(task, *args, local=False, **kwargs):
    """Run ``task`` off the request cycle, per the module-level policy.

    ``local=True`` forces the on-host path (thread/inline), bypassing the broker
    even when a worker is configured. Otherwise the broker/worker is preferred
    (so a worker whose egress can send SMTP delivers transactional email), with a
    fail-fast publish and a local fallback so an unreachable broker can never
    hang or 502 the request.
    """
    eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
    stay_local = getattr(settings, "EMAIL_TASKS_STAY_LOCAL", False)

    # Forced local, no worker (eager), or told to keep on this host → run here.
    if local or eager or stay_local:
        return _run_local(task, args, kwargs)

    # Broker-first: hand off to the worker, but publish fail-fast (retry=False +
    # the broker socket timeout in settings) so an unreachable/misconfigured
    # broker raises in ~seconds instead of retrying the connection until gunicorn
    # kills the request. Fall back to the on-host path so the request still
    # succeeds (and the send is at least attempted) during a broker outage.
    try:
        return task.apply_async(args, kwargs, retry=False)
    except Exception:
        logger.warning(
            "broker publish failed for %s; falling back to local execution",
            task.name, exc_info=True,
        )
        return _run_local(task, args, kwargs)
