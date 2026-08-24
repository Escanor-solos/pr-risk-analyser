import os

os.environ["RISK_DISABLE_EMBEDDINGS"] = "1"
os.environ["GITHUB_WEBHOOK_SECRET"] = ""

import base64

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

SAMPLE_DIFF = """diff --git a/src/auth/session.py b/src/auth/session.py
--- a/src/auth/session.py
+++ b/src/auth/session.py
@@ -1,3 +1,3 @@
 def login(user):
-    verify_token(user)
+    API_KEY = 'hunter2hunter2'
     return user
"""


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_analyze_diff_endpoint():
    resp = client.post("/analyze-diff", content=SAMPLE_DIFF.encode())
    assert resp.status_code == 200
    data = resp.json()
    rules_hit = {f["rule"] for f in data["findings"]}
    assert "secret-added" in rules_hit or "auth-logic-removed" in rules_hit


def test_webhook_ignores_non_pr_events():
    import json

    payload = {"zen": "x", "hook_id": 1}
    resp = client.post(
        "/webhook",
        content=json.dumps(payload).encode(),
        headers={"X-GitHub-Event": "ping"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_webhook_rejects_bad_signature_when_configured(monkeypatch):
    import json

    from src import main as m

    monkeypatch.setattr(m, "WEBHOOK_SECRET", "shhhh")
    payload = json.dumps({"action": "opened", "number": 1}).encode()
    bad_sig = "sha256=" + "0" * 64
    resp = client.post(
        "/webhook",
        content=payload,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": bad_sig,
            "X-GitHub-Delivery": "d-" + base64.b16encode(os.urandom(4)).decode(),
        },
    )
    assert resp.status_code == 403
