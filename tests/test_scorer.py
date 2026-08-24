import os

os.environ["RISK_DISABLE_EMBEDDINGS"] = "1"

from src.diff_parser import FileDiff, Hunk
from src.scorer import analyze, classify, render_comment


def test_classify_boundaries():
    assert classify(0) == "low"
    assert classify(2.0) == "medium"
    assert classify(5.0) == "high"
    assert classify(9.0) == "critical"
    assert classify(50.0) == "critical"


def test_analyze_critical_pr():
    files = [
        FileDiff(
            path="src/auth/session.py",
            hunks=[
                Hunk(
                    1,
                    1,
                    removed_lines=["verify_token(request)", "check_auth(user)"],
                    added_lines=["API_KEY = 'hunter2hunter2'"],
                )
            ],
        )
    ]
    result = analyze(files, use_embeddings=False)
    rules_hit = {f.rule for f in result.findings}
    assert "auth-logic-removed" in rules_hit
    assert "secret-added" in rules_hit
    assert result.severity in ("high", "critical")
    assert "Risk analysis" in render_comment(result)


def test_analyze_low_risk_pr():
    files = [FileDiff(path="README.md", hunks=[Hunk(1, 1, [], ["more docs"])])]
    result = analyze(files, use_embeddings=False)
    assert result.severity == "low"


def test_render_comment_escapes_pipes():
    files = [FileDiff(path="c.py", hunks=[Hunk(1, 1, [], ["password = 'aaaaaaaaaaaa|bb'"])])]
    result = analyze(files, use_embeddings=False)
    comment = render_comment(result)
    assert "aaaaaaaaaaaa\\|bb" in comment
