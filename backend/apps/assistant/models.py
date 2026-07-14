"""Persistence for the AI assistant.

Django owns all conversation state (single source of truth); the ML_hostel
microservice is stateless and reads/writes it through the gateway. Everything is
workspace-scoped exactly like the rest of the platform: ``Conversation`` and
``AiUsage`` subclass :class:`HostelScopedModel`, and ``Message`` lives under a
conversation so it inherits that tenancy transitively.
"""
from django.conf import settings
from django.db import models

from apps.common.models import HostelScopedModel, TimeStampedModel


class Conversation(HostelScopedModel):
    """A single chat thread between a workspace user and an agent."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_conversations"
    )
    title = models.CharField(max_length=200, blank=True)
    # Which agent persona handled the thread (assistant, finance, ops, ...).
    agent = models.CharField(max_length=40, default="assistant")
    # Denormalised record of the provider/model that last answered.
    provider = models.CharField(max_length=40, blank=True)
    model = models.CharField(max_length=80, blank=True)
    message_count = models.PositiveIntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]
        indexes = [
            models.Index(fields=["hostel", "user", "-last_message_at"]),
        ]

    def __str__(self):
        return self.title or f"Conversation {self.pk}"


class Message(TimeStampedModel):
    """One turn in a conversation. Tenancy comes from ``conversation.hostel``."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"
        TOOL = "tool", "Tool"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField(blank=True)
    # Structured record of any tools the assistant called for this turn.
    tool_calls = models.JSONField(default=list, blank=True)
    provider = models.CharField(max_length=40, blank=True)
    model = models.CharField(max_length=80, blank=True)
    tokens_prompt = models.PositiveIntegerField(default=0)
    tokens_completion = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]


class AiUsage(HostelScopedModel):
    """Per-request usage accounting — powers the AI dashboard and quota checks."""

    class Kind(models.TextChoices):
        CHAT = "chat", "Chat"
        REPORT = "report", "Report"
        INSIGHT = "insight", "Insight"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_usage",
    )
    conversation = models.ForeignKey(
        Conversation, null=True, blank=True, on_delete=models.SET_NULL, related_name="usage"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.CHAT)
    provider = models.CharField(max_length=40, blank=True)
    model = models.CharField(max_length=80, blank=True)
    tokens_prompt = models.PositiveIntegerField(default=0)
    tokens_completion = models.PositiveIntegerField(default=0)
    tokens_total = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    # Self-hosted models are free; kept so paid providers slot in without a migration.
    cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    success = models.BooleanField(default=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hostel", "-created_at"]),
            models.Index(fields=["hostel", "kind", "-created_at"]),
        ]
