from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import UserHostel
from apps.admissions.models import AdmissionRequest
from apps.complaints.models import Complaint
from apps.fees.models import FeeLedger, FeePlan, StudentFeePlan
from apps.notices.models import Notice
from apps.operations.models import EntryExitLog, LeaveRequest, VisitorLog
from apps.payments.models import Payment
from apps.rooms.models import Bed, BedAssignment, Block, Floor, Room
from apps.students.models import Student
from apps.tenants.models import Hostel


class Command(BaseCommand):
    help = "Seed a complete demo hostel with rooms, beds, students, fees, notices, and operations data."

    def handle(self, *args, **options):
        User = get_user_model()
        admin, created_user = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@example.com", "role": "ADMIN", "is_staff": True, "is_superuser": True},
        )
        if created_user:
            admin.set_password("admin12345")
            admin.save()

        hostel, _ = Hostel.objects.get_or_create(
            code="H-DEMO",
            defaults={
                "name": "Hostel Demo",
                "address": "Kathmandu, Nepal",
                "phone": "9800000000",
                "owner_name": "Demo Admin",
            },
        )
        UserHostel.objects.get_or_create(user=admin, hostel=hostel, defaults={"is_active": True})

        block, _ = Block.objects.get_or_create(hostel=hostel, name="A Block", defaults={"code": "A"})
        floor, _ = Floor.objects.get_or_create(hostel=hostel, block=block, name="First Floor", defaults={"number": 1})

        rooms = []
        for room_no in ("101", "102", "103"):
            room, _ = Room.objects.get_or_create(
                hostel=hostel,
                room_no=room_no,
                defaults={
                    "block": block,
                    "floor_ref": floor,
                    "floor": "1",
                    "capacity": 4,
                    "rent": Decimal("8000.00"),
                    "room_type": "Standard",
                    "amenities": ["wifi", "fan", "study_table"],
                },
            )
            rooms.append(room)
            for bed_no in ("A", "B", "C", "D"):
                Bed.objects.get_or_create(hostel=hostel, room=room, bed_no=bed_no, defaults={"status": "AVAILABLE"})

        students = []
        today = timezone.localdate()
        for idx, name in enumerate(("Aarav Sharma", "Nisha Thapa", "Bikash Rai"), start=1):
            student, _ = Student.objects.get_or_create(
                hostel=hostel,
                phone=f"98000000{idx}",
                defaults={
                    "full_name": name,
                    "address": "Kathmandu",
                    "guardian_name": "Guardian",
                    "guardian_phone": f"98100000{idx}",
                    "join_date": today,
                    "status": "ACTIVE",
                },
            )
            students.append(student)

        available_beds = list(Bed.objects.filter(hostel=hostel, status="AVAILABLE").order_by("room__room_no", "bed_no")[: len(students)])
        for student, bed in zip(students, available_beds):
            assignment, created_assignment = BedAssignment.objects.get_or_create(
                hostel=hostel,
                student=student,
                is_active=True,
                defaults={"bed": bed, "start_date": today},
            )
            if created_assignment:
                assignment.bed.status = "OCCUPIED"
                assignment.bed.save(update_fields=["status", "updated_at"])

        fee_plan, _ = FeePlan.objects.get_or_create(
            hostel=hostel,
            name="Monthly Rent",
            defaults={"monthly_amount": Decimal("8000.00"), "includes_wifi": True, "is_active": True},
        )
        month = today.strftime("%Y-%m")
        for student in students:
            StudentFeePlan.objects.get_or_create(hostel=hostel, student=student, fee_plan=fee_plan, start_month=month)
            ledger, _ = FeeLedger.objects.get_or_create(
                hostel=hostel,
                student=student,
                month=month,
                defaults={
                    "amount": Decimal("8000.00"),
                    "discount": Decimal("0.00"),
                    "fine": Decimal("0.00"),
                    "net_due": Decimal("8000.00"),
                    "status": "DUE",
                },
            )
            if student == students[0] and not Payment.objects.filter(hostel=hostel, student=student, date=today).exists():
                Payment.objects.create(hostel=hostel, student=student, amount=Decimal("5000.00"), date=today, method="CASH")
                ledger.status = "PARTIAL"
                ledger.net_due = Decimal("3000.00")
                ledger.save(update_fields=["status", "net_due", "updated_at"])

        AdmissionRequest.objects.get_or_create(
            hostel=hostel,
            phone="9822222222",
            defaults={
                "full_name": "Pending Applicant",
                "guardian_name": "Applicant Guardian",
                "guardian_phone": "9822222223",
                "preferred_join_date": today,
                "status": "PENDING",
                "source": "INTERNAL",
            },
        )
        Notice.objects.get_or_create(
            hostel=hostel,
            title="Monthly fee reminder",
            defaults={"body": "Please clear monthly hostel fees before the 10th.", "is_pinned": True, "created_by": admin},
        )
        Complaint.objects.get_or_create(
            hostel=hostel,
            student=students[0],
            title="WiFi issue in room 101",
            defaults={"category": "Maintenance", "priority": "HIGH", "status": "OPEN", "created_by": admin},
        )
        LeaveRequest.objects.get_or_create(
            hostel=hostel,
            student=students[1],
            start_date=today,
            end_date=today,
            defaults={"reason": "Family visit", "status": "PENDING"},
        )
        VisitorLog.objects.get_or_create(
            hostel=hostel,
            student=students[0],
            visitor_name="Ramesh Sharma",
            check_out_at=None,
            defaults={"visitor_phone": "9840000000", "relation": "Father", "purpose": "Visit", "recorded_by": admin},
        )
        EntryExitLog.objects.get_or_create(
            hostel=hostel,
            student=students[2],
            direction="OUT",
            event_at__date=today,
            defaults={"purpose": "College", "recorded_by": admin},
        )

        self.stdout.write(self.style.SUCCESS("Demo data ready. Login: admin / admin12345, Hostel Code: H-DEMO"))
