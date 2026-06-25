from rest_framework import serializers
from .models import User, UserHostel
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.tenants.models import Hostel  # adjust import path


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

class SignupSerializer(serializers.ModelSerializer):
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
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
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
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        return _run_password_validators(value)
