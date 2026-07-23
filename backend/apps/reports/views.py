import datetime as dt
from django.template.loader import render_to_string
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.common.permissions import HasHostelContext, IsOwnerOrManager
from apps.common.utils import month_key
from apps.fees.models import FeeLedger

class MonthlyDueReportView(APIView):
    permission_classes = [HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        hostel = request.hostel
        month = request.query_params.get("month") or month_key(dt.date.today())
        rows = FeeLedger.objects.filter(hostel=hostel, month=month).select_related("student").order_by("student__full_name")

        html = render_to_string("reports/monthly_due.html", {"hostel": hostel, "month": month, "rows": rows})

        # Return HTML now (easy MVP). Later you can convert to PDF.
        return Response({"month": month, "html": html})