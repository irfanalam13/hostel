import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenants.services import get_or_create_platform_workspace


@pytest.fixture
def published_hostel(hostel):
    """The shared `hostel` fixture with a published public website — the
    minimum a hostel needs to appear in the discovery directory (its
    HostelDiscoveryProfile is auto-created by the post_save signal)."""
    from apps.website import services as website_services

    website_services.get_or_scaffold_website(hostel)
    return hostel


@pytest.fixture
def platform_hostel(db):
    return get_or_create_platform_workspace()


@pytest.fixture
def consumer_user(make_user, platform_hostel):
    from apps.discovery.models import ConsumerProfile

    user = make_user(role="CONSUMER", hostel=platform_hostel)
    ConsumerProfile.objects.create(user=user, full_name="Aashish Karki", phone="9800011122")
    return user


@pytest.fixture
def consumer_client(consumer_user, platform_hostel):
    client = APIClient()
    refresh = RefreshToken.for_user(consumer_user)
    refresh["hostel_id"] = str(platform_hostel.id)
    refresh["hostel_code"] = platform_hostel.code
    refresh["role"] = "CONSUMER"
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client
