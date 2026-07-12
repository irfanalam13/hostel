from django.urls import path

from .views import (
    DomainActivateView,
    DomainDeleteView,
    DomainDisableView,
    DomainListView,
    DomainPrimaryView,
    DomainSslView,
    DomainVerifyView,
)

urlpatterns = [
    path("", DomainListView.as_view(), name="domains"),
    path("<uuid:domain_id>/verify/", DomainVerifyView.as_view(), name="domain_verify"),
    path("<uuid:domain_id>/activate/", DomainActivateView.as_view(), name="domain_activate"),
    path("<uuid:domain_id>/primary/", DomainPrimaryView.as_view(), name="domain_primary"),
    path("<uuid:domain_id>/disable/", DomainDisableView.as_view(), name="domain_disable"),
    path("<uuid:domain_id>/ssl/", DomainSslView.as_view(), name="domain_ssl"),
    path("<uuid:domain_id>/", DomainDeleteView.as_view(), name="domain_delete"),
]
