# Graph Report - .  (2026-06-03)

## Corpus Check
- Corpus is ~37,575 words - fits in a single context window. You may not need a graph.

## Summary
- 1139 nodes · 2602 edges · 174 communities (133 shown, 41 thin omitted)
- Extraction: 76% EXTRACTED · 24% INFERRED · 0% AMBIGUOUS · INFERRED: 619 edges (avg confidence: 0.51)
- Token cost: 32,722 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Billing & Invoicing (Backend)|Billing & Invoicing (Backend)]]
- [[_COMMUNITY_Frontend Protected Pages|Frontend Protected Pages]]
- [[_COMMUNITY_Frontend API Client & Login|Frontend API Client & Login]]
- [[_COMMUNITY_Exports & Dashboard (Backend)|Exports & Dashboard (Backend)]]
- [[_COMMUNITY_Accounts & Auth (Backend)|Accounts & Auth (Backend)]]
- [[_COMMUNITY_Django App Configs|Django App Configs]]
- [[_COMMUNITY_Frontend Local Store|Frontend Local Store]]
- [[_COMMUNITY_Rooms & Beds (Backend)|Rooms & Beds (Backend)]]
- [[_COMMUNITY_Tenants & Subscriptions (Frontend)|Tenants & Subscriptions (Frontend)]]
- [[_COMMUNITY_Complaints (Backend)|Complaints (Backend)]]
- [[_COMMUNITY_Hostel Beds & Rooms (Backend)|Hostel Beds & Rooms (Backend)]]
- [[_COMMUNITY_Backups (Frontend)|Backups (Frontend)]]
- [[_COMMUNITY_Frontend Dependencies|Frontend Dependencies]]
- [[_COMMUNITY_Gate Operations (Backend)|Gate Operations (Backend)]]
- [[_COMMUNITY_Payments & Receipts (Backend)|Payments & Receipts (Backend)]]
- [[_COMMUNITY_Fees & Ledger (Backend)|Fees & Ledger (Backend)]]
- [[_COMMUNITY_Admissions (Backend)|Admissions (Backend)]]
- [[_COMMUNITY_Student Docs & Complaints (Frontend)|Student Docs & Complaints (Frontend)]]
- [[_COMMUNITY_Backups (Backend)|Backups (Backend)]]
- [[_COMMUNITY_Gate Operations (Frontend)|Gate Operations (Frontend)]]
- [[_COMMUNITY_Project Stack & Dependencies|Project Stack & Dependencies]]
- [[_COMMUNITY_TypeScript Config|TypeScript Config]]
- [[_COMMUNITY_Tenants & Plans (Backend)|Tenants & Plans (Backend)]]
- [[_COMMUNITY_Beds & Rooms (Frontend)|Beds & Rooms (Frontend)]]
- [[_COMMUNITY_Payments (Frontend)|Payments (Frontend)]]
- [[_COMMUNITY_Students (Backend)|Students (Backend)]]
- [[_COMMUNITY_Audit Log (Backend)|Audit Log (Backend)]]
- [[_COMMUNITY_Students (Frontend)|Students (Frontend)]]
- [[_COMMUNITY_Owner Dashboard (Frontend)|Owner Dashboard (Frontend)]]
- [[_COMMUNITY_Residents & Attendance (Frontend)|Residents & Attendance (Frontend)]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 112|Community 112]]
- [[_COMMUNITY_Community 113|Community 113]]
- [[_COMMUNITY_Community 114|Community 114]]
- [[_COMMUNITY_Community 138|Community 138]]
- [[_COMMUNITY_Community 144|Community 144]]
- [[_COMMUNITY_Community 149|Community 149]]
- [[_COMMUNITY_Community 172|Community 172]]
- [[_COMMUNITY_Community 173|Community 173]]

## God Nodes (most connected - your core abstractions)
1. `HasHostelContext` - 43 edges
2. `apiFetch()` - 38 edges
3. `Button()` - 28 edges
4. `loadState()` - 27 edges
5. `IsStaffOrReadOnly` - 26 edges
6. `TimeStampedModel` - 23 edges
7. `HostelScopedModel` - 23 edges
8. `IsOwnerOrManager` - 23 edges
9. `Topbar()` - 23 edges
10. `IsStaff` - 22 edges

