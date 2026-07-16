"""Export real-world failure cases into eval candidates (Phase 6 drift loop).

Closes the quality loop: answers users rated 👎 (or that errored) become
candidate cases for the AI eval set (ML_hostel/tests). Run periodically; review
the output and fold genuine failures into the golden set so the model/prompt is
tested against real misses, not just synthetic prompts.

    python manage.py ai_eval_export --days 30 --out eval-candidates.json
"""
import json

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.assistant.models import AiUsage, Message


class Command(BaseCommand):
    help = "Export thumbs-down / errored AI answers as eval-set candidates (JSON)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Look-back window.")
        parser.add_argument("--out", default="eval-candidates.json", help="Output JSON path.")
        parser.add_argument("--include-errors", action="store_true", default=True,
                            help="Also include answers that failed (success=False).")

    def handle(self, *args, **opts):
        since = timezone.now() - timezone.timedelta(days=opts["days"])
        qs = AiUsage.objects.filter(created_at__gte=since, kind=AiUsage.Kind.CHAT).select_related(
            "conversation"
        )

        candidates = []
        for usage in qs:
            fb = (usage.meta or {}).get("feedback") or {}
            negative = fb.get("rating") == "down"
            errored = opts["include_errors"] and not usage.success
            if not (negative or errored):
                continue

            conv = usage.conversation
            question = answer = ""
            if conv is not None:
                last_user = conv.messages.filter(role=Message.Role.USER).order_by("-created_at").first()
                last_asst = conv.messages.filter(role=Message.Role.ASSISTANT).order_by("-created_at").first()
                question = getattr(last_user, "content", "") or ""
                answer = getattr(last_asst, "content", "") or ""

            candidates.append({
                "conversation_id": str(getattr(conv, "id", "")),
                "reason": "thumbs_down" if negative else "error",
                "question": question,
                "answer": answer,
                "model": usage.model,
                "prompt_version": (usage.meta or {}).get("prompt_version", ""),
                "feedback_note": fb.get("note", ""),
            })

        with open(opts["out"], "w", encoding="utf-8") as fh:
            json.dump({"generated_days": opts["days"], "count": len(candidates),
                       "candidates": candidates}, fh, indent=2)

        self.stdout.write(self.style.SUCCESS(
            f"Exported {len(candidates)} eval candidate(s) to {opts['out']}."
        ))
