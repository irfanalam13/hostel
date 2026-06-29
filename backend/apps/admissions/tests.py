import pytest
from django.utils import timezone
from apps.rooms.models import Room, Bed, BedAssignment
from apps.admissions.models import AdmissionRequest, AdmissionDocument
from apps.students.models import Student, StudentDocument
from apps.accounts.models import User, UserHostel

ADMISSIONS_URL = "/api/admissions/requests/"
PUBLIC_ADMISSIONS_URL = "/api/admissions/public-requests/"


@pytest.fixture
def rooms_bed(db, hostel):
    room = Room.objects.create(hostel=hostel, room_no="101", capacity=2)
    return Bed.objects.create(room=room, bed_no="A", status="AVAILABLE")


@pytest.fixture
def pending_request(db, hostel, rooms_bed):
    return AdmissionRequest.objects.create(
        hostel=hostel,
        application_number="ADM-2026-000001",
        full_name="JOHN DOE",
        phone="9801234567",
        date_of_birth=timezone.localdate() - timezone.timedelta(days=7300),  # 20 years old
        district="Kathmandu",
        educational_institute="ABC College",
        current_level="BACHELOR",
        preferred_bed=rooms_bed,
        status="PENDING",
    )


@pytest.mark.django_db
def test_create_admission_request(auth_client, warden, hostel, rooms_bed):
    client = auth_client(warden, hostel)
    payload = {
        "full_name": "jane doe",  # Will be capitalized by serializer
        "phone": "9812345678",
        "date_of_birth": "2000-01-01",
        "district": "Lalitpur",
        "educational_institute": "XYZ School",
        "current_level": "PLUS2",
        "father_name": "Father Doe",
        "preferred_bed": str(rooms_bed.id),
    }
    
    resp = client.post(ADMISSIONS_URL, payload)
    assert resp.status_code == 201
    assert resp.data["full_name"] == "JANE DOE"
    assert resp.data["application_number"].startswith("ADM-2026-")
    assert resp.data["status"] == "PENDING"
    assert float(resp.data["application_fee"]) == 500.00


@pytest.mark.django_db
def test_duplicate_phone_validation(auth_client, warden, hostel, pending_request):
    client = auth_client(warden, hostel)
    payload = {
        "full_name": "ANOTHER NAME",
        "phone": pending_request.phone,  # Duplicate
        "date_of_birth": "2000-01-01",
        "district": "Lalitpur",
        "educational_institute": "XYZ School",
        "current_level": "PLUS2",
        "father_name": "Father Doe",
    }
    resp = client.post(ADMISSIONS_URL, payload)
    assert resp.status_code == 400
    assert "phone" in resp.data


@pytest.mark.django_db
def test_age_validation(auth_client, warden, hostel):
    client = auth_client(warden, hostel)
    payload = {
        "full_name": "YOUNG CHILD",
        "phone": "9811122233",
        "date_of_birth": str(timezone.localdate() - timezone.timedelta(days=365)),  # 1 year old
        "district": "Lalitpur",
        "educational_institute": "XYZ School",
        "current_level": "SEE",
        "father_name": "Father Doe",
    }
    resp = client.post(ADMISSIONS_URL, payload)
    assert resp.status_code == 400
    assert "date_of_birth" in resp.data


@pytest.mark.django_db
def test_guardian_validation_missing(auth_client, warden, hostel):
    client = auth_client(warden, hostel)
    payload = {
        "full_name": "NO PARENTS",
        "phone": "9811122233",
        "date_of_birth": "2002-02-02",
        "district": "Lalitpur",
        "educational_institute": "XYZ School",
        "current_level": "SEE",
        # Missing father_name, mother_name, spouse_name
    }
    resp = client.post(ADMISSIONS_URL, payload)
    assert resp.status_code == 400
    assert "non_field_errors" in resp.data or "father_name" in resp.data


