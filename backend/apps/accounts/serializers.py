from rest_framework import serializers
from .models import User, UserHostel, SignupOTP
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.tenants.models import HOSTEL_CODE_RE
from apps.auditlog.models import AuditEvent


def _run_password_validators(value, user=None):
    try:
        validate_password(value, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages))
    return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id","username","email","first_name","last_name","role"]

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    class Meta:
        model = User
        fields = ["id","username","email","password","role","first_name","last_name"]

    def validate_password(self, value):
        return _run_password_validators(value)

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user




User = get_user_model()

class SignupOTPRequestSerializer(serializers.Serializer):
    """Step 1 of signup: request a verification code for an email address."""
    email = serializers.EmailField(required=True)


class SignupSerializer(serializers.ModelSerializer):
    # Email is required and must be verified via an OTP sent in step 1.
    email = serializers.EmailField(required=True, allow_blank=False)
    otp = serializers.CharField(write_only=True, min_length=6, max_length=6)

    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    hostel_name = serializers.CharField(write_only=True, max_length=120)
    # Permanent workspace username (subdomain). Optional — auto-generated from
    # the hostel name when omitted; validated + uniqueness-checked when given.
    workspace_username = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=63
    )
    hostel_phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    hostel_address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    owner_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "otp",
            "password",
            "password2",
            "hostel_name",
            "workspace_username",
            "hostel_phone",
            "hostel_address",
            "owner_name",
        )

    def validate_workspace_username(self, value):
        if not value:
            return ""
        from apps.tenants.services import is_workspace_username_available
        from apps.tenants.validators import clean_workspace_username

        try:
            value = clean_workspace_username(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        if not is_workspace_username_available(value):
            raise serializers.ValidationError("This workspace username is already taken.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        _run_password_validators(attrs["password"])

        # Email must have been verified via the OTP sent in step 1.
        otp_obj = (
            SignupOTP.objects.filter(
                email__iexact=attrs["email"], otp=attrs["otp"], is_used=False
            )
            .order_by("-created_at")
            .first()
        )
        if not otp_obj or not otp_obj.is_valid():
            raise serializers.ValidationError(
                {"otp": "Invalid or expired verification code. Request a new one."}
            )
        # Stash for create() to consume (mark used) once the account is built.
        self._signup_otp = otp_obj
        return attrs

    def create(self, validated_data):
        """Create owner + workspace atomically.

        The whole signup — user, tenant, workspace username, membership link,
        default settings, audit trail, OTP burn — is one transaction: if any
        step fails nothing is left behind (no orphan users or hostels).
        """
        from django.db import transaction

        from apps.tenants.services import provision_workspace

        validated_data.pop("password2")
        validated_data.pop("otp", None)
        password = validated_data.pop("password")

        hostel_name = validated_data.pop("hostel_name")
        workspace_username = validated_data.pop("workspace_username", "")
        hostel_phone = validated_data.pop("hostel_phone", "")
        hostel_address = validated_data.pop("hostel_address", "")
        owner_name = validated_data.pop("owner_name", "")

        with transaction.atomic():
            # ✅ Create OWNER user
            user = User(**validated_data)
            user.role = "OWNER"
            user.set_password(password)
            user.save()

            # ✅ Provision the workspace (tenant + slug + membership link +
            # default settings/config + audit log) — all inside this transaction.
            hostel = provision_workspace(
                owner=user,
                hostel_name=hostel_name,
                workspace_username=workspace_username or None,
                phone=hostel_phone,
                address=hostel_address,
                owner_name=owner_name or user.username,
            )

            # ✅ Burn the verification code so it can't be replayed for another signup
            otp_obj = getattr(self, "_signup_otp", None)
            if otp_obj is not None:
                otp_obj.is_used = True
                otp_obj.save(update_fields=["is_used"])
            SignupOTP.objects.filter(email__iexact=user.email, is_used=False).update(is_used=True)

        # attach hostel for response
        user._created_hostel = hostel
        return user
    
    
    
class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_staff",
            "is_active",
            "date_joined",
            "last_login",
            # Drives the frontend first-login forced-password-change gate.
            "must_change_password",
        )
        read_only_fields = fields


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Self-service profile edit — the signed-in user changes their own
    display name and email. Username and role are intentionally NOT editable
    here (role changes are an owner-only administrative action)."""

    email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def validate_email(self, value):
        if not value:
            return value
        qs = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This email is already in use.")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Authenticated password change: prove knowledge of the current password,
    then set a validated new one."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Your current password is incorrect.")
        return value

    def validate_new_password(self, value):
        return _run_password_validators(value, user=self.context["request"].user)

    def validate(self, attrs):
        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from your current password."}
            )
        return attrs

class ActivityEventSerializer(serializers.ModelSerializer):
    """Read-only view of the signed-in user's own audit trail — powers the
    account Activity timeline. Deliberately whitelists a safe field subset (no
    hostel/branch ids, no actor FK) since it's always scoped to `request.user`."""

    class Meta:
        model = AuditEvent
        fields = ("id", "action", "message", "ip_address", "user_agent", "created_at", "meta")
        read_only_fields = fields


class UserHostelSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserHostel
        fields = ["id", "user", "hostel", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("username"):
            raise serializers.ValidationError("Provide email or username.")
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    email_or_username = serializers.CharField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        return _run_password_validators(value)


class ForgotHostelIDSerializer(serializers.Serializer):
    email_or_username = serializers.CharField(required=True)


class SecureLoginSerializer(serializers.Serializer):
    # Optional when the request already carries workspace context (subdomain /
    # X-Workspace): the resolved tenant IS the login scope. Required on the
    # root domain (legacy Hostel-ID flow).
    hostel_id = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    username = serializers.CharField(required=True, trim_whitespace=True)
    password = serializers.CharField(required=True, write_only=True, trim_whitespace=False)
    # Which login surface this attempt came from; the account's role must be
    # admitted by that portal (see apps.common.rbac.PORTALS).
    portal = serializers.ChoiceField(
        choices=["admin", "staff", "student", "parent"], required=False, allow_blank=True
    )
    # Longer refresh-token lifetime (fewer re-logins); access stays short-lived.
    remember = serializers.BooleanField(required=False, default=False)

    default_error_messages = {
        "invalid_login": "Invalid Hostel ID, email, or password.",
    }

    def validate(self, attrs):
        hostel_id = (attrs.get("hostel_id") or "").strip().upper()
        if hostel_id and not HOSTEL_CODE_RE.match(hostel_id):
            raise serializers.ValidationError({"detail": self.error_messages["invalid_login"]})
        attrs["hostel_id"] = hostel_id
        return attrs

