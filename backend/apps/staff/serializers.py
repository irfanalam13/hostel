"""Staff Management serializers.

Relational fields (role / department / designation / reporting manager) are
constrained to the request's workspace at construction time so a payload can
never reference another tenant's rows.
"""
from rest_framework import serializers

from .models import Department, Designation, Role, StaffDocument, StaffProfile


class _HostelScopedRelationsMixin:
    """Restrict the querysets of listed relational fields to ``request.hostel``.

    ``scoped_relations`` maps a serializer field name to the model it points at;
    each is a hostel-scoped model, so the queryset is filtered accordingly.
    """

    scoped_relations: dict = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        hostel = getattr(request, "hostel", None)
        for field_name, model in self.scoped_relations.items():
            field = self.fields.get(field_name)
            if field is not None and hostel is not None:
                field.queryset = model.objects.filter(hostel=hostel)


class RoleSerializer(serializers.ModelSerializer):
    staff_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id", "name", "slug", "description", "permissions",
            "is_system", "is_active", "staff_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "is_system", "staff_count", "created_at", "updated_at"]

    def get_staff_count(self, obj) -> int:
        # Annotated in the viewset queryset; fall back to a count if absent.
        count = getattr(obj, "staff_count", None)
        return count if count is not None else obj.staff.count()

    def validate_permissions(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise serializers.ValidationError("Expected a list of permission strings.")
        return value


class DepartmentSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"head": StaffProfile}
    staff_count = serializers.SerializerMethodField()
    head_name = serializers.CharField(source="head.full_name", read_only=True, default=None)

    class Meta:
        model = Department
        fields = [
            "id", "name", "code", "description", "head", "head_name",
            "is_active", "staff_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "staff_count", "head_name", "created_at", "updated_at"]

    def get_staff_count(self, obj) -> int:
        count = getattr(obj, "staff_count", None)
        return count if count is not None else obj.staff.count()


class DesignationSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"department": Department}
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = Designation
        fields = [
            "id", "title", "department", "department_name", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "department_name", "created_at", "updated_at"]


class StaffDocumentSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"staff": StaffProfile}
    doc_type_display = serializers.CharField(source="get_doc_type_display", read_only=True)

    class Meta:
        model = StaffDocument
        fields = [
            "id", "staff", "doc_type", "doc_type_display", "title", "file",
            "expiry_date", "uploaded_by", "created_at",
        ]
        read_only_fields = ["id", "doc_type_display", "uploaded_by", "created_at"]


# Profile fields the client may write (create + update). Account identity
# (username/email/role) and lifecycle status are handled separately.
_PROFILE_WRITABLE = [
    "first_name", "middle_name", "last_name", "photo", "gender", "date_of_birth",
    "nationality", "citizenship_number", "passport_number", "marital_status",
    "phone", "emergency_contact_name", "emergency_contact_phone",
    "country", "province", "district", "city", "ward", "street", "postal_code",
    "role", "department", "designation", "reporting_manager", "joining_date",
    "employment_type", "work_location", "shift", "salary_type", "basic_salary",
    "allowances", "tax_percentage", "payment_method", "bank_name",
    "bank_account", "pan_number", "notes",
]


class StaffProfileSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    """Read + update representation. Nested account/role/department names are
    denormalized for the directory and profile screens."""

    scoped_relations = {
        "role": Role,
        "department": Department,
        "designation": Designation,
        "reporting_manager": StaffProfile,
    }

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    account_role = serializers.CharField(source="user.role", read_only=True)
    account_active = serializers.BooleanField(source="user.is_active", read_only=True)
    last_login = serializers.DateTimeField(source="user.last_login", read_only=True)
    full_name = serializers.CharField(read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True, default=None)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    designation_title = serializers.CharField(source="designation.title", read_only=True, default=None)
    reporting_manager_name = serializers.CharField(
        source="reporting_manager.full_name", read_only=True, default=None
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    documents = StaffDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = StaffProfile
        fields = [
            "id", "employee_id", "user", "username", "email", "account_role",
            "account_active", "last_login", "full_name",
            "status", "status_display", "must_change_password",
            "role_name", "department_name", "designation_title",
            "reporting_manager_name", "documents",
            *_PROFILE_WRITABLE,
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "employee_id", "user", "status", "must_change_password",
            "created_at", "updated_at",
        ]


class StaffCreateSerializer(StaffProfileSerializer):
    """Create payload: profile fields plus the login-account identity. The
    account is provisioned with a one-time temporary password by the service."""

    username = serializers.CharField(required=False, allow_blank=True, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True, write_only=True)
    account_role = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta(StaffProfileSerializer.Meta):
        # Same fields; username/email/account_role are redefined above as
        # writable. `user` is assigned by the service, not the client.
        read_only_fields = [
            "id", "employee_id", "user", "status", "must_change_password",
            "created_at", "updated_at",
        ]
