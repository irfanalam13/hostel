"""Website Builder serializers — validation is the security boundary here:
sections/settings are owner-authored JSON that will be rendered publicly, so
shapes, lengths and file contents are all checked server-side."""
from django.conf import settings
from rest_framework import serializers

from .models import WebsiteInquiry, WebsiteMedia, WebsiteSection, WebsiteVersion
from .sections import SECTION_TYPES

# Hard bounds for owner-authored JSON: generous for real content, small enough
# that a malicious payload can't balloon storage or the public response.
_MAX_JSON_BYTES = 200_000
_MAX_LIST_ITEMS = 100


def _validate_json_blob(value, field_name):
    import json

    if not isinstance(value, dict):
        raise serializers.ValidationError(f"{field_name} must be an object.")
    if len(json.dumps(value)) > _MAX_JSON_BYTES:
        raise serializers.ValidationError(f"{field_name} is too large.")
    return value


class WebsiteSettingsSerializer(serializers.Serializer):
    """GET/PATCH surface for the draft's global settings. Partial by design —
    each key updates independently."""

    theme = serializers.JSONField(required=False)
    seo = serializers.JSONField(required=False)
    branding = serializers.JSONField(required=False)
    navigation = serializers.JSONField(required=False)
    footer = serializers.JSONField(required=False)
    social = serializers.JSONField(required=False)

    def validate(self, attrs):
        for key, value in attrs.items():
            _validate_json_blob(value, key)
        return attrs


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteSection
        fields = ["id", "type", "order", "is_visible", "content", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_type(self, value):
        if value not in SECTION_TYPES:
            raise serializers.ValidationError("Unknown section type.")
        return value

    def validate_content(self, value):
        _validate_json_blob(value, "content")
        for key, items in value.items():
            if isinstance(items, list) and len(items) > _MAX_LIST_ITEMS:
                raise serializers.ValidationError(
                    f"'{key}' can hold at most {_MAX_LIST_ITEMS} items."
                )
        return value

    def update(self, instance, validated_data):
        # A section's type is fixed after creation (its content shape depends
        # on it); replace the section to change type.
        validated_data.pop("type", None)
        return super().update(instance, validated_data)


class ReorderSerializer(serializers.Serializer):
    """POST /sections/reorder/ — the full ordered list of section ids."""

    order = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class VersionSerializer(serializers.ModelSerializer):
    published_by = serializers.SerializerMethodField()

    class Meta:
        model = WebsiteVersion
        fields = ["number", "note", "published_by", "created_at"]

    def get_published_by(self, obj):
        return getattr(obj.published_by, "username", None)


class PublicInquirySerializer(serializers.ModelSerializer):
    """Public inquiry submission. ``website`` is a honeypot: humans never see
    it, bots fill it — such submissions are accepted (no oracle) but dropped."""

    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = WebsiteInquiry
        fields = ["name", "email", "phone", "room_interest", "message", "website"]

    def validate_name(self, value):
        value = (value or "").strip()
        if len(value) < 2:
            raise serializers.ValidationError("Please tell us your name.")
        return value

    def validate_message(self, value):
        value = (value or "").strip()
        if len(value) < 10:
            raise serializers.ValidationError("Please write a little more (at least 10 characters).")
        if len(value) > 4000:
            raise serializers.ValidationError("Message is too long.")
        return value

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("phone"):
            raise serializers.ValidationError("Provide an email or a phone number so we can reply.")
        return attrs


class InquiryAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteInquiry
        fields = ["id", "name", "email", "phone", "room_interest", "message",
                  "status", "created_at"]
        read_only_fields = ["id", "name", "email", "phone", "room_interest",
                            "message", "created_at"]


_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
_DOCUMENT_EXTENSIONS = {"pdf"}


class MediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = WebsiteMedia
        fields = ["id", "file", "url", "kind", "alt_text", "created_at"]
        read_only_fields = ["id", "url", "kind", "created_at"]

    def get_url(self, obj):
        request = self.context.get("request")
        try:
            url = obj.file.url
            return request.build_absolute_uri(url) if request else url
        except Exception:
            return ""

    def validate_file(self, uploaded):
        max_mb = int(getattr(settings, "MAX_UPLOAD_SIZE_MB", 10))
        if uploaded.size > max_mb * 1024 * 1024:
            raise serializers.ValidationError(f"File too large (max {max_mb} MB).")

        ext = (uploaded.name.rsplit(".", 1)[-1] if "." in uploaded.name else "").lower()
        if ext in _IMAGE_EXTENSIONS:
            # Sanitization: Pillow must fully parse it as an image — a script
            # or polyglot renamed to .png fails here.
            from PIL import Image

            try:
                image = Image.open(uploaded)
                image.verify()
            except Exception:
                raise serializers.ValidationError("Invalid or corrupted image file.")
            uploaded.seek(0)
            self._kind = WebsiteMedia.Kind.IMAGE
        elif ext in _DOCUMENT_EXTENSIONS:
            head = uploaded.read(5)
            uploaded.seek(0)
            if head != b"%PDF-":
                raise serializers.ValidationError("Invalid PDF file.")
            self._kind = WebsiteMedia.Kind.DOCUMENT
        else:
            raise serializers.ValidationError(
                "Unsupported file type. Allowed: jpg, jpeg, png, webp, gif, pdf."
            )
        return uploaded

    def create(self, validated_data):
        validated_data["kind"] = getattr(self, "_kind", WebsiteMedia.Kind.IMAGE)
        return super().create(validated_data)
