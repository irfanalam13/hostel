# apps/hostel/serializers.py
from rest_framework import serializers
from .models import Room, Bed


class BedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bed
        fields = ["id", "room", "label", "created_at"]
        read_only_fields = ["id", "created_at"]


class BedCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Create/update bed safely inside a hostel (tenant).
    Hostel is assigned server-side.
    """
    class Meta:
        model = Bed
        fields = ["id", "room", "label", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_room(self, room: Room):
        hostel = getattr(self.context["request"], "hostel", None)
        if not hostel:
            raise serializers.ValidationError("Hostel context missing. Provide X-HOSTEL-CODE.")
        if room.hostel_id != hostel.id:
            raise serializers.ValidationError("Room does not belong to this hostel.")
        return room

    def create(self, validated_data):
        request = self.context["request"]
        hostel = getattr(request, "hostel", None)
        if not hostel:
            raise serializers.ValidationError("Hostel context missing. Provide X-HOSTEL-CODE.")
        # Ensure bed.hostel is always correct
        validated_data["hostel"] = hostel
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Prevent hostel switching
        validated_data.pop("hostel", None)
        return super().update(instance, validated_data)


class RoomSerializer(serializers.ModelSerializer):
    beds = BedSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = ["id", "number", "floor", "notes", "beds", "created_at"]
        read_only_fields = ["id", "created_at"]


class RoomCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Create/update room safely inside a hostel (tenant).
    Hostel is assigned server-side.
    """
    class Meta:
        model = Room
        fields = ["id", "number", "floor", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        hostel = getattr(request, "hostel", None)
        if not hostel:
            raise serializers.ValidationError("Hostel context missing. Provide X-HOSTEL-CODE.")
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        hostel = getattr(request, "hostel", None)
        if not hostel:
            raise serializers.ValidationError("Hostel context missing. Provide X-HOSTEL-CODE.")
        validated_data["hostel"] = hostel
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Prevent hostel switching
        validated_data.pop("hostel", None)
        return super().update(instance, validated_data)