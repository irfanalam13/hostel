"""Public, anonymous discovery directory: listing, filters, search, detail,
and the per-hostel published-reviews list."""
import pytest

from apps.discovery.models import HostelDiscoveryProfile
from apps.tenants.workspace_settings import update_workspace_settings

pytestmark = pytest.mark.django_db

HOSTELS_URL = "/api/discovery/hostels/"


def _data(resp):
    body = resp.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


def test_published_hostel_appears_in_directory(api, published_hostel):
    resp = api.get(HOSTELS_URL)
    assert resp.status_code == 200, resp.content
    items = _data(resp)
    assert any(item["workspace"] == published_hostel.slug for item in items)


def test_unpublished_hostel_is_excluded(api, hostel):
    # `hostel` (unlike `published_hostel`) never had its website scaffolded/published.
    resp = api.get(HOSTELS_URL)
    items = _data(resp)
    assert not any(item["workspace"] == hostel.slug for item in items)


def test_hostel_with_public_website_disabled_is_excluded(api, published_hostel):
    update_workspace_settings(published_hostel, "preferences", {"enable_public_website": False})
    resp = api.get(HOSTELS_URL)
    items = _data(resp)
    assert not any(item["workspace"] == published_hostel.slug for item in items)


def test_platform_kill_switch_excludes_a_hostel(api, published_hostel):
    profile = HostelDiscoveryProfile.objects.get(hostel=published_hostel)
    profile.is_listed = False
    profile.save(update_fields=["is_listed"])
    resp = api.get(HOSTELS_URL)
    items = _data(resp)
    assert not any(item["workspace"] == published_hostel.slug for item in items)


def test_city_filter(api, published_hostel):
    update_workspace_settings(published_hostel, "business", {"city": "Kathmandu"})
    profile = HostelDiscoveryProfile.objects.get(hostel=published_hostel)
    assert profile.city == "kathmandu"  # normalized lowercase

    resp = api.get(HOSTELS_URL, {"city": "Kathmandu"})
    assert any(item["workspace"] == published_hostel.slug for item in _data(resp))

    resp = api.get(HOSTELS_URL, {"city": "Pokhara"})
    assert not any(item["workspace"] == published_hostel.slug for item in _data(resp))


def test_min_rating_filter(api, published_hostel):
    profile = HostelDiscoveryProfile.objects.get(hostel=published_hostel)
    profile.average_rating = 3.0
    profile.save(update_fields=["average_rating"])

    resp = api.get(HOSTELS_URL, {"min_rating": 4})
    assert not any(item["workspace"] == published_hostel.slug for item in _data(resp))

    resp = api.get(HOSTELS_URL, {"min_rating": 2})
    assert any(item["workspace"] == published_hostel.slug for item in _data(resp))


def test_amenity_filter(api, published_hostel):
    profile = HostelDiscoveryProfile.objects.get(hostel=published_hostel)
    profile.amenity_tags = ["wifi", "hot_water"]
    profile.save(update_fields=["amenity_tags"])

    resp = api.get(HOSTELS_URL, {"amenity": "wifi"})
    assert any(item["workspace"] == published_hostel.slug for item in _data(resp))

    resp = api.get(HOSTELS_URL, {"amenity": "gym"})
    assert not any(item["workspace"] == published_hostel.slug for item in _data(resp))


def test_search_by_name(api, published_hostel):
    resp = api.get(HOSTELS_URL, {"search": published_hostel.name})
    assert any(item["workspace"] == published_hostel.slug for item in _data(resp))


def test_detail_view(api, published_hostel):
    resp = api.get(f"{HOSTELS_URL}{published_hostel.slug}/")
    assert resp.status_code == 200, resp.content
    data = _data(resp)
    assert data["workspace"] == published_hostel.slug
    assert data["name"] == published_hostel.name
    assert "description" in data
    assert "rating_breakdown" in data


def test_reviews_list_empty(api, published_hostel):
    resp = api.get(f"{HOSTELS_URL}{published_hostel.slug}/reviews/")
    assert resp.status_code == 200, resp.content
    assert _data(resp) == []


def test_directory_is_paginated_with_pagination_meta(api, published_hostel):
    resp = api.get(HOSTELS_URL)
    body = resp.json()
    assert "pagination" in body["meta"]
    assert "count" in body["meta"]["pagination"]
