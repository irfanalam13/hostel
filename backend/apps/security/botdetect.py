"""User-agent based bot classification.

First-line, cheap detection: substring classification of the User-Agent
against three configurable lists (allowed / blocked / suspicious). Real
headless-browser fingerprinting and JS challenges are Cloudflare's job
(Super Bot Fight Mode / Managed Challenge) — this layer catches the long
tail of naive automation that talks to the origin directly and provides the
signal feed for IP reputation.

Categories -> configured actions (allow | log | block); the global/section
monitor mode downgrades block to log automatically in the middleware.
"""
from dataclasses import dataclass

CATEGORY_ALLOWED = "allowed"        # verified good bots / monitors
CATEGORY_BLOCKED = "blocked"        # attack tools & scanners
CATEGORY_SUSPICIOUS = "suspicious"  # generic automation (curl, headless, ...)
CATEGORY_EMPTY = "empty"            # no User-Agent at all
CATEGORY_UNKNOWN = "unknown"        # looks like a normal client


@dataclass
class BotVerdict:
    category: str
    action: str          # allow | log | block
    matched: str = ""    # which pattern fired (for the event log)


def classify(user_agent: str, config) -> BotVerdict:
    conf = config.get("bots") or {}
    if not conf.get("enabled", True):
        return BotVerdict(CATEGORY_UNKNOWN, "allow")

    ua = (user_agent or "").strip().lower()
    if not ua:
        return BotVerdict(CATEGORY_EMPTY, str(conf.get("empty_user_agent_action", "log")))

    for pattern in conf.get("allowed_agents") or []:
        if pattern and pattern.lower() in ua:
            return BotVerdict(CATEGORY_ALLOWED, "allow", pattern)

    for pattern in conf.get("blocked_agents") or []:
        if pattern and pattern.lower() in ua:
            return BotVerdict(CATEGORY_BLOCKED, str(conf.get("blocked_action", "block")), pattern)

    for pattern in conf.get("suspicious_agents") or []:
        if pattern and pattern.lower() in ua:
            return BotVerdict(
                CATEGORY_SUSPICIOUS, str(conf.get("suspicious_action", "log")), pattern
            )

    return BotVerdict(CATEGORY_UNKNOWN, "allow")
