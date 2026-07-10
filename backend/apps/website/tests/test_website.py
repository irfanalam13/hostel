"""Website Builder (Prompt 03): scaffold, editing, publish/rollback flow,
public rendering, inquiries, media validation, RBAC and tenant isolation."""
import io

import pytest

from apps.website import services
from apps.website.models import WebsiteInquiry, WebsiteSection
from apps.website.sections import DEFAULT_SECTION_ORDER

pytestmark = pytest.mark.django_db

SETTINGS_URL = "/api/website/settings/"
OVERVIEW_URL = "/api/website/overview/"
SECTIONS_URL = "/api/website/sections/"
PUBLISH_URL = "/api/website/publish/"
UNPUBLISH_URL = "/api/website/unpublish/"
VERSIONS_URL = "/api/website/versions/"
INQUIRIES_URL = "/api/website/inquiries/"
MEDIA_URL = "/api/website/media/"
PUBLIC_URL = "/api/website/public/"
PUBLIC_INQUIRY_URL = "/api/website/public/inquiries/"


def _data(resp):
    body = resp.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


def _results(payload):
    return payload["results"] if isinstance(payload, dict) and "results" in payload else payload


# --- Scaffold -----------------------------------------------------------------
def test_every_hostel_automatically_gets_a_published_website(api, hostel):
    """First public hit scaffolds + publishes a professional default site."""
    resp = api.get(PUBLIC_URL, HTTP_X_WORKSPACE=hostel.slug)
    assert resp.status_code == 200, resp.content
    data = _data(resp)
    assert data["published"] is True
    assert data["version"] == 1
    assert data["workspace"]["username"] == hostel.slug
    types = [s["type"] for s in data["sections"]]
    assert types == DEFAULT_SECTION_ORDER
    # Hostel identity is woven into the scaffold.
    hero = data["sections"][0]
    assert hero["content"]["headline"] == hostel.name
    assert data["seo"]["meta_title"] == hostel.name
    assert data["theme"]["primary_color"]


def test_public_requires_workspace_context(api, db):
    assert api.get(PUBLIC_URL).status_code == 404


