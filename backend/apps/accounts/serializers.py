from rest_framework import serializers
from .models import User, UserHostel, SignupOTP
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.tenants.models import Hostel, HOSTEL_CODE_RE


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
            "hostel_phone",
            "hostel_address",
            "owner_name",
        )

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
        validated_data.pop("password2")
        validated_data.pop("otp", None)
        password = validated_data.pop("password")

        hostel_name = validated_data.pop("hostel_name")
        hostel_phone = validated_data.pop("hostel_phone", "")
        hostel_address = validated_data.pop("hostel_address", "")
        owner_name = validated_data.pop("owner_name", "")

        # ✅ Create OWNER user
        user = User(**validated_data)
        user.role = "OWNER"
        user.set_password(password)
        user.save()

        # ✅ Create Hostel (code auto-generates on save)
        hostel = Hostel.objects.create(
            name=hostel_name,
            phone=hostel_phone,
            address=hostel_address,
            owner_name=owner_name or user.username,
        )

        # ✅ Link user to hostel
        UserHostel.objects.create(user=user, hostel=hostel, is_active=True)

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
        fields = ("id", "username", "email", "first_name", "last_name", "role", "is_staff", "is_active")

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
    hostel_id = serializers.CharField(required=True, trim_whitespace=True)
    username = serializers.CharField(required=True, trim_whitespace=True)
    password = serializers.CharField(required=True, write_only=True, trim_whitespace=False)

    default_error_messages = {
        "invalid_login": "Invalid Hostel ID, email, or password.",
    }

    def validate(self, attrs):
        attrs["hostel_id"] = attrs["hostel_id"].strip().upper()
        if not HOSTEL_CODE_RE.match(attrs["hostel_id"]):
            raise serializers.ValidationError({"detail": self.error_messages["invalid_login"]})
        return attrs

