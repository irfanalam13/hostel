import csv
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.billing.models import Invoice, LedgerEntry
from apps.common.permissions import HasHostelContext, IsOwnerOrManager
from apps.residents.models import Resident
from apps.rooms.models import Bed, Room
from apps.fees.models import FeeLedger
from apps.payments.models import Payment as StudentPayment
from apps.attendance.models import Attendance
from apps.complaints.models import Complaint
from apps.operations.models import EntryExitLog, LeaveRequest, VisitorLog


def csv_response(filename, headers, rows):
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(resp)
    writer.writerow(headers)
    writer.writerows(rows)
    return resp


class ExportResidentsExcel(APIView):
    permission_classes = [IsAuthenticated, HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        hostel = request.hostel
        rows = [
            [r.id, r.full_name, r.phone, r.guardian_phone, r.status, str(r.created_at)]
            for r in Resident.objects.filter(hostel=hostel).order_by("-id")
        ]
        return csv_response(
            f"{hostel.code}_residents.csv",
            ["ID", "Name", "Phone", "Guardian", "Status", "Created"],
            rows,
        )


class ExportInvoicesExcel(APIView):
    permission_classes = [IsAuthenticated, HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        hostel = request.hostel
        rows = [
            [inv.id, inv.resident.full_name, str(inv.month), str(inv.amount), str(inv.due_amount), inv.status]
            for inv in Invoice.objects.filter(resident__hostel=hostel).select_related("resident").order_by("-id")
        ]
        return csv_response(
            f"{hostel.code}_invoices.csv",
            ["ID", "Resident", "Month", "Amount", "Due", "Status"],
            rows,
        )


class ExportLedgerExcel(APIView):
    permission_classes = [IsAuthenticated, HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        hostel = request.hostel
        rows = [
            [
                entry.id,
                entry.resident.full_name,
                entry.entry_type,
                str(entry.amount),
                entry.invoice_id or "",
                entry.description,
                str(entry.created_at),
            ]
            for entry in LedgerEntry.objects.filter(resident__hostel=hostel)
            .select_related("resident", "invoice")
            .order_by("-id")
        ]
        return csv_response(
            f"{hostel.code}_ledger.csv",
            ["ID", "Resident", "Type", "Amount", "Invoice", "Description", "Created"],
            rows,
        )


class ExportOccupancyCSV(APIView):
    permission_classes = [IsAuthenticated, HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        hostel = request.hostel
        rooms = Room.objects.filter(hostel=hostel).prefetch_related("beds").order_by("room_no")
        rows = []
        for room in rooms:
            beds = list(room.beds.all())
            total = len(beds)
            occupied = sum(1 for bed in beds if bed.status == "OCCUPIED")
            maintenance = sum(1 for bed in beds if bed.status == "MAINTENANCE")
            available = max(0, total - occupied - maintenance)
            rows.append([room.room_no, room.floor, total, occupied, available, maintenance])
        return csv_response(
            f"{hostel.code}_occupancy.csv",
            ["Room", "Floor", "Total Beds", "Occupied", "Available", "Maintenance"],
            rows,
        )


class ExportDuePaymentsCSV(APIView):
    permission_classes = [IsAuthenticated, HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        hostel = request.hostel
        rows = [
            [ledger.id, ledger.student.full_name, ledger.month, str(ledger.net_due), ledger.status]
            for ledger in FeeLedger.objects.filter(hostel=hostel)
            .exclude(status="PAID")
            .select_related("student")
            .order_by("month", "student__full_name")
        ]
        return csv_response(
            f"{hostel.code}_dues.csv",
            ["ID", "Student", "Month", "Due", "Status"],
            rows,
        )


class ExportFeeCollectionCSV(APIView):
    permission_classes = [IsAuthenticated, HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        hostel = request.hostel
        rows = [
            [payment.id, payment.student.full_name, str(payment.amount), payment.date, payment.method, payment.reference_no]
            for payment in StudentPayment.objects.filter(hostel=hostel)
            .select_related("student")
            .order_by("-date")
        ]
        return csv_response(
            f"{hostel.code}_collections.csv",
            ["ID", "Student", "Amount", "Date", "Method", "Reference"],
            rows,
        )


class ExportComplaintPerformanceCSV(APIView):
    permission_classes = [IsAuthenticated, HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        hostel = request.hostel
        rows = [
            [
                complaint.id,
                complaint.title,
                complaint.category,
                complaint.priority,
                complaint.status,
                complaint.assigned_to.username if complaint.assigned_to else "",
                complaint.created_at,
                complaint.resolved_at or "",
            ]
            for complaint in Complaint.objects.filter(hostel=hostel)
            .select_related("assigned_to")
            .order_by("-created_at")
        ]
        return csv_response(
            f"{hostel.code}_complaints.csv",
            ["ID", "Title", "Category", "Priority", "Status", "Assigned To", "Created", "Resolved"],
            rows,
        )


class ExportAttendanceLeaveCSV(APIView):
    permission_classes = [IsAuthenticated, HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        hostel = request.hostel
        rows = [
            ["attendance", item.id, item.resident.full_name, item.date, item.status, item.note]
            for item in Attendance.objects.filter(hostel=hostel).select_related("resident").order_by("-date")
        ]
        rows.extend(
            [
                ["leave", item.id, item.resident.full_name if item.resident else item.student.full_name, item.start_date, item.status, item.reason]
                for item in LeaveRequest.objects.filter(hostel=hostel)
                .select_related("resident", "student")
                .order_by("-start_date")
            ]
        )
        return csv_response(
            f"{hostel.code}_attendance_leave.csv",
            ["Type", "ID", "Person", "Date", "Status", "Note"],
            rows,
        )


class ExportVisitorLogCSV(APIView):
    permission_classes = [IsAuthenticated, HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        hostel = request.hostel
        rows = [
            [
                item.id,
                item.visitor_name,
                item.visitor_phone,
                item.resident.full_name if item.resident else item.student.full_name if item.student else "",
                item.purpose,
                item.check_in_at,
                item.check_out_at or "",
            ]
            for item in VisitorLog.objects.filter(hostel=hostel)
            .select_related("resident", "student")
            .order_by("-check_in_at")
        ]
        return csv_response(
            f"{hostel.code}_visitors.csv",
            ["ID", "Visitor", "Phone", "Resident", "Purpose", "Check In", "Check Out"],
            rows,
        )


class ExportEntryExitCSV(APIView):
    permission_classes = [IsAuthenticated, HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        hostel = request.hostel
        rows = [
            [
                item.id,
                item.resident.full_name if item.resident else item.student.full_name if item.student else "",
                item.direction,
                item.event_at,
                item.purpose,
                item.note,
            ]
            for item in EntryExitLog.objects.filter(hostel=hostel)
            .select_related("resident", "student")
            .order_by("-event_at")
        ]
        return csv_response(
            f"{hostel.code}_entry_exit.csv",
            ["ID", "Person", "Direction", "Time", "Purpose", "Note"],
            rows,
        )