## Surprising Connections (you probably didn't know these)
- `Hostel Frontend (Next.js)` --shares_data_with--> `Hostel Backend (Django)`  [INFERRED]
  frontend/README.md → backend/requirements.txt
- `BackupViewSet` --uses--> `UserHostel`  [INFERRED]
  backend/apps/backups/views.py → backend/apps/accounts/models.py
- `Meta` --uses--> `AdmissionRequest`  [INFERRED]
  backend/apps/admissions/serializers.py → backend/apps/admissions/models.py
- `AdmissionRequestViewSet` --uses--> `HasHostelContext`  [INFERRED]
  backend/apps/admissions/views.py → backend/apps/common/permissions.py
- `AdmissionRequestViewSet` --uses--> `IsStaffOrReadOnly`  [INFERRED]
  backend/apps/admissions/views.py → backend/apps/common/permissions.py

## Import Cycles
- 1-file cycle: `frontend/src/features/students/components/StudentDuesCard.tsx -> frontend/src/features/students/components/StudentDuesCard.tsx`
- 1-file cycle: `frontend/src/features/students/components/StudentPayments.tsx -> frontend/src/features/students/components/StudentPayments.tsx`

## Hyperedges (group relationships)
- **Async Task Queue Stack** — backend_project, requirements_celery, requirements_redis [INFERRED 0.75]
- **Django REST API Stack** — requirements_django, requirements_djangorestframework, requirements_djangorestframework_simplejwt, requirements_drf_spectacular [INFERRED 0.75]
- **Monthly Due PDF Report Flow** — monthlydue_report, requirements_weasyprint, monthlydue_pdf_rendering [INFERRED 0.75]
- **Next.js Template Boilerplate Assets** — file_file_icon, globe_globe_icon, next_nextjs_logo, vercel_vercel_logo, window_window_icon [INFERRED 0.95]

## Communities (174 total, 41 thin omitted)

### Community 0 - "Billing & Invoicing (Backend)"
Cohesion: 0.05
Nodes (42): Attendance, Meta, AttendanceSerializer, Meta, AttendanceViewSet, Invoice, LedgerEntry, Meta (+34 more)

### Community 1 - "Frontend Protected Pages"
Cohesion: 0.14
Nodes (26): categories, ExpensesPage(), FeePlan, Bed, Expense, Room, getRole(), isAuthed() (+18 more)

### Community 2 - "Frontend API Client & Login"
Cohesion: 0.08
Nodes (17): API_BASE, apiDownload(), ApiOptions, ApiResult, apiUrl(), buildHeaders(), QueryParams, refreshAccess() (+9 more)

### Community 3 - "Exports & Dashboard (Backend)"
Cohesion: 0.11
Nodes (21): APIView, str, BasePermission, HasHostelContext, IsOwnerOrManager, month_key(), parse_month_key(), OwnerDashboardView (+13 more)

### Community 4 - "Accounts & Auth (Backend)"
Cohesion: 0.17
Nodes (22): AbstractUser, Meta, User, UserHostel, MeSerializer, Meta, PasswordResetConfirmSerializer, PasswordResetRequestSerializer (+14 more)

### Community 5 - "Django App Configs"
Cohesion: 0.05
Nodes (21): AccountsConfig, AdmissionsConfig, AppConfig, AttendanceConfig, AuditlogConfig, BackupsConfig, BillingConfig, CommonConfig (+13 more)

### Community 6 - "Frontend Local Store"
Cohesion: 0.14
Nodes (36): addBed(), addExpense(), addPayment(), addRoom(), addStudent(), assignBed(), DEFAULT_STATE, deleteExpense() (+28 more)

### Community 7 - "Rooms & Beds (Backend)"
Cohesion: 0.28
Nodes (21): HostelScopedModel, IsStaffOrReadOnly, Bed, BedAssignment, Block, Floor, Meta, Room (+13 more)

### Community 8 - "Tenants & Subscriptions (Frontend)"
Cohesion: 0.16
Nodes (14): request(), tenantsApi, HostelForm(), HostelList(), PlanList(), SubscriptionForm(), SubscriptionList(), Hostel (+6 more)

### Community 9 - "Complaints (Backend)"
Cohesion: 0.22
Nodes (15): HostelMemberCanCreateStaffCanEdit, Allows any authenticated hostel user to view/create self-service records,     wh, Complaint, ComplaintAttachment, ComplaintComment, Meta, ComplaintAttachmentSerializer, ComplaintCommentCreateSerializer (+7 more)

