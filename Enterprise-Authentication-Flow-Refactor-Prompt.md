
# Enterprise Authentication Flow Refactor Prompt

## Objective

Analyze the **entire existing MyHostel Cloud Platform codebase** before making any modifications. Do **not** rewrite or replace the authentication system from scratch. Instead, understand the current architecture, identify inconsistencies, and refactor the authentication flow to follow a clean enterprise multi-tenant SaaS architecture while preserving all existing functionality.

---

# Primary Goal

The project already contains an authentication, authorization, tenant, RBAC, subscription, and permission system.

Your task is to:

- Analyze the complete backend and frontend.
- Understand the current authentication flow.
- Identify duplicate or conflicting login flows.
- Identify multiple user entry points.
- Identify inconsistent redirects.
- Identify authentication gaps.
- Preserve all working features.
- Refactor only where necessary.
- Never break existing APIs.
- Never remove existing enterprise functionality.

The final result should feel like one cohesive authentication platform rather than multiple authentication systems stitched together.

---

# Phase 1 — Codebase Discovery

Before changing anything, inspect the complete project.

Understand:

- Authentication architecture
- User model
- Tenant model
- Membership model
- Roles
- Permissions
- Session management
- JWT flow
- Refresh tokens
- Authentication middleware
- Tenant middleware
- RBAC implementation
- Feature flags
- Subscription enforcement
- Dashboard routing
- Navigation guards
- API permissions
- Frontend route guards
- Login pages
- Signup flow
- Password reset
- Email verification
- Invitation flow
- User onboarding
- Workspace switching
- Super Admin portal
- Owner portal
- Tenant portal

Do not begin implementation until the current flow is fully understood.

---

# Phase 2 — Authentication Audit

Produce an internal audit of the existing implementation.

Identify:

- Duplicate authentication logic
- Duplicate login pages
- Multiple authentication providers
- Inconsistent redirects
- Missing tenant validation
- Missing permission checks
- Missing role checks
- Broken authorization flow
- Dead authentication code
- Unused middleware
- Legacy authentication code
- Duplicate session handling
- Incorrect dashboard routing
- Cross-tenant security risks
- Authentication performance bottlenecks

Refactor instead of replacing whenever possible.

---

# Phase 3 — Preserve Existing Features

The following features must continue working exactly as before:

- JWT Authentication
- Refresh Tokens
- Remember Me
- Logout
- Password Reset
- Email Verification
- Invitation Acceptance
- Tenant Isolation
- Role-Based Access
- Permission Checks
- Feature Flags
- Subscription Checks
- API Authentication
- Mobile Compatibility
- Audit Logs
- Session Tracking
- Activity Logging
- Notifications
- Existing API contracts

No regressions are acceptable.

---

# Phase 4 — Platform Authentication

The platform website (myhostel.com) should become responsible only for platform-level operations.

Allowed functionality:

- Landing Page
- Pricing
- Features
- Documentation
- Contact
- Demo
- Owner Login
- Create Hostel
- Trial Registration

Do not expose tenant user authentication here.

Do not expose student login.

Do not expose staff login.

Do not expose parent login.

Do not expose receptionist login.

---

# Phase 5 — Signup Flow

Refactor the signup flow without breaking existing provisioning.

The platform should:

- Validate owner information
- Validate organization name
- Validate subdomain availability
- Validate business email
- Create tenant
- Create owner account
- Assign Owner role
- Generate default permissions
- Generate default departments
- Generate default subscription
- Generate trial
- Generate tenant configuration
- Generate default settings
- Generate audit logs
- Send verification emails
- Redirect into the newly created tenant workspace

Reuse existing services whenever possible.

Do not duplicate provisioning logic.

---

# Phase 6 — Owner Login Flow

Platform login should authenticate only organization owners.

Flow:

Owner Loginl

↓

Authenticate

↓

Load owned organizations

↓

If exactly one organization

↓

Redirect directly to

tenant.myhostel.com/dashboard

If multiple organizations

↓

Display organization selector

↓

Redirect to selected workspace

Do not leave owners inside the platform website.

---

# Phase 7 — Tenant Authentication

Each tenant workspace should become completely self-contained.

Example:

tenant.myhostel.com/login

This login page must authenticate:

- Owner
- Hostel Admin
- Staff
- Receptionist
- Accountant
- Parent
- Student
- Security
- Laundry
- Maintenance

No role-specific login pages should exist.

Authentication determines identity.

Authorization determines access.

---

# Phase 8 — Authentication Pipeline

Standardize the complete authentication lifecycle.

Authentication

↓

User

↓

Tenant Resolution

↓

Membership Validation

↓

Role Loading

↓

Permission Loading

↓

Subscription Validation

↓

Feature Flag Evaluation

↓

Session Creation

↓

Navigation Generation

↓

Dashboard Routing

This flow should be implemented consistently across backend and frontend.

---

# Phase 9 — Authorization

Review every protected endpoint.

Every endpoint should verify:

Authenticated User

↓

Tenant Membership

↓

Role

↓

Permission

↓

Subscription

↓

Feature Enabled

↓

Business Rule

Never rely solely on frontend authorization.

---

# Phase 10 — Frontend Refactor

Audit the frontend authentication implementation.

Standardize:

- Route Guards
- Middleware
- Session Provider
- Authentication Context
- Tenant Context
- Workspace Context
- Permission Hooks
- Sidebar Generation
- Menu Visibility
- Dashboard Routing
- Unauthorized Screens
- Redirect Logic

Remove duplicated authentication logic while preserving functionality.

---

# Phase 11 — Workspace Routing

Standardize routing.

Platform

myhostel.com

↓

Owner Login

↓

Workspace Resolution

↓

tenant.myhostel.com

↓

Tenant Authentication

↓

Dashboard

Every authenticated request must know:

Current Tenant

Current Membership

Current Role

Current Permissions

Current Subscription

Current Feature Flags

---

# Phase 12 — Security Review

Review and strengthen:

- Session Security
- Token Rotation
- Cookie Security
- CSRF
- CORS
- Refresh Logic
- Login Rate Limiting
- MFA Readiness
- Password Policies
- Secure Headers
- Device Tracking
- Audit Logs
- Suspicious Login Detection

Improve existing implementations rather than replacing them.

---

# Phase 13 — Refactoring Rules

Follow these mandatory rules:

- Analyze before modifying.
- Prefer refactoring over rewriting.
- Reuse existing services.
- Reuse existing APIs.
- Preserve backward compatibility.
- Avoid duplicate implementations.
- Remove redundant authentication logic only after confirming it is unused.
- Keep code modular.
- Keep architecture scalable.
- Maintain enterprise coding standards.
- Do not introduce breaking database changes unless absolutely required.
- Preserve existing tests whenever possible.
- Update or add tests only where behavior changes.

---

# Expected Deliverable

Deliver a unified, enterprise-grade authentication system that:

- Uses a single platform onboarding flow.
- Uses isolated tenant authentication.
- Preserves existing enterprise RBAC.
- Preserves tenant isolation.
- Preserves subscriptions and feature flags.
- Eliminates duplicate login flows.
- Standardizes redirects and session handling.
- Simplifies future maintenance.
- Remains fully backward compatible.
- Is production-ready, secure, modular, scalable, and suitable for a large multi-tenant SaaS platform.
