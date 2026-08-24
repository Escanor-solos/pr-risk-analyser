from dataclasses import dataclass

from . import semantic_engine
from .diff_parser import FileDiff
from .rules import Finding, scan

THRESHOLDS = [(2.0, "low"), (5.0, "medium"), (9.0, "high")]
SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass
class AnalysisResult:
    severity: str
    score: float
    findings: list[Finding]
    semantic_shift: float | None


def classify(score: float) -> str:
    label = "critical"
    for bound, name in THRESHOLDS:
        if score < bound:
            return name
        label = "critical"
    return label


def analyze(files: list[FileDiff], use_embeddings: bool = True) -> AnalysisResult:
    findings, rule_score = scan(files)
    shift = semantic_engine.max_shift(files) if use_embeddings else None
    semantic_score = shift * semantic_engine.W_SEMANTIC if shift is not None else 0.0
    total = round(rule_score + semantic_score, 2)
    return AnalysisResult(
        severity=classify(total),
        score=total,
        findings=findings,
        semantic_shift=shift,
    )


def render_comment(result: AnalysisResult) -> str:
    lines = [
        f"## 🔒 Risk analysis: **{result.severity.upper()}** (score {result.score})",
        "",
    ]
    if result.findings:
        lines.append("| Rule | File | Detail |")
        lines.append("|---|---|---|")
        for f in result.findings:
            detail = f.line_hint.replace("|", "\\|")
            lines.append(f"| `{f.rule}` | `{f.path}` | {f.message} `{detail}` |")
    else:
        lines.append("_No rule-based findings._")
    if result.semantic_shift is not None:
        flag = "⚠️ high" if result.semantic_shift >= semantic_engine.DRIFT_THRESHOLD else "ok"
        lines.append("")
        lines.append(f"Max semantic drift across hunks: **{result.semantic_shift}** ({flag})")
    return "\n".join(lines)
