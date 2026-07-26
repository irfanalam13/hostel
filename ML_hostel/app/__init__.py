"""ML_hostel — the AI service for the Hostel Management SaaS.

All AI/LLM/agent logic lives here, isolated from the Django monolith. The
service is stateless: it authenticates each request with a short-lived context
token minted by Django (apps.assistant), and reaches business data only through
Django's own APIs, so multi-tenancy and RBAC are enforced by the platform, not
re-implemented here.
"""
