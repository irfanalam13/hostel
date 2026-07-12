"""Workspace-username validation rules (pure — no DB)."""
import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from apps.tenants.validators import (
    clean_workspace_username,
    normalize_workspace_username,
    reserved_workspace_names,
    validate_workspace_username,
)


# --- Normalization -----------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("  everest  ", "everest"),
    ("Everest", "everest"),
    ("EVEREST-123", "everest-123"),
    ("", ""),
    (None, ""),
])
def test_normalize(raw, expected):
    assert normalize_workspace_username(raw) == expected


# --- Valid usernames ---------------------------------------------------------
@pytest.mark.parametrize("value", [
    "everest", "everest123", "everest-hostel", "ktm-hostel", "abc", "a2c",
    "e" * 32,
])
def test_valid_usernames(value):
    assert clean_workspace_username(value) == value


# --- Invalid usernames -------------------------------------------------------
@pytest.mark.parametrize("value,code", [
    ("", "required"),
    ("ab", "too_short"),
    ("e" * 33, "too_long"),
    ("everest hostel", "invalid"),   # space
    ("everest@", "invalid"),         # symbol
    ("everest_hostel", "invalid"),   # underscore
    ("-everest", "invalid"),         # leading hyphen
    ("everest-", "invalid"),         # trailing hyphen
    ("éverest", "invalid"),          # unicode
    ("admin", "reserved"),
    ("api", "reserved"),
    ("www", "reserved"),
    ("mail", "reserved"),
])
def test_invalid_usernames(value, code):
    with pytest.raises(ValidationError) as exc:
        clean_workspace_username(value)
    assert exc.value.code == code


def test_uppercase_is_normalized_not_rejected():
    # "Everest" is invalid as-is but clean() normalizes first.
    assert clean_workspace_username("Everest") == "everest"
    # validate() alone (no normalize) rejects it.
    with pytest.raises(ValidationError):
        validate_workspace_username("Everest")


# --- Configurability ---------------------------------------------------------
@override_settings(RESERVED_WORKSPACE_NAMES=["mycustomname"])
def test_reserved_list_is_extendable_via_settings():
    assert "mycustomname" in reserved_workspace_names()
    with pytest.raises(ValidationError) as exc:
        clean_workspace_username("mycustomname")
    assert exc.value.code == "reserved"
    # Built-ins can never be un-reserved.
    assert "admin" in reserved_workspace_names()


@override_settings(WORKSPACE_USERNAME_MIN_LENGTH=5, WORKSPACE_USERNAME_MAX_LENGTH=10)
def test_length_limits_configurable():
    with pytest.raises(ValidationError):
        clean_workspace_username("abcd")  # < 5
    with pytest.raises(ValidationError):
        clean_workspace_username("abcdefghijk")  # > 10
    assert clean_workspace_username("abcde") == "abcde"


@override_settings(WORKSPACE_USERNAME_MAX_LENGTH=500)
def test_max_length_capped_at_dns_label_limit():
    with pytest.raises(ValidationError) as exc:
        clean_workspace_username("a" * 64)
    assert exc.value.code == "too_long"