# --- Draft editing + publish flow ----------------------------------------------
def test_draft_edits_never_leak_until_published(api, auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    client.get(SETTINGS_URL)  # scaffold (publishes v1)

    website = services.get_or_scaffold_website(hostel)
    hero = website.sections.get(type="hero")
    resp = client.patch(
        f"{SECTIONS_URL}{hero.id}/",
        {"content": {**hero.content, "headline": "Brand New Headline"}},
        format="json",
    )
    assert resp.status_code == 200, resp.content

    # Public still serves v1 (the old headline)...
    public = _data(api.get(PUBLIC_URL, HTTP_X_WORKSPACE=hostel.slug))
    assert public["sections"][0]["content"]["headline"] == hostel.name

    # ...until publish.
    assert client.post(PUBLISH_URL, {"note": "hero update"}).status_code == 200
    public = _data(api.get(PUBLIC_URL, HTTP_X_WORKSPACE=hostel.slug))
    assert public["sections"][0]["content"]["headline"] == "Brand New Headline"
    assert public["version"] == 2


def test_unpublish_takes_site_offline(api, auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    client.get(SETTINGS_URL)
    assert client.post(UNPUBLISH_URL).status_code == 200
    resp = api.get(PUBLIC_URL, HTTP_X_WORKSPACE=hostel.slug)
    assert resp.status_code == 404
    # Republish brings it back.
    assert client.post(PUBLISH_URL).status_code == 200
    assert api.get(PUBLIC_URL, HTTP_X_WORKSPACE=hostel.slug).status_code == 200


def test_version_history_and_rollback(auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    client.get(SETTINGS_URL)  # v1

    website = services.get_or_scaffold_website(hostel)
    hero = website.sections.get(type="hero")
    client.patch(f"{SECTIONS_URL}{hero.id}/",
                 {"content": {**hero.content, "headline": "V2 Headline"}}, format="json")
    client.post(PUBLISH_URL)  # v2

    versions = _data(client.get(VERSIONS_URL))
    assert [v["number"] for v in versions] == [2, 1]

    # Restore v1 into the draft (publish stays at v2 until republished).
    # Restore replaces the draft's section rows wholesale.
    assert client.post(f"{VERSIONS_URL}1/restore/").status_code == 200
    fresh = website.sections.get(type="hero")
    assert fresh.content["headline"] == hostel.name

    overview = _data(client.get(OVERVIEW_URL))
    assert overview["has_unpublished_changes"] is True


# --- Sections ------------------------------------------------------------------
def test_section_add_hide_duplicate_reorder_delete(auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    client.get(SETTINGS_URL)

    # Add
    resp = client.post(SECTIONS_URL, {"type": "custom", "content": {}}, format="json")
    assert resp.status_code == 201, resp.content
    custom_id = _data(resp)["id"]
    # Added at the end with the registry default content.
    assert _data(resp)["content"]["title"] == ""

    # Hide
    resp = client.patch(f"{SECTIONS_URL}{custom_id}/", {"is_visible": False}, format="json")
    assert _data(resp)["is_visible"] is False

    # Duplicate
    website = services.get_or_scaffold_website(hostel)
    faq = website.sections.get(type="faq")
    resp = client.post(f"{SECTIONS_URL}{faq.id}/duplicate/")
    assert resp.status_code == 201
    assert _data(resp)["type"] == "faq"

    # Reorder (reverse everything)
    ids = [str(s.id) for s in website.sections.all().order_by("order", "created_at")]
    resp = client.post(f"{SECTIONS_URL}reorder/", {"order": list(reversed(ids))}, format="json")
    assert resp.status_code == 200
    new_order = [s["id"] for s in _data(resp)]
    assert new_order == list(reversed(ids))

    # Reorder must include every id exactly once.
    resp = client.post(f"{SECTIONS_URL}reorder/", {"order": ids[:2]}, format="json")
    assert resp.status_code == 400

    # Delete
    assert client.delete(f"{SECTIONS_URL}{custom_id}/").status_code == 204

    # Hidden sections don't reach the public payload.
    client.patch(f"{SECTIONS_URL}{faq.id}/", {"is_visible": False}, format="json")
    client.post(PUBLISH_URL)


def test_unknown_section_type_rejected(auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    client.get(SETTINGS_URL)
    resp = client.post(SECTIONS_URL, {"type": "evil-type", "content": {}}, format="json")
    assert resp.status_code == 400


def test_hidden_sections_excluded_from_public(api, auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    client.get(SETTINGS_URL)
    website = services.get_or_scaffold_website(hostel)
    faq = website.sections.get(type="faq")
    client.patch(f"{SECTIONS_URL}{faq.id}/", {"is_visible": False}, format="json")
    client.post(PUBLISH_URL)
    public = _data(api.get(PUBLIC_URL, HTTP_X_WORKSPACE=hostel.slug))
    assert "faq" not in [s["type"] for s in public["sections"]]


# --- Theme / SEO settings --------------------------------------------------------
def test_theme_and_seo_update_and_publish(api, auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    client.get(SETTINGS_URL)
    resp = client.patch(SETTINGS_URL, {
        "theme": {"primary_color": "#16a34a", "font": "serif"},
        "seo": {"meta_title": "Everest — Best Hostel", "meta_description": "Great rooms."},
    }, format="json")
    assert resp.status_code == 200, resp.content
    data = _data(resp)
    assert data["theme"]["primary_color"] == "#16a34a"
    # Defaults overlay: untouched keys keep their default values.
    assert data["theme"]["accent_color"]

    client.post(PUBLISH_URL)
    public = _data(api.get(PUBLIC_URL, HTTP_X_WORKSPACE=hostel.slug))
    assert public["theme"]["primary_color"] == "#16a34a"
    assert public["seo"]["meta_title"] == "Everest — Best Hostel"


# --- Tenant isolation -------------------------------------------------------------
def test_websites_are_tenant_isolated(api, auth_client, make_user, hostel, other_hostel):
    owner_a = make_user(role="OWNER", hostel=hostel)
    owner_b = make_user(role="OWNER", hostel=other_hostel)
    client_a = auth_client(owner_a, hostel)
    client_b = auth_client(owner_b, other_hostel)

    client_a.get(SETTINGS_URL)
    client_b.get(SETTINGS_URL)

    website_a = services.get_or_scaffold_website(hostel)
    hero_a = website_a.sections.get(type="hero")

    # B cannot read or write A's sections (404 — different tenant's draft).
    assert client_b.get(f"{SECTIONS_URL}{hero_a.id}/").status_code == 404
    assert client_b.patch(
        f"{SECTIONS_URL}{hero_a.id}/", {"content": {"headline": "hacked"}}, format="json"
    ).status_code == 404

    # Public payloads never mix.
    pa = _data(api.get(PUBLIC_URL, HTTP_X_WORKSPACE=hostel.slug))
    pb = _data(api.get(PUBLIC_URL, HTTP_X_WORKSPACE=other_hostel.slug))
    assert pa["workspace"]["username"] == hostel.slug
    assert pb["workspace"]["username"] == other_hostel.slug
    assert pa["sections"][0]["content"]["headline"] == hostel.name
    assert pb["sections"][0]["content"]["headline"] == other_hostel.name


# --- RBAC ---------------------------------------------------------------------------
def test_staff_cannot_edit_or_publish(auth_client, make_user, hostel):
    staff = make_user(role="STAFF", hostel=hostel)
    client = auth_client(staff, hostel)
    assert client.get(SETTINGS_URL).status_code == 403     # no website.view
    assert client.post(PUBLISH_URL).status_code == 403


def test_manager_can_edit_and_publish(auth_client, make_user, hostel):
    manager = make_user(role="MANAGER", hostel=hostel)
    client = auth_client(manager, hostel)
    assert client.get(SETTINGS_URL).status_code == 200
    assert client.post(PUBLISH_URL).status_code == 200


# --- Inquiries -------------------------------------------------------------------
def test_public_inquiry_stored_in_admin_inbox(api, auth_client, owner, hostel):
    resp = api.post(PUBLIC_INQUIRY_URL, {
        "name": "Ram Sharma", "phone": "9800000000",
        "room_interest": "Single room",
        "message": "I would like to visit this weekend.",
    }, HTTP_X_WORKSPACE=hostel.slug)
    assert resp.status_code == 201, resp.content

    inquiry = WebsiteInquiry.objects.get(hostel=hostel)
    assert inquiry.status == "new"

    client = auth_client(owner, hostel)
    inbox = _results(_data(client.get(INQUIRIES_URL)))
    assert len(inbox) == 1
    assert inbox[0]["name"] == "Ram Sharma"

    # Mark read
    resp = client.patch(f"{INQUIRIES_URL}{inbox[0]['id']}/", {"status": "read"}, format="json")
    assert _data(resp)["status"] == "read"


def test_inquiry_honeypot_drops_bots_silently(api, hostel):
    resp = api.post(PUBLIC_INQUIRY_URL, {
        "name": "Bot Bot", "email": "bot@spam.io",
        "message": "Buy cheap things online now!!",
        "website": "http://spam.example",  # honeypot — humans never see it
    }, HTTP_X_WORKSPACE=hostel.slug)
    assert resp.status_code == 201  # same response, no oracle
    assert WebsiteInquiry.objects.count() == 0


def test_inquiry_requires_contact_and_message(api, hostel):
    resp = api.post(PUBLIC_INQUIRY_URL, {"name": "X", "message": "hi"},
                    HTTP_X_WORKSPACE=hostel.slug)
    assert resp.status_code == 400


def test_inquiries_are_tenant_isolated(api, auth_client, make_user, hostel, other_hostel):
    api.post(PUBLIC_INQUIRY_URL, {
        "name": "For A", "phone": "980", "message": "Interested in a room here.",
    }, HTTP_X_WORKSPACE=hostel.slug)
    owner_b = make_user(role="OWNER", hostel=other_hostel)
    inbox_b = _results(_data(auth_client(owner_b, other_hostel).get(INQUIRIES_URL)))
    assert inbox_b == []


# --- Media -----------------------------------------------------------------------
def _png_bytes():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "blue").save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def test_media_upload_valid_image(auth_client, owner, hostel):
    from django.core.files.uploadedfile import SimpleUploadedFile

    client = auth_client(owner, hostel)
    upload = SimpleUploadedFile("photo.png", _png_bytes(), content_type="image/png")
    resp = client.post(MEDIA_URL, {"file": upload, "alt_text": "front gate"}, format="multipart")
    assert resp.status_code == 201, resp.content
    data = _data(resp)
    assert data["kind"] == "image"
    assert data["url"]
    # Tenant-prefixed storage path.
    assert str(hostel.id) in data["file"]


def test_media_rejects_fake_image_and_unknown_types(auth_client, owner, hostel):
    from django.core.files.uploadedfile import SimpleUploadedFile

    client = auth_client(owner, hostel)
    fake = SimpleUploadedFile("evil.png", b"<script>alert(1)</script>", content_type="image/png")
    assert client.post(MEDIA_URL, {"file": fake}, format="multipart").status_code == 400

    exe = SimpleUploadedFile("tool.exe", b"MZ\x90\x00", content_type="application/octet-stream")
    assert client.post(MEDIA_URL, {"file": exe}, format="multipart").status_code == 400


def test_media_rejects_fake_pdf(auth_client, owner, hostel):
    from django.core.files.uploadedfile import SimpleUploadedFile

    client = auth_client(owner, hostel)
    fake = SimpleUploadedFile("doc.pdf", b"not a pdf at all", content_type="application/pdf")
    assert client.post(MEDIA_URL, {"file": fake}, format="multipart").status_code == 400


# --- Overview ----------------------------------------------------------------------
def test_overview_reports_status_and_missing_sections(auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    client.get(SETTINGS_URL)
    data = _data(client.get(OVERVIEW_URL))
    assert data["is_published"] is True
    assert data["published_version"] == 1
    assert data["section_count"] == len(DEFAULT_SECTION_ORDER)
    assert data["missing_sections"] == []  # scaffold includes every recommended type
    assert 0 <= data["seo_score"] <= 100
    assert data["inquiry_count"] == 0

    # Deleting a recommended section shows up as missing.
    website = services.get_or_scaffold_website(hostel)
    website.sections.filter(type="faq").delete()
    data = _data(client.get(OVERVIEW_URL))
    assert "faq" in data["missing_sections"]
