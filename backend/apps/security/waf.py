"""Application-layer WAF (request-line hygiene).

Inspects the METHOD, PATH and QUERY STRING — the parts of a request that are
cheap to scan on every hit and where injection/scanner noise concentrates.
Request *bodies* are intentionally NOT scanned here: JSON payloads routinely
contain SQL-looking prose (notes, descriptions) and body inspection belongs
at the Cloudflare WAF / input-validation layers; doing it here would add
latency and false positives to every write.

Rule groups (individually switchable, hot-reloadable):

    path_traversal, sql_injection, xss, remote_code_execution,
    file_inclusion, scanner_probes

Patterns are tuned for low false positives on a JSON API (they anchor on
syntax that never appears in legitimate REST paths/queries). Every hit is
logged with the rule id; in ``monitor`` mode nothing is blocked — soak the
rules, then flip ``waf.mode`` to enforce at runtime.
"""
import re
from dataclasses import dataclass
from urllib.parse import unquote

# rule_id -> compiled pattern, matched against "<path>?<query>" (URL-decoded
# once; a second decode round catches %25-double-encoding tricks).
_PATTERNS: dict[str, list[re.Pattern]] = {
    "path_traversal": [
        re.compile(r"\.\./|\.\.\\|%2e%2e", re.I),
        re.compile(r"/etc/(passwd|shadow|hosts)|c:\\windows", re.I),
    ],
    "sql_injection": [
        re.compile(r"(?i)\bunion\b[\s+/*]+(all[\s+/*]+)?\bselect\b"),
        re.compile(r"(?i)\b(sleep|benchmark|pg_sleep|waitfor)\s*\("),
        re.compile(r"(?i)\binformation_schema\b|\bload_file\s*\(|\binto\s+(out|dump)file\b"),
        re.compile(r"(?i)('|%27)\s*(or|and)\s+[\w'\"]+\s*=\s*[\w'\"]+(\s*--|\s*#|;)?"),
    ],
    "xss": [
        re.compile(r"(?i)<\s*script[\s>/]|<\s*/\s*script\s*>"),
        re.compile(r"(?i)\bjavascript\s*:"),
        re.compile(r"(?i)\bon(error|load|click|mouseover|focus)\s*="),
        re.compile(r"(?i)<\s*(img|svg|iframe|object|embed)[^>]*\bon\w+\s*="),
    ],
    "remote_code_execution": [
        re.compile(r"(?i)[;|`]\s*(wget|curl|bash|sh|nc|ncat|python|perl)\b"),
        re.compile(r"\$\(|\$\{(?!\w+\})|`[^`]+`"),
        re.compile(r"(?i)\b(eval|exec|system|passthru|shell_exec|popen)\s*\("),
    ],
    "file_inclusion": [
        re.compile(r"(?i)\b(php|zip|phar|expect|data|glob)://"),
        re.compile(r"(?i)\bfile://(?!localhost/)"),
    ],
    "scanner_probes": [
        re.compile(
            r"(?i)^/(\.env|\.git|\.aws|\.ssh|\.svn|\.DS_Store|wp-admin|wp-login|"
            r"wp-content|xmlrpc\.php|phpmyadmin|pma|adminer|config\.php|"
            r"vendor/phpunit|cgi-bin|actuator|server-status|\.vscode|\.idea|"
            r"id_rsa|backup\.(sql|zip|tar))"
        ),
        re.compile(r"(?i)\.(php[3-8]?|asp|aspx|jsp|cgi)(\?|$)"),
    ],
}


@dataclass
class Violation:
    rule: str
    detail: str


def inspect(request, config) -> list[Violation]:
    """All WAF violations for this request (empty list = clean)."""
    conf = config.get("waf") or {}
    if not conf.get("enabled", True):
        return []

    violations: list[Violation] = []

    method = (request.method or "").upper()
    allowed_methods = conf.get("allowed_methods") or []
    if allowed_methods and method not in allowed_methods:
        violations.append(Violation("method_not_allowed", method))

    path = request.path or ""
    query = request.META.get("QUERY_STRING", "") or ""

    if len(path) > int(conf.get("max_path_length", 2048)):
        violations.append(Violation("oversized_path", f"len={len(path)}"))
    if len(query) > int(conf.get("max_query_length", 4096)):
        violations.append(Violation("oversized_query", f"len={len(query)}"))

    target = f"{path}?{unquote(query)}" if query else path
    # Second decode pass defeats double-encoding (%252e%252e -> %2e%2e -> ..).
    try:
        decoded_twice = unquote(target)
    except Exception:  # pathological input — inspect the raw form
        decoded_twice = target

    rules = conf.get("rules") or {}
    for rule_id, patterns in _PATTERNS.items():
        if not rules.get(rule_id, True):
            continue
        for pattern in patterns:
            match = pattern.search(target) or pattern.search(decoded_twice)
            if match:
                violations.append(Violation(rule_id, match.group(0)[:120]))
                break  # one hit per rule group is enough

    return violations
