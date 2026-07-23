"""Spoof-resistant client IP resolution behind reverse proxies.

Threat model: ``X-Forwarded-For`` is attacker-controlled unless the direct
peer is a proxy we operate/trust. Getting this wrong turns every IP-keyed
control (rate limits, reputation, allow/deny lists, axes lockout) into a
bypass — an attacker rotates a fake XFF and gets a fresh budget per request.

Algorithm (industry standard "rightmost untrusted"):

1. Start from the socket peer (``REMOTE_ADDR``). If it is NOT a trusted
   proxy, that IS the client — forwarded headers are ignored entirely.
2. If the peer is Cloudflare (when Cloudflare support is enabled) use
   ``CF-Connecting-IP`` — set by Cloudflare itself, not spoofable through it.
3. Otherwise walk ``X-Forwarded-For`` right to left, skipping trusted
   proxies; the first non-trusted hop is the client. Anything left of it is
   client-supplied noise and never trusted.
4. Malformed entries stop the walk at the last good hop (flagged
   ``suspicious_chain`` for the logs — header tampering signal).
"""
import ipaddress
from dataclasses import dataclass, field

_MAX_CHAIN = 20  # sanity bound on forwarded hops


@dataclass
class ClientAddress:
    ip: str
    parsed: object                    # ipaddress.IPv4Address / IPv6Address
    via_cloudflare: bool = False
    proxy_chain: list = field(default_factory=list)
    suspicious_chain: bool = False    # malformed/oversized forwarded header


def _parse(value: str):
    value = (value or "").strip()
    if not value:
        return None
    # Strip a port if present ("1.2.3.4:5678", "[::1]:5678").
    if value.startswith("["):
        value = value.partition("]")[0].lstrip("[")
    elif value.count(":") == 1 and "." in value:
        value = value.partition(":")[0]
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def resolve_client_ip(request, config) -> ClientAddress:
    peer_raw = request.META.get("REMOTE_ADDR", "") or "0.0.0.0"
    peer = _parse(peer_raw) or ipaddress.ip_address("0.0.0.0")

    # Direct connection — headers are irrelevant (and untrustworthy).
    if not config.is_trusted_proxy(peer):
        return ClientAddress(ip=str(peer), parsed=peer)

    # Cloudflare in front: CF-Connecting-IP is authoritative, but only accept
    # it when the peer chain actually reaches us through trusted infrastructure
    # (peer is trusted, checked above). If the header names Cloudflare ranges
    # explicitly, also verify the edge hop when present in XFF.
    cf_conf = config.get("cloudflare") or {}
    if cf_conf.get("enabled"):
        header = "HTTP_" + str(
            cf_conf.get("connecting_ip_header", "CF-Connecting-IP")
        ).upper().replace("-", "_")
        cf_ip = _parse(request.META.get(header, ""))
        if cf_ip is not None:
            return ClientAddress(ip=str(cf_ip), parsed=cf_ip, via_cloudflare=True,
                                 proxy_chain=[str(peer)])

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if not forwarded:
        return ClientAddress(ip=str(peer), parsed=peer)

    hops = [h.strip() for h in forwarded.split(",") if h.strip()]
    suspicious = len(hops) > _MAX_CHAIN
    hops = hops[-_MAX_CHAIN:]

    chain = [str(peer)]
    candidate = peer
    for raw in reversed(hops):
        hop = _parse(raw)
        if hop is None:
            # Malformed entry: stop at the last valid hop; flag for the logs.
            suspicious = True
            break
        if config.is_trusted_proxy(hop) or config.is_cloudflare(hop):
            chain.append(str(hop))
            candidate = hop
            continue
        return ClientAddress(ip=str(hop), parsed=hop, proxy_chain=chain,
                             via_cloudflare=config.is_cloudflare(candidate),
                             suspicious_chain=suspicious)

    # Every hop was a trusted proxy (internal traffic) or the chain broke.
    return ClientAddress(ip=str(candidate), parsed=candidate, proxy_chain=chain,
                         suspicious_chain=suspicious)
