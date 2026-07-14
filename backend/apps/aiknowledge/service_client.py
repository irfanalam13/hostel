"""Thin client to the ML_hostel service for embedding/ingestion.

Used only by the ingestion Celery task. Auth is a tenant-scoped *system* context
token (no user). Uses stdlib urllib so the backend gains no new dependency.
"""
import json
import urllib.error
import urllib.request

from django.conf import settings

from apps.assistant.tokens import mint_system_token


class MlServiceError(Exception):
    pass


def ingest_text(hostel, text: str) -> dict:
    """Ask the service to chunk + embed ``text``.

    Returns ``{"chunks": [{"ordinal", "content", "embedding", "token_count"}],
    "model": str}``. Raises :class:`MlServiceError` on any failure.
    """
    url = f"{settings.ML_SERVICE_URL.rstrip('/')}/v1/ingest"
    token = mint_system_token(hostel=hostel)
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=settings.ML_INGEST_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise MlServiceError(f"ingest failed: HTTP {exc.code}") from exc
    except Exception as exc:  # timeout / connection / decode
        raise MlServiceError(f"ingest failed: {exc}") from exc
    return payload
