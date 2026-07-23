from rest_framework import serializers
from .models import Faq, Lead, LegalDocument, SitePage


class FaqSerializer(serializers.ModelSerializer):
    class Meta:
        model = Faq
        fields = ["id", "question", "answer", "category", "order"]


class LegalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalDocument
        fields = ["slug", "eyebrow", "title", "description", "last_updated", "sections"]


class SitePageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SitePage
        fields = ["slug", "eyebrow", "title", "description", "body"]


class LeadSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ["name", "email", "organization", "message", "kind"]
        extra_kwargs = {
            "organization": {"required": False},
            "kind": {"required": False},
        }

    def validate_message(self, value):
        value = (value or "").strip()
        if len(value) < 5:
            raise serializers.ValidationError("Please tell us a little more.")
        return value
