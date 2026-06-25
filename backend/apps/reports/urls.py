from django.urls import path
from .views import MonthlyDueReportView

urlpatterns = [
    path("monthly-due/", MonthlyDueReportView.as_view()),
]