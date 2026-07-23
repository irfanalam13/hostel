"""Security report generation (daily / weekly / monthly / custom).

Builds a structured report from the threat aggregation + reputation state,
with human-readable recommendations derived from what the window actually
shows. Consumed by the Super-Admin API (JSON) and the ``security_report``
management command (JSON / CSV export for compliance archives).
"""
import csv
import io

from . import threat

_PRESETS = {"daily": 24, "weekly": 168, "monthly": 720}


def build(period: str = "daily", window_hours: int | None = None, tenant_id=None) -> dict:
    """Assemble a security report for a preset period or explicit window."""
    hours = window_hours or _PRESETS.get(period, 24)
    data = threat.summary(window_hours=hours, tenant_id=tenant_id)
    data["period"] = period
    data["offenders"] = threat.top_offenders(window_hours=hours, tenant_id=tenant_id)
    data["recommendations"] = _recommendations(data)
    return data


def _recommendations(data: dict) -> list:
    recs = []
    by_type = data.get("by_type", {})
    level = data.get("threat_level")

    if level in ("high", "critical"):
        recs.append(
            f"Threat level is {level.upper()} ({data['threat_events']} defensive "
            "events). Review the top offenders and consider tightening limits or "
            "enabling CAPTCHA/enforce mode."
        )
    if by_type.get("auth_lockout", 0) or by_type.get("auth_failure", 0) > 50:
        recs.append(
            "Elevated authentication failures/lockouts — possible brute-force or "
            "credential-stuffing campaign. Confirm progressive lockout + CAPTCHA "
            "are in enforce mode and review the offending IPs."
        )
    if by_type.get("waf_violation", 0):
        recs.append(
            f"{by_type['waf_violation']} WAF violations — inspect the matched rules; "
            "if false-positive-free, move waf.mode to enforce."
        )
    if by_type.get("bot_detected", 0) > 100:
        recs.append(
            "High automated-traffic volume — consider enabling Cloudflare "
            "Super Bot Fight Mode / Managed Challenge at the edge."
        )
    if data.get("offenders"):
        worst = data["offenders"][0]
        recs.append(
            f"Top offender {worst['ip']} ({worst['blocked']} blocked). Consider a "
            "temporary or permanent IPRule deny if the pattern persists."
        )
    if not recs:
        recs.append("No significant threats in this window. Posture is nominal.")
    return recs


def to_csv(data: dict) -> str:
    """Flatten a report to CSV (compliance/spreadsheet export)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["section", "key", "value"])
    writer.writerow(["meta", "period", data.get("period")])
    writer.writerow(["meta", "window_hours", data.get("window_hours")])
    writer.writerow(["meta", "generated_at", data.get("generated_at")])
    writer.writerow(["summary", "total_events", data.get("total_events")])
    writer.writerow(["summary", "blocked_events", data.get("blocked_events")])
    writer.writerow(["summary", "threat_events", data.get("threat_events")])
    writer.writerow(["summary", "threat_level", data.get("threat_level")])
    for etype, n in (data.get("by_type") or {}).items():
        writer.writerow(["by_type", etype, n])
    for row in data.get("offenders") or []:
        writer.writerow(["offender", row["ip"], row["blocked"]])
    for i, rec in enumerate(data.get("recommendations") or [], 1):
        writer.writerow(["recommendation", str(i), rec])
    return buf.getvalue()
