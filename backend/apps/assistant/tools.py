"""Read-only tools the assistant can call, backed by the *real* data layer.

Each tool reuses the same querysets the normal API/dashboard use — there is no
duplicated business logic and no parallel data path. A tool only runs if the
caller's captured permission set / role would allow the equivalent screen, so
tool access is bounded by RBAC exactly like the rest of the platform.

Adding a domain to the assistant = adding a ``Tool`` here (name, description,
JSON-schema params for the LLM, a permission guard, and a ``run`` that queries
existing models). The ML service discovers them via ``GET /api/ai/tools/``.
"""
import math
from dataclasses import dataclass
from typing import Callable

from django.db.models import Count, Q, Sum

from apps.common.permissions import STAFF_ROLES
from apps.common.utils import month_key


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict           # JSON schema advertised to the LLM
    guard: Callable            # (perms: set, role: str) -> bool
    run: Callable              # (hostel, args: dict, ctx: dict) -> dict


def _has(*needed):
    """Guard: caller holds ANY of the listed permissions."""
    return lambda perms, role: any(p in perms for p in needed)


def _is_staff(perms, role):
    return role in STAFF_ROLES


# --------------------------------------------------------------------------- #
# Tool implementations (all workspace-scoped; mirror dashboard/report queries)
# --------------------------------------------------------------------------- #
def _occupancy_summary(hostel, args, ctx):
    from apps.rooms.models import Bed

    stats = Bed.objects.filter(hostel=hostel).aggregate(
        total=Count("id"),
        occupied=Count("id", filter=Q(status="OCCUPIED")),
        available=Count("id", filter=Q(status="AVAILABLE")),
    )
    total = stats["total"] or 0
    occupied = stats["occupied"] or 0
    return {
        "total_beds": total,
        "occupied_beds": occupied,
        "available_beds": stats["available"] or 0,
        "occupancy_percent": round((occupied / total) * 100, 2) if total else 0,
    }


def _dues_summary(hostel, args, ctx):
    from django.utils import timezone

    from apps.fees.models import FeeLedger

    this_month = month_key(timezone.localdate())
    total_due = (
        FeeLedger.objects.filter(hostel=hostel, month=this_month).aggregate(t=Sum("net_due"))["t"]
        or 0
    )
    due_count = FeeLedger.objects.filter(
        hostel=hostel, month=this_month, status__in=["DUE", "PARTIAL"]
    ).count()
    return {
        "month": this_month,
        "total_outstanding": str(total_due),
        "students_with_dues": due_count,
    }


def _collections_summary(hostel, args, ctx):
    from django.utils import timezone

    from apps.payments.models import Payment

    today = timezone.localdate()
    today_total = (
        Payment.objects.filter(hostel=hostel, date=today).aggregate(t=Sum("amount"))["t"] or 0
    )
    month_total = (
        Payment.objects.filter(
            hostel=hostel, date__year=today.year, date__month=today.month
        ).aggregate(t=Sum("amount"))["t"]
        or 0
    )
    return {
        "date": today.isoformat(),
        "collected_today": str(today_total),
        "collected_this_month": str(month_total),
    }


def _find_students(hostel, args, ctx):
    from apps.students.models import Student

    query = (args.get("query") or "").strip()
    limit = min(int(args.get("limit") or 10), 25)
    qs = Student.objects.filter(hostel=hostel)
    status = (args.get("status") or "").strip().upper()
    if status:
        qs = qs.filter(status=status)
    if query:
        qs = qs.filter(
            Q(full_name__icontains=query)
            | Q(phone__icontains=query)
            | Q(guardian_phone__icontains=query)
        )
    rows = qs.order_by("full_name")[:limit]
    return {
        "count": qs.count(),
        "results": [
            {
                "id": str(s.id),
                "full_name": s.full_name,
                "phone": s.phone,
                "status": s.status,
            }
            for s in rows
        ],
    }


def _counts_overview(hostel, args, ctx):
    from apps.admissions.models import AdmissionRequest
    from apps.complaints.models import Complaint
    from apps.students.models import Student

    return {
        "active_students": Student.objects.filter(hostel=hostel, status="ACTIVE").count(),
        "pending_admissions": AdmissionRequest.objects.filter(
            hostel=hostel, status="PENDING"
        ).count(),
        "open_complaints": Complaint.objects.filter(
            hostel=hostel, status__in=["OPEN", "IN_PROGRESS"]
        ).count(),
    }


