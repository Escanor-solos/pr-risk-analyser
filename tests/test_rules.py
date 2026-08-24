import os

os.environ["RISK_DISABLE_EMBEDDINGS"] = "1"

from src import rules
from src.diff_parser import FileDiff, Hunk
from src.rules import scan


def _diff(path: str, removed: list[str], added: list[str]) -> list[FileDiff]:
    return [FileDiff(path=path, hunks=[Hunk(1, 1, removed_lines=removed, added_lines=added)])]


def test_secret_detected():
    findings, score = scan(_diff("app/helpers.py", [], ["API_KEY = \"supersecret123\""]))
    assert [f.rule for f in findings] == ["secret-added"]
    assert score == 10.0


def test_auth_removed_boosted_by_path():
    _, base_score = scan(_diff("src/utils.py", ["verify_token(request)"], []))
    _, boosted = scan(_diff("src/auth/session.py", ["verify_token(request)"], []))
    assert boosted > base_score
    assert abs(boosted - base_score * 1.3) < 0.01


def test_tls_bypass_detected():
    findings, _ = scan(_diff("client.py", [], ["requests.get(url, verify=False)"]))
    assert findings[0].rule == "tls-check-bypassed"


def test_infra_rule_scoped_to_config_files():
    findings_yaml, _ = scan(_diff("deploy/config.yaml", [], ["cidr: 0.0.0.0/0"]))
    findings_py, _ = scan(_diff("app/main.py", [], ["host = '0.0.0.0'"]))
    assert len(findings_yaml) == 1
    assert not any(f.rule == "infra-permission-widened" for f in findings_py)


def test_no_findings_on_clean_code():
    findings, score = scan(_diff("src/math.py", ["return a + b"], ["return a + b + c"]))
    assert findings == []
    assert score == 0.0


def test_all_rules_have_required_keys():
    for rule in rules.RULES:
        assert {"name", "pattern", "weight", "message", "scope"} <= set(rule)
        assert rule["scope"] in ("added", "removed", "both")
