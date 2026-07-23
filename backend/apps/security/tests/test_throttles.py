"""Concrete throttle classes: auth (per-IP), role/plan (global), tenant."""
import time
from types import SimpleNamespace

from django.test import RequestFactory

from apps.security import conf
from apps.security.throttles import LoginRateThrottle, RoleRateThrottle

from .conftest import make_config

rf = RequestFactory()


def _install(overrides=None):
    snap = make_config(overrides)
    conf._snapshot = snap
    conf._snapshot_gen = snap.generation
    conf._last_check = time.monotonic()
    return snap


class TestLoginThrottle:
    def test_per_ip_limit_enforced(self, install_config):
        _install({"rate_limits": {"auth_login": {
            "enabled": True, "algorithm": "sliding_window",
            "limit": 3, "window_seconds": 300}}})
        throttle = LoginRateThrottle()
        request = rf.post("/api/auth/login/")
        request.client_ip = "8.8.8.8"
        assert sum(throttle.allow_request(request, None) for _ in range(3)) == 3
        assert throttle.allow_request(request, None) is False
        assert throttle.wait() >= 1

    def test_limits_are_per_ip(self, install_config):
        _install({"rate_limits": {"auth_login": {
            "enabled": True, "limit": 1, "window_seconds": 300}}})
        throttle = LoginRateThrottle()
        a = rf.post("/api/auth/login/")
        a.client_ip = "8.8.8.8"
        b = rf.post("/api/auth/login/")
        b.client_ip = "9.9.9.9"
        assert throttle.allow_request(a, None) is True
        assert throttle.allow_request(a, None) is False
        assert throttle.allow_request(b, None) is True


class TestRoleRateThrottle:
    def _cfg(self, **roles):
        return {"role_limits": {
            "enabled": True, "window_seconds": 60, "algorithm": "sliding_window",
            "anon": 2, "roles": {"STUDENT": 3, "ADMIN": 10, "default": 5, **roles},
            "method_costs": {"GET": 1, "POST": 2, "OPTIONS": 0},
        }}

    def test_anonymous_budget(self, install_config):
        _install(self._cfg())
        throttle = RoleRateThrottle()
        request = rf.get("/api/x/")
        request.client_ip = "1.1.1.1"
        request.user = SimpleNamespace(is_authenticated=False)
        assert sum(throttle.allow_request(request, None) for _ in range(2)) == 2
        assert throttle.allow_request(request, None) is False

    def test_role_budget_and_isolation(self, install_config):
        _install(self._cfg())
        throttle = RoleRateThrottle()

        def req(uid, role):
            r = rf.get("/api/x/")
            r.client_ip = "1.1.1.1"
            r.user = SimpleNamespace(is_authenticated=True, pk=uid, role=role,
                                     is_superuser=False)
            r.tenant = None
            return r

        student = req(1, "STUDENT")
        assert sum(throttle.allow_request(student, None) for _ in range(3)) == 3
        assert throttle.allow_request(student, None) is False
        # A different user (admin) has an independent, larger budget.
        admin = req(2, "ADMIN")
        assert throttle.allow_request(admin, None) is True

    def test_write_costs_more_than_read(self, install_config):
        _install(self._cfg(STUDENT=4))
        throttle = RoleRateThrottle()
        r = rf.post("/api/x/")
        r.client_ip = "1.1.1.1"
        r.user = SimpleNamespace(is_authenticated=True, pk=1, role="STUDENT",
                                 is_superuser=False)
        r.tenant = None
        # POST costs 2 -> only 2 writes fit in a budget of 4.
        assert throttle.allow_request(r, None) is True
        assert throttle.allow_request(r, None) is True
        assert throttle.allow_request(r, None) is False

    def test_options_never_counted(self, install_config):
        _install(self._cfg(STUDENT=1))
        throttle = RoleRateThrottle()
        r = rf.options("/api/x/")
        r.client_ip = "1.1.1.1"
        r.user = SimpleNamespace(is_authenticated=True, pk=1, role="STUDENT",
                                 is_superuser=False)
        r.tenant = None
        for _ in range(5):
            assert throttle.allow_request(r, None) is True

    def test_plan_multiplier_scales_budget(self, install_config):
        _install({**self._cfg(STUDENT=2),
                  "plan_multipliers": {"enterprise": 3.0, "default": 1.0}})
        throttle = RoleRateThrottle()
        r = rf.get("/api/x/")
        r.client_ip = "1.1.1.1"
        r.user = SimpleNamespace(is_authenticated=True, pk=1, role="STUDENT",
                                 is_superuser=False)
        r.tenant = SimpleNamespace(pk=9, plan_name="enterprise", slug="w",
                                   _state=SimpleNamespace(fields_cache={}))
        assert sum(throttle.allow_request(r, None) for _ in range(6)) == 6   # 2*3
        assert throttle.allow_request(r, None) is False

    def test_disabled_is_passthrough(self, install_config):
        _install({"role_limits": {"enabled": False}})
        throttle = RoleRateThrottle()
        r = rf.get("/api/x/")
        r.client_ip = "1.1.1.1"
        r.user = SimpleNamespace(is_authenticated=False)
        for _ in range(50):
            assert throttle.allow_request(r, None) is True
