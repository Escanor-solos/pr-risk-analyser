import hashlib
import hmac
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request

from . import github_client
from .diff_parser import parse_unified_diff
from .scorer import analyze, render_comment

load_dotenv()

app = FastAPI(title="PR Risk Analyzer", version="0.1.0")

WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
DRY_RUN = os.environ.get("RISK_DRY_RUN", "1") != "0"
_seen_deliveries: set[str] = set()


def verify_signature(payload: bytes, signature: str | None) -> bool:
    if not WEBHOOK_SECRET:
        return True
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[7:])


@app.get("/health")
def health():
    return {"status": "ok", "dry_run": DRY_RUN}


@app.post("/webhook")
async def webhook(request: Request, x_hub_signature_256: str | None = Header(None), x_github_delivery: str | None = Header(None), x_github_event: str | None = Header(None)):
    raw = await request.body()
    if not verify_signature(raw, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="invalid signature")
    if x_github_delivery:
        if x_github_delivery in _seen_deliveries:
            return {"status": "duplicate-ignored"}
        _seen_deliveries.add(x_github_delivery)

    event = json.loads(raw)
    if x_github_event != "pull_request" or event.get("action") not in ("opened", "synchronize"):
        return {"status": "ignored"}

    repo = event["repository"]["full_name"]
    pr_number = event["number"]
    diff_text = github_client.fetch_diff(repo, pr_number)
    files = parse_unified_diff(diff_text)
    result = analyze(files)
    comment = render_comment(result)
    posted = github_client.post_comment(repo, pr_number, comment, dry_run=DRY_RUN)
    return {
        "status": "analyzed",
        "repo": repo,
        "pr": pr_number,
        "severity": result.severity,
        "score": result.score,
        "comment_posted": posted,
    }


@app.post("/analyze-diff")
async def analyze_diff(request: Request):
    diff_text = (await request.body()).decode()
    files = parse_unified_diff(diff_text)
    result = analyze(files)
    return {"severity": result.severity, "score": result.score, "findings": [f.__dict__ for f in result.findings], "semantic_shift": result.semantic_shift}
