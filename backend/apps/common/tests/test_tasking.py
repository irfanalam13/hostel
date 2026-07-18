"""dispatch_task: run a task via the worker, a thread, or inline.

Guards the workerless deploy: a slow email must not run inline in the request
(it blocks the response past the SPA/gunicorn timeout — the ~41s request-otp
incident). With no worker it goes to a daemon thread; with a worker it still
uses .delay(); in tests it runs inline so delivery is deterministic.
"""
import threading
import time

from django.test import override_settings

from apps.common.tasking import dispatch_task


class _FakeTask:
    name = "fake.task"

    def __init__(self, fail=False):
        self.fail = fail
        self.delay_args = None
        self.apply_calls = []
        self.ran = threading.Event()

    def delay(self, *args, **kwargs):
        self.delay_args = (args, kwargs)
        return "async-result"

    def apply(self, args=(), kwargs=None, throw=False):
        self.apply_calls.append((args, kwargs or {}, throw))
        self.ran.set()
        if self.fail:
            raise RuntimeError("send failed")
        return "eager-result"


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
def test_uses_delay_when_a_worker_is_present():
    task = _FakeTask()
    assert dispatch_task(task, "a", n=1) == "async-result"
    assert task.delay_args == (("a",), {"n": 1})
    assert task.apply_calls == []


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, EMAIL_SEND_IN_THREAD=False)
def test_runs_inline_and_raises_on_failure_in_test_mode():
    ok = _FakeTask()
    assert dispatch_task(ok, "x") == "eager-result"
    assert ok.apply_calls == [(("x",), {}, True)]  # throw=True

    boom = _FakeTask(fail=True)
    try:
        dispatch_task(boom, "x")
        raised = False
    except RuntimeError:
        raised = True
    assert raised, "inline dispatch must surface the failure to the caller"


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
