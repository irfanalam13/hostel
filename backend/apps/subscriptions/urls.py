from django.urls import path

from .views import (
    AvailablePlansView,
    EntitlementsView,
    UpgradeOptionsView,
)

app_name = "subscriptions"

urlpatterns = [
    path("entitlements/", EntitlementsView.as_view(), name="entitlements"),
    path("plans/", AvailablePlansView.as_view(), name="available-plans"),
    path("upgrade-options/", UpgradeOptionsView.as_view(), name="upgrade-options"),
]
