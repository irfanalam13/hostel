"""Spoof-resistance of client IP resolution."""
from django.test import RequestFactory

from apps.security.ip import resolve_client_ip

from .conftest import make_config

rf = RequestFactory()

TRUSTED = {"trusted_proxies": ["10.0.0.0/8", "127.0.0.0/8"]}


def test_direct_connection_ignores_forwarded_header():
    # An attacker connecting directly cannot spoof identity via XFF.
    request = rf.get("/", REMOTE_ADDR="203.0.113.5",
                     HTTP_X_FORWARDED_FOR="198.51.100.99")
    addr = resolve_client_ip(request, make_config(TRUSTED))
    assert addr.ip == "203.0.113.5"


def test_trusted_proxy_yields_forwarded_client():
    request = rf.get("/", REMOTE_ADDR="10.0.0.1",
                     HTTP_X_FORWARDED_FOR="198.51.100.7")
    addr = resolve_client_ip(request, make_config(TRUSTED))
    assert addr.ip == "198.51.100.7"


def test_rightmost_untrusted_wins_over_client_prefix_spoof():
    # Client sent "9.9.9.9" in its own XFF before our proxy appended the real
    # peer — the spoofed left-hand value must never be selected.
    request = rf.get("/", REMOTE_ADDR="10.0.0.1",
                     HTTP_X_FORWARDED_FOR="9.9.9.9, 198.51.100.7, 10.0.0.2")
    addr = resolve_client_ip(request, make_config(TRUSTED))
    assert addr.ip == "198.51.100.7"


def test_malformed_hop_flags_suspicious_and_falls_back():
    request = rf.get("/", REMOTE_ADDR="10.0.0.1",
                     HTTP_X_FORWARDED_FOR="not-an-ip, 10.0.0.2")
    addr = resolve_client_ip(request, make_config(TRUSTED))
    assert addr.suspicious_chain is True
    assert addr.ip == "10.0.0.2"  # last valid trusted hop


def test_port_suffixes_are_stripped():
    request = rf.get("/", REMOTE_ADDR="10.0.0.1",
                     HTTP_X_FORWARDED_FOR="198.51.100.7:4711")
    addr = resolve_client_ip(request, make_config(TRUSTED))
    assert addr.ip == "198.51.100.7"


def test_cloudflare_header_honoured_only_via_trusted_peer():
    config = make_config({**TRUSTED, "cloudflare": {"enabled": True}})
    request = rf.get("/", REMOTE_ADDR="10.0.0.1",
                     HTTP_CF_CONNECTING_IP="198.51.100.9")
    addr = resolve_client_ip(request, config)
    assert addr.ip == "198.51.100.9"
    assert addr.via_cloudflare is True

    # Direct client forging CF-Connecting-IP: ignored (peer not trusted).
    request = rf.get("/", REMOTE_ADDR="203.0.113.5",
                     HTTP_CF_CONNECTING_IP="198.51.100.9")
    addr = resolve_client_ip(request, config)
    assert addr.ip == "203.0.113.5"
    assert addr.via_cloudflare is False


def test_all_trusted_chain_returns_innermost_proxy():
    request = rf.get("/", REMOTE_ADDR="10.0.0.1",
                     HTTP_X_FORWARDED_FOR="10.0.0.3, 10.0.0.2")
    addr = resolve_client_ip(request, make_config(TRUSTED))
    assert addr.ip == "10.0.0.3"