### Community 10 - "Hostel Beds & Rooms (Backend)"
Cohesion: 0.16
Nodes (14): Bed, Meta, Room, BedCreateUpdateSerializer, BedSerializer, Meta, Create/update bed safely inside a hostel (tenant).     Hostel is assigned serve, Create/update room safely inside a hostel (tenant).     Hostel is assigned serv (+6 more)

### Community 11 - "Backups (Frontend)"
Cohesion: 0.13
Nodes (18): createSnapshot(), downloadBackup(), listBackups(), restoreBackup(), scheduleNow(), BackupSettingsPage(), Button(), cn() (+10 more)

### Community 12 - "Frontend Dependencies"
Cohesion: 0.07
Nodes (26): dependencies, axios, jwt-decode, next, react, react-dom, devDependencies, autoprefixer (+18 more)

### Community 13 - "Gate Operations (Backend)"
Cohesion: 0.27
Nodes (14): EntryExitLog, LeaveRequest, Meta, VisitorLog, EntryExitLogSerializer, LeaveDecisionSerializer, LeaveRequestSerializer, Meta (+6 more)

### Community 14 - "Payments & Receipts (Backend)"
Cohesion: 0.25
Nodes (16): FeeLedger, Payment, PaymentAllocation, Receipt, Meta, PaymentAllocationSerializer, PaymentCreateSerializer, PaymentSerializer (+8 more)

### Community 15 - "Fees & Ledger (Backend)"
Cohesion: 0.30
Nodes (16): str, FeeLedger, FeePlan, Meta, StudentFeePlan, FeeLedgerSerializer, FeePlanSerializer, Meta (+8 more)

### Community 16 - "Admissions (Backend)"
Cohesion: 0.19
Nodes (8): AdmissionRequest, Meta, AdmissionDecisionSerializer, AdmissionRequestSerializer, approve_admission(), Meta, AdmissionRequestViewSet, PublicAdmissionRequestViewSet

### Community 17 - "Student Docs & Complaints (Frontend)"
Cohesion: 0.15
Nodes (11): api, uploadDocument(), createComplaint(), listComplaints(), setComplaintStatus(), Complaint, ComplaintPriority, ComplaintStatus (+3 more)

### Community 18 - "Backups (Backend)"
Cohesion: 0.19
Nodes (10): BackupSnapshot, Meta, BackupSnapshotSerializer, Meta, _dump_hostel(), scheduled_backup_for_hostel(), _values(), BackupViewSet (+2 more)

### Community 19 - "Gate Operations (Frontend)"
Cohesion: 0.19
Nodes (13): getStudents(), approveLeave(), checkoutVisitor(), createEntryExit(), createLeaveRequest(), createVisitor(), listEntryExit(), listLeaveRequests() (+5 more)

### Community 20 - "Project Stack & Dependencies"
Cohesion: 0.12
Nodes (20): Hostel Backend (Django), create-next-app, next/font + Geist, Next.js, Hostel Frontend (Next.js), Vercel Platform, PDF Report Rendering via WeasyPrint, Monthly Due Report Template (+12 more)

### Community 21 - "TypeScript Config"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 22 - "Tenants & Plans (Backend)"
Cohesion: 0.34
Nodes (12): HostelAdmin, generate_hostel_code(), Hostel, Plan, Subscription, HostelSerializer, Meta, PlanSerializer (+4 more)

### Community 23 - "Beds & Rooms (Frontend)"
Cohesion: 0.27
Nodes (14): apiFetch(), createBed(), createBlock(), createFloor(), createRoom(), getBlocks(), getFloors(), getRooms() (+6 more)

### Community 24 - "Payments (Frontend)"
Cohesion: 0.19
Nodes (13): createPayment(), getPayments(), getPaymentsByStudent(), getStudentDuesSummary(), PaymentListParams, StudentPaymentForm(), to2(), Payment (+5 more)

### Community 25 - "Students (Backend)"
Cohesion: 0.30
Nodes (8): Student, StudentDocument, Meta, StudentDocumentSerializer, StudentSerializer, HostelScopedViewSet, StudentDocumentViewSet, StudentViewSet

