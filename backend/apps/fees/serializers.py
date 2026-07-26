from apps.common.serializers import HostelScopedSerializer
from .models import FeePlan, StudentFeePlan, FeeLedger

class FeePlanSerializer(HostelScopedSerializer):
    class Meta:
        model = FeePlan
        fields = "__all__"

class StudentFeePlanSerializer(HostelScopedSerializer):
    class Meta:
        model = StudentFeePlan
        fields = "__all__"

class FeeLedgerSerializer(HostelScopedSerializer):
    class Meta:
        model = FeeLedger
        fields = "__all__"