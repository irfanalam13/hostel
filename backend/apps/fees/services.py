from decimal import Decimal
from django.db import transaction
from .models import StudentFeePlan, FeeLedger
from apps.students.models import Student

def get_student_plan_for_month(hostel, student, month: str):
    # month: YYYY-MM
    q = StudentFeePlan.objects.filter(hostel=hostel, student=student)
    for link in q.select_related("fee_plan"):
        if link.start_month <= month and (link.end_month is None or month <= link.end_month):
            return link.fee_plan
    return None

@transaction.atomic
def generate_monthly_ledger(hostel, month: str):
    """
    Create FeeLedger for ACTIVE students who have a fee plan for that month.
    Does NOT overwrite existing ledgers (idempotent).
    """
    created = 0
    for student in Student.objects.filter(hostel=hostel, status="ACTIVE"):
        plan = get_student_plan_for_month(hostel, student, month)
        if not plan:
            continue
        obj, was_created = FeeLedger.objects.get_or_create(
            hostel=hostel,
            student=student,
            month=month,
            defaults={
                "amount": plan.monthly_amount,
                "discount": Decimal("0"),
                "fine": Decimal("0"),
                "net_due": plan.monthly_amount,
                "status": "DUE",
            }
        )
        if was_created:
            created += 1
    return {"month": month, "created": created}