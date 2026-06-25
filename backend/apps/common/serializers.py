from rest_framework import serializers


class HostelScopedSerializer(serializers.ModelSerializer):
    """ModelSerializer for tenant-scoped models.

    The ``hostel`` foreign key is injected server-side from the request
    (``serializer.save(hostel=request.hostel)``), never supplied by the client.
    With ``fields = "__all__"`` DRF would otherwise treat that non-null FK as a
    *required* input and reject every create with ``{"hostel": ["This field is
    required."]}``. Forcing it read-only fixes that and also prevents a client
    from attempting to set/spoof another tenant's id.

    Safe to use as a drop-in base for serializers whose model has no ``hostel``
    field — the override is a no-op in that case.
    """

    def get_fields(self):
        fields = super().get_fields()
        hostel_field = fields.get("hostel")
        if hostel_field is not None:
            hostel_field.read_only = True
            hostel_field.required = False
        return fields