### Community 26 - "Audit Log (Backend)"
Cohesion: 0.20
Nodes (9): AuditLogMiddleware, Action, AuditEvent, AuditLog, Meta, AuditEventSerializer, Meta, AuditEventViewSet (+1 more)

### Community 27 - "Students (Frontend)"
Cohesion: 0.15
Nodes (7): checkoutStudent(), createStudent(), getStudent(), getStudentTimeline(), StudentListParams, transferStudentBed(), StudentFormState

### Community 28 - "Owner Dashboard (Frontend)"
Cohesion: 0.23
Nodes (9): BedsPage(), formatMoney(), OwnerDashboardCards(), getOwnerDashboard(), DashboardPage(), OwnerDashboardResponse, computeDues(), occupancy() (+1 more)

### Community 29 - "Residents & Attendance (Frontend)"
Cohesion: 0.24
Nodes (6): Attendance, createResident(), listResidents(), Resident, ResidentStatus, Stay

### Community 30 - "Community 30"
Cohesion: 0.22
Nodes (6): authApi, AuthUser, SignupPayload, SignupResponse, Input(), Props

### Community 31 - "Community 31"
Cohesion: 0.17
Nodes (5): getActiveAssignments(), DuesSummary, computeDues(), DuesSummary, sum2()

### Community 32 - "Community 32"
Cohesion: 0.19
Nodes (8): getBillingSummary(), listDues(), BillingPayment, BillingSummary, Invoice, LedgerEntry, MonthlyDue, VacateRequest

### Community 33 - "Community 33"
Cohesion: 0.28
Nodes (6): Meta, Notice, Meta, NoticeSerializer, models_q_expires(), NoticeViewSet

### Community 34 - "Community 34"
Cohesion: 0.21
Nodes (5): createBedAssignment(), endBedAssignment(), getActiveAssignmentByBed(), getActiveAssignmentByStudent(), updateStudentPartial()

### Community 35 - "Community 35"
Cohesion: 0.29
Nodes (7): generateMonth(), getLedgers(), getStudentLedgers(), FeeLedger, LedgerStatus, computeDues(), sumDecimalStrings()

### Community 36 - "Community 36"
Cohesion: 0.36
Nodes (6): approveAdmission(), createAdmission(), listAdmissions(), rejectAdmission(), AdmissionRequest, AdmissionStatus

### Community 38 - "Community 38"
Cohesion: 0.46
Nodes (4): createNotice(), listNotices(), updateNotice(), Notice

### Community 40 - "Community 40"
Cohesion: 0.83
Nodes (3): downloadCSV(), downloadJSON(), downloadText()

## Knowledge Gaps
- **139 isolated node(s):** `Migration`, `Migration`, `Meta`, `Migration`, `Meta` (+134 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **41 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TimeStampedModel` connect `Billing & Invoicing (Backend)` to `Accounts & Auth (Backend)`, `Rooms & Beds (Backend)`, `Hostel Beds & Rooms (Backend)`, `Backups (Backend)`, `Tenants & Plans (Backend)`, `Audit Log (Backend)`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `HostelScopedModel` connect `Rooms & Beds (Backend)` to `Billing & Invoicing (Backend)`, `Community 33`, `Complaints (Backend)`, `Gate Operations (Backend)`, `Payments & Receipts (Backend)`, `Fees & Ledger (Backend)`, `Admissions (Backend)`, `Students (Backend)`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Why does `HasHostelContext` connect `Exports & Dashboard (Backend)` to `Billing & Invoicing (Backend)`, `Community 33`, `Rooms & Beds (Backend)`, `Complaints (Backend)`, `Gate Operations (Backend)`, `Payments & Receipts (Backend)`, `Fees & Ledger (Backend)`, `Admissions (Backend)`, `Students (Backend)`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 40 inferred relationships involving `HasHostelContext` (e.g. with `AdmissionRequestViewSet` and `PublicAdmissionRequestViewSet`) actually correct?**
  _`HasHostelContext` has 40 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `apiFetch()` (e.g. with `createBed()` and `createBedAssignment()`) actually correct?**
  _`apiFetch()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `IsStaffOrReadOnly` (e.g. with `AdmissionRequestViewSet` and `PublicAdmissionRequestViewSet`) actually correct?**
  _`IsStaffOrReadOnly` has 23 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Migration`, `Migration`, `Meta` to the rest of the system?**
  _150 weakly-connected nodes found - possible documentation gaps or missing edges._