from rest_framework import serializers

from apps.tenants.models import Hostel

from .models import Review, ReviewFlag, ReviewResponse


def _section(snapshot: dict, section_type: str) -> dict:
    for section in (snapshot or {}).get("sections", []):
        if section.get("type") == section_type:
            return section.get("content", {}) or {}
    return {}


def _cover_image(hostel) -> str:
    website = getattr(hostel, "website", None)
    if not website:
        return ""
    snapshot = website.published_snapshot or {}
    hero = _section(snapshot, "hero")
    if hero.get("image"):
        return hero["image"]
    gallery_items = _section(snapshot, "gallery").get("items") or []
    if gallery_items and gallery_items[0].get("image"):
        return gallery_items[0]["image"]
    return ""


def _description(hostel) -> str:
    website = getattr(hostel, "website", None)
    if not website:
        return ""
    snapshot = website.published_snapshot or {}
    return (
        _section(snapshot, "hero").get("description")
        or _section(snapshot, "about").get("description")
        or (snapshot.get("seo") or {}).get("meta_description")
        or ""
    )


class DirectoryHostelListSerializer(serializers.Serializer):
    """One card in the directory grid."""

    workspace = serializers.CharField(source="slug")
    name = serializers.CharField()
    city = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    hostel_type = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    amenity_tags = serializers.SerializerMethodField()
    public_url = serializers.CharField(source="workspace_url")

    def get_city(self, hostel):
        return hostel.discovery_profile.city

    def get_district(self, hostel):
        return hostel.discovery_profile.district

    def get_hostel_type(self, hostel):
        return hostel.discovery_profile.hostel_type

    def get_cover_image(self, hostel):
        return _cover_image(hostel)

    def get_average_rating(self, hostel):
        return float(hostel.discovery_profile.average_rating)

    def get_rating_count(self, hostel):
        return hostel.discovery_profile.rating_count

    def get_amenity_tags(self, hostel):
        return hostel.discovery_profile.amenity_tags


class DirectoryHostelDetailSerializer(DirectoryHostelListSerializer):
    description = serializers.SerializerMethodField()
    rating_breakdown = serializers.SerializerMethodField()
    address = serializers.CharField()

    def get_description(self, hostel):
        return _description(hostel)

    def get_rating_breakdown(self, hostel):
        return hostel.discovery_profile.rating_breakdown


class ReviewOwnerResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewResponse
        fields = ["body", "created_at"]


class ReviewPublicSerializer(serializers.ModelSerializer):
    owner_response = ReviewOwnerResponseSerializer(read_only=True)
    author_display_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id", "rating", "title", "body", "resident_name_snapshot",
            "author_display_name", "verification_method", "stay_start", "stay_end",
            "owner_response", "created_at",
        ]

    def get_author_display_name(self, review):
        # First name + last-initial, e.g. "Aashish K." — a genuine reviewer's
        # full name stays out of a public page even though it's on file.
        name = (review.resident_name_snapshot or "").strip()
        if not name:
            return "Verified resident"
        parts = name.split()
        if len(parts) == 1:
            return parts[0]
        return f"{parts[0]} {parts[-1][0]}."


class ReviewCreateSerializer(serializers.ModelSerializer):
    """A consumer submitting a review for one hostel. Verification (auto-
    publish vs. pending) is applied in .create() via
    apps.discovery.services.apply_verification, using the phone on file in
    the author's ConsumerProfile — never accepted as request input, so a
    reviewer can't claim someone else's phone number."""

    # queryset is a placeholder — real (lazy) queryset is set in __init__ so
    # importing this module never touches the DB at class-definition time.
    hostel = serializers.SlugRelatedField(slug_field="slug", queryset=Hostel.objects.none())

    class Meta:
        model = Review
        fields = ["id", "hostel", "rating", "title", "body", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .services import visible_hostels_queryset

        self.fields["hostel"].queryset = visible_hostels_queryset()

    def validate(self, attrs):
        from .services import verification_attempts_exhausted

        request = self.context["request"]
        if Review.objects.filter(hostel=attrs["hostel"], author=request.user).exists():
            raise serializers.ValidationError(
                "You've already reviewed this hostel. Edit your existing review instead."
            )
        # Rejected up front (before a Review row is even created) once this
        # (author, hostel) pair has exhausted its failed phone-match attempt
        # cap — a distinct error from, and enforced regardless of, the
        # discovery_review throttle's remaining budget.
        if verification_attempts_exhausted(request.user.id, attrs["hostel"].id):
            raise serializers.ValidationError(
                "Too many verification attempts for this hostel. "
                "Contact the hostel staff for manual review."
            )
        return attrs

    def create(self, validated_data):
        from .services import apply_verification

        request = self.context["request"]
        review = Review.objects.create(author=request.user, **validated_data)
        profile = getattr(request.user, "consumer_profile", None)
        apply_verification(review, profile.phone if profile else "")
        review.refresh_from_db()
        return review


class ReviewUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["rating", "title", "body"]

    def save(self, **kwargs):
        kwargs.setdefault("edit_count", self.instance.edit_count + 1)
        return super().save(**kwargs)


class ReviewFlagCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewFlag
        fields = ["reason", "note"]


class ReviewResponseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewResponse
        fields = ["body"]


class MyReviewSerializer(ReviewPublicSerializer):
    """Like ReviewPublicSerializer, but includes `status` (pending/published/
    rejected/flagged) — meaningful only to the review's own author, checking
    on their own submission, never shown on the public reviews list."""

    class Meta(ReviewPublicSerializer.Meta):
        fields = ReviewPublicSerializer.Meta.fields + ["status"]


class ReviewModerationSerializer(serializers.ModelSerializer):
    """Full detail for hostel-staff and platform-admin moderation queues —
    unlike ReviewPublicSerializer, this is never shown to the public."""

    hostel_name = serializers.CharField(source="hostel.name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id", "hostel", "hostel_name", "author", "rating", "title", "body",
            "status", "verification_method", "resident_name_snapshot",
            "stay_start", "stay_end", "flag_count", "created_at",
        ]
        read_only_fields = fields
