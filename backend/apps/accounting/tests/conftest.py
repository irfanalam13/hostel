"""Accounting test fixtures.

The ``accounting`` feature is default-disabled in the catalog (enterprise
gating), so API tests must enable it for the workspace under test — mirroring a
plan that includes accounting.
"""
import pytest


@pytest.fixture(autouse=True)
def enable_accounting(db, hostel):
    """Grant the ``accounting`` feature to the primary test hostel via an
    entitlement override (the catalog default is off)."""
    from apps.subscriptions.models import Feature, FeatureOverride

    feature = Feature.objects.filter(key="accounting").first()
    if feature is not None:
        FeatureOverride.objects.get_or_create(
            hostel=hostel, feature=feature, defaults={"is_enabled": True}
        )
    yield
