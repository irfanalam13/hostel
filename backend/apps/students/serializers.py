from apps.common.serializers import HostelScopedSerializer
from .models import Student, StudentDocument

class StudentDocumentSerializer(HostelScopedSerializer):
    class Meta:
        model = StudentDocument
        fields = "__all__"

class StudentSerializer(HostelScopedSerializer):
    documents = StudentDocumentSerializer(many=True, read_only=True)
    class Meta:
        model = Student
        fields = "__all__"