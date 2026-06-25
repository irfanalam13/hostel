import json

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.common.renderers import StandardJSONRenderer
from apps.tenants.models import Hostel
from apps.accounts.models import User, UserHostel
from apps.students.models import Student
from apps.students.views import StudentViewSet


def _render(data, status_code=200, path="/api/students/students/"):
    factory = APIRequestFactory()
    request = factory.get(path)

    class _Resp:
        pass

    resp = _Resp()
    resp.status_code = status_code
    raw = StandardJSONRenderer().render(
        data, renderer_context={"request": request, "response": resp}
    )
    return json.loads(raw) if raw else None


class StandardJSONRendererUnitTests(TestCase):
    def test_plain_object_is_wrapped(self):
        out = _render({"id": 1, "name": "x"})
        self.assertEqual(out["success"], True)
        self.assertEqual(out["data"], {"id": 1, "name": "x"})
        self.assertEqual(out["meta"], {})

    def test_paginated_list_moves_results_to_data(self):
        page = {"count": 2, "next": None, "previous": None, "results": [{"id": 1}, {"id": 2}]}
        out = _render(page)
        self.assertEqual(out["success"], True)
        self.assertEqual(out["data"], [{"id": 1}, {"id": 2}])
        self.assertEqual(out["meta"]["pagination"]["count"], 2)

    def test_error_body_wrapped_with_message_and_errors(self):
        out = _render({"detail": "Nope."}, status_code=403)
        self.assertEqual(out["success"], False)
        self.assertEqual(out["message"], "Nope.")
        self.assertIsNone(out["data"])
        self.assertEqual(out["errors"], {"detail": "Nope."})

    def test_field_error_message_picks_first(self):
        out = _render({"amount": ["This field is required."]}, status_code=400)
        self.assertEqual(out["success"], False)
        self.assertEqual(out["message"], "This field is required.")

    def test_auth_namespace_is_not_wrapped(self):
        out = _render({"detail": "Login successful"}, path="/api/auth/login/")
        self.assertEqual(out, {"detail": "Login successful"})

    def test_already_wrapped_is_not_double_wrapped(self):
        env = {"success": True, "message": "", "data": [1, 2], "meta": {}}
        out = _render(env)
        self.assertEqual(out, env)

    def test_none_body_stays_empty(self):
        out = _render(None, status_code=204)
        self.assertIsNone(out)


class StandardJSONRendererIntegrationTests(TestCase):
    def setUp(self):
        self.hostel = Hostel.objects.create(name="Test Hostel")
        self.user = User.objects.create_user(username="warden", password="x", role="WARDEN")
        UserHostel.objects.create(user=self.user, hostel=self.hostel, is_active=True)
        import datetime as dt
        Student.objects.create(
            hostel=self.hostel, full_name="Asha", phone="1", join_date=dt.date.today()
        )

    def test_student_list_returns_enveloped_array(self):
        factory = APIRequestFactory()
        req = factory.get("/api/students/students/")
        req.hostel = self.hostel
        force_authenticate(req, user=self.user)
        resp = StudentViewSet.as_view({"get": "list"})(req)
        resp.render()
        body = json.loads(resp.content)
        self.assertEqual(body["success"], True)
        self.assertIsInstance(body["data"], list)
        self.assertEqual(len(body["data"]), 1)
        self.assertEqual(body["data"][0]["full_name"], "Asha")
        self.assertIn("pagination", body["meta"])

    def test_anonymous_cannot_read_student_list(self):
        """Anonymous GET with a valid hostel code must be denied (tenant leak)."""
        factory = APIRequestFactory()
        req = factory.get("/api/students/students/")
        req.hostel = self.hostel  # hostel resolved from header, but no auth
        resp = StudentViewSet.as_view({"get": "list"})(req)
        self.assertIn(resp.status_code, (401, 403))

    def test_authenticated_member_can_still_read(self):
        factory = APIRequestFactory()
        req = factory.get("/api/students/students/")
        req.hostel = self.hostel
        force_authenticate(req, user=self.user)
        resp = StudentViewSet.as_view({"get": "list"})(req)
        self.assertEqual(resp.status_code, 200)


class IsStaffOrReadOnlyTests(TestCase):
    def setUp(self):
        from apps.common.permissions import IsStaffOrReadOnly
        self.perm = IsStaffOrReadOnly()
        self.factory = APIRequestFactory()

    class _Anon:
        is_authenticated = False
        role = None

    class _Member:
        is_authenticated = True
        role = "RESIDENT"  # authenticated, non-staff

    class _Staff:
        is_authenticated = True
        role = "WARDEN"

    def _check(self, method, user):
        req = getattr(self.factory, method.lower())("/x/")
        req.user = user
        return self.perm.has_permission(req, None)

    def test_anonymous_denied_read(self):
        self.assertFalse(self._check("GET", self._Anon()))

    def test_anonymous_denied_write(self):
        self.assertFalse(self._check("POST", self._Anon()))

    def test_member_can_read(self):
        self.assertTrue(self._check("GET", self._Member()))

    def test_member_cannot_write(self):
        self.assertFalse(self._check("POST", self._Member()))

    def test_staff_can_write(self):
        self.assertTrue(self._check("POST", self._Staff()))