@pytest.mark.django_db
def test_approve_admission_workflow(auth_client, warden, hostel, pending_request, rooms_bed):
    client = auth_client(warden, hostel)
    
    # Upload a mock document first
    AdmissionDocument.objects.create(
        hostel=hostel,
        admission_request=pending_request,
        doc_type="citizenship_front",
        file="admissions/docs/test_doc.png"
    )

    payload = {
        "bed": str(rooms_bed.id),
        "join_date": "2026-07-01",
        "decision_note": "Approved and assigned bed 101-A.",
        "monthly_fee": "8500.00",
        "security_deposit": "10000.00",
        "admission_fee": "2000.00",
        "payment_status": "PAID",
    }
    
    resp = client.post(f"{ADMISSIONS_URL}{pending_request.id}/approve/", payload)
    assert resp.status_code == 200
    assert resp.data["status"] == "APPROVED"
    assert resp.data["approved_bed"] == str(rooms_bed.id)
    assert resp.data["student"] is not None

    # Check Student was created
    student = Student.objects.get(id=resp.data["student"])
    assert student.full_name == "JOHN DOE"
    assert student.phone == "9801234567"
    assert student.citizenship_number == ""
    
    # Check BedAssignment was created
    assignment = BedAssignment.objects.get(student=student, is_active=True)
    assert assignment.bed == rooms_bed
    
    # Check Bed status changed to OCCUPIED
    rooms_bed.refresh_from_db()
    assert rooms_bed.status == "OCCUPIED"

    # Check User account (role RESIDENT) was created
    username = "std_9801234567"
    user = User.objects.get(username=username)
    assert user.role == "RESIDENT"
    assert UserHostel.objects.filter(user=user, hostel=hostel, is_active=True).exists()

    # Check document copy
    assert StudentDocument.objects.filter(student=student, doc_type="citizenship_front").exists()


@pytest.mark.django_db
def test_reject_admission_workflow(auth_client, warden, hostel, pending_request):
    client = auth_client(warden, hostel)
    payload = {
        "decision_note": "Rejecting this request.",
        "rejection_reason": "Incomplete application details.",
    }
    resp = client.post(f"{ADMISSIONS_URL}{pending_request.id}/reject/", payload)
    assert resp.status_code == 200
    assert resp.data["status"] == "REJECTED"
    assert resp.data["decision_note"] == "Rejecting this request."
    assert resp.data["rejection_reason"] == "Incomplete application details."


@pytest.mark.django_db
def test_bulk_approve_reject(auth_client, warden, hostel, rooms_bed):
    client = auth_client(warden, hostel)
    req1 = AdmissionRequest.objects.create(
        hostel=hostel,
        application_number="ADM-2026-000002",
        full_name="MEMBER ONE",
        phone="9801111111",
        current_level="SEE",
        educational_institute="Inst",
        father_name="F",
        status="PENDING",
    )
    req2 = AdmissionRequest.objects.create(
        hostel=hostel,
        application_number="ADM-2026-000003",
        full_name="MEMBER TWO",
        phone="9802222222",
        current_level="SEE",
        educational_institute="Inst",
        father_name="F",
        status="PENDING",
    )

    # Bulk Approve
    resp = client.post(f"{ADMISSIONS_URL}bulk-approve/", {"ids": [str(req1.id), str(req2.id)]})
    assert resp.status_code == 200
    assert resp.data["approved_count"] == 2

    # Verify requests status
    req1.refresh_from_db()
    req2.refresh_from_db()
    assert req1.status == "APPROVED"
    assert req2.status == "APPROVED"


@pytest.mark.django_db
def test_export_analytics(auth_client, warden, hostel, pending_request):
    client = auth_client(warden, hostel)
    
    # Excel/CSV export
    resp = client.get(f"{ADMISSIONS_URL}export-excel/")
    assert resp.status_code == 200
    assert resp["Content-Disposition"].startswith("attachment; filename=")

    # Analytics
    resp = client.get(f"{ADMISSIONS_URL}analytics/")
    assert resp.status_code == 200
    assert "cards" in resp.data
    assert "charts" in resp.data
    assert resp.data["cards"]["pending"] == 1
