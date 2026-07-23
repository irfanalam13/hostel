"""Shared pytest fixtures + Factory Boy factories for the canonical Track A suite.

Everything here is reusable across apps/auth/billing/residents/rbac tests so no
test hardcodes its own hostel/user/room setup. Auth is done with a real JWT
Bearer token (not ``force_authenticate``) so requests traverse the full
authentication + tenant-resolution + permission stack the way production does.
"""
import datetime as dt
from decimal import Decimal

import factory
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, UserHostel
from apps.billing.models import MonthlyDue, Payment
from apps.hostel.models import Bed, Room
from apps.residents.models import Resident
from apps.tenants.models import Hostel


# ---------------------------------------------------------------------------
# Factory Boy factories
# ---------------------------------------------------------------------------
class HostelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Hostel

    name = factory.Sequence(lambda n: f"Hostel {n}")
    # code auto-generates in Hostel.save()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    role = "WARDEN"

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        obj.set_password(extracted or "TestPass!234")
        if create:
            obj.save()


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Room

    hostel = factory.SubFactory(HostelFactory)
    number = factory.Sequence(lambda n: f"R{n}")
    floor = "1"


class BedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Bed

    hostel = factory.SubFactory(HostelFactory)
    room = factory.SubFactory(RoomFactory)
    label = factory.Sequence(lambda n: f"B{n}")


class ResidentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Resident

    hostel = factory.SubFactory(HostelFactory)
    full_name = factory.Sequence(lambda n: f"Resident {n}")
    phone = factory.Sequence(lambda n: f"98000000{n:02d}")
    monthly_fee = Decimal("5000.00")


class MonthlyDueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MonthlyDue

    hostel = factory.SubFactory(HostelFactory)
    resident = factory.SubFactory(ResidentFactory)
    year = 2026
    month = factory.Sequence(lambda n: (n % 12) + 1)
    amount = Decimal("5000.00")


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    hostel = factory.SubFactory(HostelFactory)
    resident = factory.SubFactory(ResidentFactory)
    amount = Decimal("5000.00")
    method = "cash"


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clear_cache():
    """Tenant lookups are cached (apps.tenants.cache); the DB rolls back
    between tests but LocMemCache does not — clear it so no test sees a
    cached tenant from a previous test."""
    from django.core.cache import cache

    cache.clear()
    yield


@pytest.fixture
def hostel(db):
    return HostelFactory()


@pytest.fixture
def other_hostel(db):
    """A second tenant — used to prove cross-hostel isolation."""
    return HostelFactory()


@pytest.fixture
def make_user(db):
    """Factory: create a user and (optionally) link them to a hostel."""

    def _make(role="WARDEN", hostel=None, password="TestPass!234", **kwargs):
        is_super = kwargs.pop("is_superuser", False)
        user = UserFactory(role=role, password=password, **kwargs)
        if is_super:
            user.is_superuser = True
            user.is_staff = True
            user.save(update_fields=["is_superuser", "is_staff"])
        if hostel is not None:
            UserHostel.objects.create(user=user, hostel=hostel, is_active=True)
        return user

    return _make


@pytest.fixture
def api():
    """Unauthenticated API client."""
    return APIClient()


@pytest.fixture
def auth_client():
    """Factory: an APIClient authenticated as ``user`` and scoped to ``hostel``.

    Uses a real Bearer access token so the request goes through
    ``CookieJWTAuthentication`` (header branch — no CSRF needed) and the hostel
    is resolved from the ``X-Hostel-Code`` header exactly like the SPA does.
    """

    def _client(user, hostel=None):
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        if hostel is not None:
            refresh["hostel_id"] = str(hostel.id)
            refresh["hostel_code"] = hostel.code
            refresh["role"] = user.role
        access = str(refresh.access_token)
        creds = {"HTTP_AUTHORIZATION": f"Bearer {access}"}
        client.credentials(**creds)
        return client

    return _client


# Convenience role fixtures, each a member of `hostel`.
@pytest.fixture
def owner(make_user, hostel):
    return make_user(role="OWNER", hostel=hostel)


@pytest.fixture
def manager(make_user, hostel):
    return make_user(role="MANAGER", hostel=hostel)


@pytest.fixture
def accountant(make_user, hostel):
    return make_user(role="ACCOUNTANT", hostel=hostel)


@pytest.fixture
def warden(make_user, hostel):
    """A STAFF-level role (warden) that is a member of `hostel`."""
    return make_user(role="WARDEN", hostel=hostel)


@pytest.fixture
def resident_user(make_user, hostel):
    """A non-staff RESIDENT role, member of `hostel`."""
    return make_user(role="RESIDENT", hostel=hostel)


@pytest.fixture
def superuser(make_user):
    return make_user(role="ADMIN", is_superuser=True)


@pytest.fixture
def resident(hostel):
    return ResidentFactory(hostel=hostel)


@pytest.fixture
def room(hostel):
    return RoomFactory(hostel=hostel)


@pytest.fixture
def bed(hostel, room):
    return BedFactory(hostel=hostel, room=room)


@pytest.fixture
def today():
    return dt.date.today()
