# PR Risk Analyzer

An NLP-powered GitHub App that analyzes pull request diffs and flags **risky
semantic changes** — silently weakened auth checks, hardcoded secrets, widened IAM
permissions — with severity-rated comments posted back on the PR.

See [INTERVIEW_PREP.md](INTERVIEW_PREP.md) for the full architecture walkthrough.

## How it works

1. GitHub sends a `pull_request` webhook → FastAPI service (deployed on Cloud Run)
2. Diff is fetched from the GitHub API and parsed into files/hunks
3. Hybrid risk engine:
   - **Rule engine** — weighted regex rules scoped by line polarity (added vs removed)
     and boosted on high-blast-radius paths (`auth/`, `migrations/`, `.tf`, ...)
   - **Semantic engine** — sentence-transformer (`all-MiniLM-L6-v2`) embeddings;
     cosine distance between removed/added lines detects reworded logic regexes miss
4. Scores fuse into a severity: `low / medium / high / critical`
5. A PR comment is created or updated (idempotent, dry-run supported)

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# offline demo — no model download, no GitHub token needed
RISK_DISABLE_EMBEDDINGS=1 uvicorn src.main:app --reload

curl localhost:8000/health
curl -X POST --data-binary @tests/data/sample_diffs/auth_gut.diff \
     localhost:8000/analyze-diff
```

## Tests & eval gate

```bash
pytest -q                      # offline unit tests
EVAL_CRITICAL_RECALL_MIN=1.0 python run_eval.py   # regression gate over labeled diffs
```

## CI/CD

- **CI** (`.github/workflows/ci.yml`): ruff lint → pytest → eval regression gate → Docker build.
  The detector cannot regress silently: if dangerous-PR recall drops below threshold, CI fails.
- **CD** (`.github/workflows/deploy.yml`): push image to GHCR → deploy to GCP Cloud Run via
  `infra/main.tf` → smoke test `/health`.

## Configuration

| Env var | Purpose |
|---|---|
| `GITHUB_TOKEN` | posting PR comments |
| `GITHUB_WEBHOOK_SECRET` | HMAC-SHA256 webhook signature verification |
| `RISK_DRY_RUN` | `1` = log comments instead of posting (default) |
| `RISK_DISABLE_EMBEDDINGS` | skip semantic engine (offline/test mode) |

## Roadmap

- Learn fusion weights from labeled data instead of hand-tuning
- Fine-tune a small classifier head on the eval set
- Queue (PubSub/SQS) between webhook and workers for burst traffic
