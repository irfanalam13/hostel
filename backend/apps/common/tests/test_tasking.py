"""dispatch_task: run a task via the worker (broker-first), a thread, or inline.

Guards the split deploy: transactional email prefers the broker/worker (whose
egress can send SMTP the free-tier web host can't), but a broken/unreachable
broker must never hang the request — it fails fast and falls back to the on-host
path. With no worker (eager) or when forced local it runs on this host; in tests
that path runs inline so delivery is deterministic.
"""
import threading
import time

from django.test import override_settings

from apps.common.tasking import dispatch_task


class _FakeTask:
    name = "fake.task"

    def __init__(self, fail=False, fail_publish=False):
        self.fail = fail                # local apply() raises
        self.fail_publish = fail_publish  # broker apply_async() raises
        self.delay_args = None
        self.apply_async_calls = []
        self.apply_calls = []
        self.ran = threading.Event()

    def delay(self, *args, **kwargs):
        self.delay_args = (args, kwargs)
        return "async-result"

    def apply_async(self, args=(), kwargs=None, retry=None):
        self.apply_async_calls.append((tuple(args), kwargs or {}, retry))
        if self.fail_publish:
            raise RuntimeError("broker unreachable")
        return "async-result"

    def apply(self, args=(), kwargs=None, throw=False):
        self.apply_calls.append((args, kwargs or {}, throw))
        self.ran.set()
        if self.fail:
            raise RuntimeError("send failed")
        return "eager-result"


@override_settings(CELERY_TASK_ALWAYS_EAGER=False, EMAIL_TASKS_STAY_LOCAL=False)
def test_publishes_to_broker_when_a_worker_is_present():
    # A worker is configured and the broker is healthy: hand off via apply_async,
    # fail-fast (retry=False), and never run locally.
    task = _FakeTask()
    assert dispatch_task(task, "a", n=1) == "async-result"
    assert task.apply_async_calls == [(("a",), {"n": 1}, False)]
    assert task.apply_calls == []
    assert task.delay_args is None


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=False,
    EMAIL_TASKS_STAY_LOCAL=False,
    EMAIL_SEND_IN_THREAD=True,
)
def test_falls_back_to_local_when_broker_publish_fails():
    # Regression for the request-otp 502: with a worker configured (eager off)
    # but the broker unreachable, the publish must fail fast (not hang) and the
    # task must still run on this host so the request succeeds.
    task = _FakeTask(fail_publish=True)
    assert dispatch_task(task, "x") is None
    assert len(task.apply_async_calls) == 1, "must attempt the broker first"
    assert task.ran.wait(timeout=5), "must fall back to running locally"
    assert task.apply_calls[0][0] == ("x",)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, EMAIL_SEND_IN_THREAD=False)
def test_runs_inline_and_raises_on_failure_in_test_mode():
    ok = _FakeTask()
    assert dispatch_task(ok, "x") == "eager-result"
    assert ok.apply_calls == [(("x",), {}, True)]  # throw=True
    assert ok.apply_async_calls == []              # eager: never the broker

    boom = _FakeTask(fail=True)
    try:
        dispatch_task(boom, "x")
        raised = False
    except RuntimeError:
        raised = True
    assert raised, "inline dispatch must surface the failure to the caller"


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=False,
    EMAIL_TASKS_STAY_LOCAL=True,
    EMAIL_SEND_IN_THREAD=True,
)
def test_stays_local_even_when_a_worker_is_present():
    # Split deploy override: a worker exists (eager off) but email is pinned to
    # this host. It must NOT touch the broker; it runs in a local thread instead.
    task = _FakeTask()
    assert dispatch_task(task, "x") is None
    assert task.apply_async_calls == [], "must not publish email to the broker"
    assert task.ran.wait(timeout=5), "task should run locally, off-thread"
    assert task.apply_calls[0][0] == ("x",)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=False,
    EMAIL_TASKS_STAY_LOCAL=False,
    EMAIL_SEND_IN_THREAD=True,
)
def test_local_override_never_hits_the_broker():
    # local=True forces the on-host path even when the default policy would
    # publish to the broker.
    task = _FakeTask()
    assert dispatch_task(task, "x", local=True) is None
    assert task.apply_async_calls == [], "local=True must not publish to the broker"
    assert task.ran.wait(timeout=5), "task should run locally, off-thread"
    assert task.apply_calls[0][0] == ("x",)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, EMAIL_SEND_IN_THREAD=True)
def test_runs_in_background_thread_without_blocking_or_raising():
    task = _FakeTask()
    # Returns immediately (fire-and-forget), not the eager result.
    assert dispatch_task(task, "x") is None
    assert task.ran.wait(timeout=5), "task should still run, just off-thread"
    assert task.apply_calls[0][0] == ("x",)

    # A failure in the thread must not propagate to the caller.
    boom = _FakeTask(fail=True)
    assert dispatch_task(boom, "x") is None
    assert boom.ran.wait(timeout=5)
    time.sleep(0.05)  # let the thread finish its except/log path
