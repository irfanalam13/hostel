from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.common.permissions import HasHostelContext, IsOwnerOrManager
from apps.common.utils import month_key
from apps.payments.models import Payment
from apps.fees.models import FeeLedger
from apps.rooms.models import Bed
from apps.students.models import Student
from apps.complaints.models import Complaint
from apps.admissions.models import AdmissionRequest
from apps.operations.models import EntryExitLog, LeaveRequest

class OwnerDashboardView(APIView):
    permission_classes = [HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        hostel = request.hostel
        today = timezone.localdate()
        this_month = month_key(today)

        today_collection = Payment.objects.filter(hostel=hostel, date=today).aggregate(total=Sum("amount"))["total"] or 0
        month_collection = Payment.objects.filter(hostel=hostel, date__year=today.year, date__month=today.month).aggregate(total=Sum("amount"))["total"] or 0

        total_due = FeeLedger.objects.filter(hostel=hostel, month=this_month).aggregate(total=Sum("net_due"))["total"] or 0
        due_count = FeeLedger.objects.filter(hostel=hostel, month=this_month, status__in=["DUE","PARTIAL"]).count()

        # One pass over beds instead of three separate COUNT round-trips.
        bed_stats = Bed.objects.filter(hostel=hostel).aggregate(
            total=Count("id"),
            occupied=Count("id", filter=Q(status="OCCUPIED")),
            available=Count("id", filter=Q(status="AVAILABLE")),
        )
        total_beds = bed_stats["total"] or 0
        occupied_beds = bed_stats["occupied"] or 0
        available_beds = bed_stats["available"] or 0
        active_students = Student.objects.filter(hostel=hostel, status="ACTIVE").count()
        pending_complaints = Complaint.objects.filter(hostel=hostel, status__in=["OPEN", "IN_PROGRESS"]).count()
        pending_admissions = AdmissionRequest.objects.filter(hostel=hostel, status="PENDING").count()
        today_entries = EntryExitLog.objects.filter(hostel=hostel, event_at__date=today).count()
        pending_leave_requests = LeaveRequest.objects.filter(hostel=hostel, status="PENDING").count()

        return Response({
            "total_residents": active_students,
            "today_collection": today_collection,
            "month_collection": month_collection,
            "this_month": this_month,
            "total_due_this_month": total_due,
            "due_students_this_month": due_count,
            "pending_complaints": pending_complaints,
            "pending_admissions": pending_admissions,
            "today_entries": today_entries,
            "pending_leave_requests": pending_leave_requests,
            "beds": {
                "total": total_beds,
                "occupied": occupied_beds,
                "available": available_beds,
                "occupancy_percent": round((occupied_beds / total_beds) * 100, 2) if total_beds else 0,
            }
        })