# --------------------------------------------------------------------------- #
# RAG retrieval (Phase 2)
# --------------------------------------------------------------------------- #
def _cosine(a, b) -> float:
    """Cosine similarity of two equal-length vectors (pure Python; small KB scale)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = num_a = num_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        num_a += x * x
        num_b += y * y
    if num_a == 0 or num_b == 0:
        return 0.0
    return dot / (math.sqrt(num_a) * math.sqrt(num_b))


def _allowed_visibilities(ctx) -> list:
    """Permission-aware retrieval: everyone sees STAFF docs; admins also see ADMIN."""
    from apps.aiknowledge.models import KnowledgeDocument

    role = ctx.get("role", "")
    perms = ctx.get("perms", set())
    vis = [KnowledgeDocument.Visibility.STAFF]
    if role in {"OWNER", "ADMIN"} or "ai.manage" in perms:
        vis.append(KnowledgeDocument.Visibility.ADMIN)
    return vis


def _search_knowledge(hostel, args, ctx):
    """Retrieve the most relevant knowledge-base chunks for a query.

    The ML service supplies the pre-computed query ``embedding`` (it owns the
    embedding model); this function does tenant- and visibility-scoped cosine
    ranking over stored chunk vectors and returns citable snippets.
    """
    from django.conf import settings

    from apps.aiknowledge.models import DocumentChunk, KnowledgeDocument

    query_vec = args.get("embedding") or []
    top_k = min(int(args.get("top_k") or getattr(settings, "ML_RAG_TOP_K", 5)), 10)
    if not query_vec:
        return {"results": [], "note": "no query embedding supplied"}

    chunks = (
        DocumentChunk.objects.filter(
            hostel=hostel,
            document__status=KnowledgeDocument.Status.READY,
            document__visibility__in=_allowed_visibilities(ctx),
        )
        .select_related("document")
        .only("content", "embedding", "ordinal", "document__id", "document__title")
    )
    scored = []
    for c in chunks:
        score = _cosine(query_vec, c.embedding)
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda t: t[0], reverse=True)

    results = []
    for score, c in scored[:top_k]:
        results.append(
            {
                "document_id": str(c.document_id),
                "title": c.document.title,
                "ordinal": c.ordinal,
                "score": round(score, 4),
                "content": c.content[:1200],
            }
        )
    return {"count": len(results), "results": results}


REGISTRY = {
    t.name: t
    for t in [
        Tool(
            name="occupancy_summary",
            description="Current bed occupancy for the hostel: total, occupied, available beds and occupancy percentage.",
            parameters={"type": "object", "properties": {}},
            guard=_has("rooms.view", "beds.view"),
            run=_occupancy_summary,
        ),
        Tool(
            name="dues_summary",
            description="Outstanding fee dues for the current month: total amount owed and how many students owe.",
            parameters={"type": "object", "properties": {}},
            guard=_has("finance.view", "billing.view"),
            run=_dues_summary,
        ),
        Tool(
            name="collections_summary",
            description="Payments collected today and this month.",
            parameters={"type": "object", "properties": {}},
            guard=_has("finance.view", "payments.view"),
            run=_collections_summary,
        ),
        Tool(
            name="find_students",
            description="Search students by name or phone. Optionally filter by status (ACTIVE/LEFT).",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "name or phone fragment"},
                    "status": {"type": "string", "enum": ["ACTIVE", "LEFT"]},
                    "limit": {"type": "integer", "description": "max results (<=25)"},
                },
            },
            guard=_is_staff,
            run=_find_students,
        ),
        Tool(
            name="counts_overview",
            description="Quick operational snapshot: active students, pending admissions, open complaints.",
            parameters={"type": "object", "properties": {}},
            guard=_is_staff,
            run=_counts_overview,
        ),
        Tool(
            name="search_knowledge",
            description=(
                "Search the hostel's knowledge base (policies, rules, manual, FAQs) for "
                "passages relevant to a question. Use this for any policy/rule/how-to "
                "question and cite the returned document titles."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "the question or topic to look up"}
                },
                "required": ["query"],
            },
            guard=_has("ai.chat"),
            run=_search_knowledge,
        ),
    ]
}


def tools_for(perms, role) -> list:
    """The subset of tool specs the caller is allowed to use (LLM-facing)."""
    perms = set(perms or [])
    return [
        {"name": t.name, "description": t.description, "parameters": t.parameters}
        for t in REGISTRY.values()
        if t.guard(perms, role)
    ]


def run_tool(name, hostel, args, perms, role) -> dict:
    """Execute a tool after re-checking the guard. Raises ``KeyError`` / ``PermissionError``."""
    tool = REGISTRY[name]
    perms = set(perms or [])
    if not tool.guard(perms, role):
        raise PermissionError(name)
    return tool.run(hostel, args or {}, {"perms": perms, "role": role})
