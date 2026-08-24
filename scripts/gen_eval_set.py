"""Generate a labeled eval set of realistic PR diffs.

Creates ~50 .diff files under tests/data/sample_diffs/ and labels in
eval/labeled_diffs.jsonl. Categories mirror real-world risky changes:
secrets, auth removal, destructive SQL, TLS bypass, IAM widening, weak crypto,
and benign refactors/docs/tests.

Run: python scripts/gen_eval_set.py
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).parent.parent
DIFF_DIR = ROOT / "tests" / "data" / "sample_diffs"
LABELS = ROOT / "eval" / "labeled_diffs.jsonl"

random.seed(42)

SECRETS = [
    ("config/settings.py", 'AWS_SECRET_ACCESS_KEY = "{tok}"', "prod"),
    ("app/auth/client.py", 'api_key: str = "{tok}"', "live"),
    ("services/payment.py", 'STRIPE_KEY = "sk_{tok}0123456789"', "test"),
    ("workers/notify.py", 'SLACK_TOKEN = "xoxb-{tok}-123456"', "demo"),
]
AUTH_REMOVALS = [
    ("src/auth/session.py", ["verify_token(session)", "check_auth(user)"], ["return True"]),
    ("api/middleware.py", ["if not is_authenticated(request):", "    return redirect('/login')"], ["pass"]),
    ("routes/admin.py", ["@require_login", "def dashboard(): ..."], ["def dashboard(): ..."]),
    ("lib/guards.py", ["assert authorize(user, resource)"], ["# removed check"]),
]
SQL = [
    ("db/migrations/007_cleanup.sql", ["DROP TABLE old_events;", "TRUNCATE TABLE audit_log;"], []),
    ("db/migrations/008_purge.sql", ["DELETE FROM users WHERE last_login < '2020-01-01';"], []),
]
TLS = [
    ("clients/http.py", ['requests.post(url, json=payload, verify=False)'], []),
    ("internal/api.go", ["InsecureSkipVerify: true // dev only"], []),
]
IAM = [
    ("infra/main.tf", ['ingress { from_port = 0; cidr_blocks = ["0.0.0.0/0"] }'], []),
    (".github/workflows/deploy.yml", ["role: roles/owner"], []),
    ("policies/trust.json", ['"Effect": "Allow", "Action": "*", "Resource": "*"'], []),
]
CRYPTO = [
    ("utils/hash.py", ["digest = hashlib.md5(data).hexdigest()"], []),
    ("legacy/token.py", ["cipher = DES.new(key, DES.MODE_ECB)"], []),
]

BENIGN = [
    ("README.md", ["## Old title"], ["## New title"]),
    ("docs/setup.md", ["Run `make dev`"], ["Run `make develop`"]),
    ("src/format.py", ['return d.strftime("%Y-%m-%d")'], ['return d.isoformat()']),
    ("tests/test_util.py", ["def test_old(): assert True"], ["def test_new(): assert True"]),
    ("src/naming.py", ["def calcTotal(a, b):"], ["def calculate_total(a, b):"]),
    ("CHANGELOG.md", [], ["- release 1.2.3"]),
    ("src/comments.py", ["x = 1 # TODO fix"], ["x = 1"]),
    ("styles/theme.css", ["color: #000;"], ["color: #111;"]),
]


def make_hunk(removed, added):
    lines = [f"@@ -10,{len(removed) + 1} +10,{len(added) + 1} @@"]
    for r in removed:
        lines.append(f"-{r}")
    for a in added:
        lines.append(f"+{a}")
    lines.append(" context_line_untouched()")
    return "\n".join(lines)


def make_diff(path, removed, added):
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        + make_hunk(removed, added)
        + "\n"
    )


cases = []
i = 0


def add(label, diff_text):
    global i
    i += 1
    name = f"{label}_{i:02d}.diff"
    (DIFF_DIR / name).write_text(diff_text)
    cases.append({"label": label, "file": name, "note": ""})


for path, tpl, env in SECRETS * 3:
    tok = "".join(random.choices("abcdef0123456789", k=20))
    add("critical", make_diff(path, ["# moved config"], [tpl.format(tok=tok)]))

for path, removed, added in AUTH_REMOVALS * 2:
    sev = "high" if "admin" not in path else "critical"
    add(sev, make_diff(path, removed, added))

for path, removed, _ in SQL * 2:
    add("high", make_diff(path, removed, ["-- scheduled cleanup"]))

for path, added, _ in TLS * 2:
    add("high", make_diff(path, ["# placeholder"], added))

for path, added, _ in IAM * 3:
    add("critical", make_diff(path, ["# tighten later"], added))

for path, added, _ in CRYPTO * 2:
    add("medium", make_diff(path, ["hashlib.sha256(data).hexdigest()"], added))

for n in range(18):
    path, removed, added = random.choice(BENIGN)
    add("low", make_diff(path, removed, added))

with LABELS.open("w") as f:
    for c in cases:
        f.write(json.dumps(c) + "\n")

print(f"wrote {len(cases)} labeled diffs to {DIFF_DIR} and {LABELS}")
