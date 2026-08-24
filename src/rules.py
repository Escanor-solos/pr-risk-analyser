import re
from dataclasses import dataclass

from .diff_parser import FileDiff


@dataclass
class Finding:
    path: str
    line_hint: str
    rule: str
    message: str
    weight: float


RULES: list[dict] = [
    {
        "name": "secret-added",
        "pattern": re.compile(
            r"(?i)[a-z0-9_]*(api[_-]?key|secret|password|token|private[_-]?key)[a-z0-9_]*"
            r"\s*[:=][^'\"\n]{0,40}['\"][^'\"]{8,}"
        ),
        "weight": 10.0,
        "message": "Hardcoded credential detected in added lines.",
        "scope": "added",
        "files": None,
    },
    {
        "name": "credential-format",
        "pattern": re.compile(
            r"\b(sk_[A-Za-z0-9_-]{10,}"
            r"|xox[baprs]-[A-Za-z0-9-]{10,}"
            r"|AKIA[0-9A-Z]{16}"
            r"|gh[pousr]_[A-Za-z0-9]{20,}"
            r"|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
        ),
        "weight": 10.0,
        "message": "Added line matches a known credential token format.",
        "scope": "both",
        "files": None,
    },
    {
        "name": "auth-logic-removed",
        "pattern": re.compile(r"(?i)(verify_token|check_auth|is_authenticated|require_login|authorize)"),
        "weight": 8.0,
        "message": "Authentication/authorization logic was removed.",
        "scope": "removed",
        "files": None,
    },
    {
        "name": "dangerous-sql",
        "pattern": re.compile(r"(?i)(drop\s+table|truncate\s+table|delete\s+from)\b"),
        "weight": 7.0,
        "message": "Destructive SQL statement touched in this diff.",
        "scope": "both",
        "files": None,
    },
    {
        "name": "crypto-weakened",
        "pattern": re.compile(r"(?i)(md5|sha1|des|ecb\b)"),
        "weight": 6.0,
        "message": "Weak cryptographic primitive referenced.",
        "scope": "added",
        "files": None,
    },
    {
        "name": "tls-check-bypassed",
        "pattern": re.compile(r"(?i)(verify\s*=\s*False|InsecureSkipVerify\s*:\s*true|rejectUnauthorized\s*:\s*false)"),
        "weight": 9.0,
        "message": "TLS certificate verification disabled.",
        "scope": "added",
        "files": None,
    },
    {
        "name": "infra-permission-widened",
        "pattern": re.compile(
            r"(?i)(0\.0\.0\.0/0|\*\s*:|Effect\"\s*:\s*\"Allow\""
            r"|roles/(admin|owner|editor)|AdministratorAccess)"
        ),
        "weight": 7.5,
        "message": "Overly broad network or IAM permission introduced.",
        "scope": "added",
        "files": r"\.(ya?ml|json|tf)$|^\.github/",
    },
]

HIGH_RISK_PATHS = [
    re.compile(p)
    for p in (
        r"(^|/)(auth|login|session|permission)",
        r"(^|/)(admin|iam|security|config)",
        r"(^|/)(migration|migrations)/",
        r"(^|/)\.github/workflows/",
        r"\.(tf|env|pem|key)$",
        r"(^|/)dockerfile$",
        r"(^|/)(iam|security|config)",
    )
]


def scan(files: list[FileDiff]) -> tuple[list[Finding], float]:
    findings: list[Finding] = []
    for fd in files:
        path_boost = any(rx.search(fd.path) for rx in HIGH_RISK_PATHS)
        for rule in RULES:
            if rule["files"] and not re.search(rule["files"], fd.path):
                continue
            lines: list[str] = []
            if rule["scope"] in ("added", "both"):
                lines += fd.added
            if rule["scope"] in ("removed", "both"):
                lines += fd.removed
            for line in lines:
                if rule["pattern"].search(line):
                    weight = rule["weight"] * (1.3 if path_boost else 1.0)
                    findings.append(
                        Finding(
                            path=fd.path,
                            line_hint=line.strip()[:80],
                            rule=rule["name"],
                            message=rule["message"],
                            weight=round(weight, 2),
                        )
                    )
                    break
    return findings, sum(f.weight for f in findings)
