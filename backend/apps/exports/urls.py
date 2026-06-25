from django.urls import path
from .views import (
    ExportAttendanceLeaveCSV,
    ExportComplaintPerformanceCSV,
    ExportDuePaymentsCSV,
    ExportEntryExitCSV,
    ExportFeeCollectionCSV,
    ExportInvoicesExcel,
    ExportLedgerExcel,
    ExportOccupancyCSV,
    ExportResidentsExcel,
    ExportVisitorLogCSV,
)

urlpatterns = [
    path("residents.csv", ExportResidentsExcel.as_view()),
    path("invoices.csv", ExportInvoicesExcel.as_view()),
    path("ledger.csv", ExportLedgerExcel.as_view()),
    path("occupancy.csv", ExportOccupancyCSV.as_view()),
    path("dues.csv", ExportDuePaymentsCSV.as_view()),
    path("collections.csv", ExportFeeCollectionCSV.as_view()),
    path("complaints.csv", ExportComplaintPerformanceCSV.as_view()),
    path("attendance-leave.csv", ExportAttendanceLeaveCSV.as_view()),
    path("visitors.csv", ExportVisitorLogCSV.as_view()),
    path("entry-exit.csv", ExportEntryExitCSV.as_view()),
]
