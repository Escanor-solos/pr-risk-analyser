# GitHub App Setup Guide

Wire the analyzer to a real repository. Two options — start with A, upgrade to B.

## Option A: Personal Access Token + Repo Webhook (fastest)

### 1. Create a fine-grained PAT
1. GitHub → Settings → Developer settings → **Fine-grained personal access tokens**
2. Repository access: only the target repo
3. Permissions: **Pull requests: Read & write** (that's all the bot needs)
4. Copy the token — this is your `GITHUB_TOKEN`

### 2. Create a webhook secret
```bash
openssl rand -hex 32   # this is your GITHUB_WEBHOOK_SECRET
```

### 3. Add the webhook to the repo
Repo → Settings → Webhooks → Add webhook:
- **Payload URL**: `https://<your-service-url>/webhook` (see docs/DEPLOY.md), or a
  smee.io URL for local dev: `https://smee.io/<id>`
- **Content type**: `application/json`
- **Secret**: your `GITHUB_WEBHOOK_SECRET`
- **Events**: "Let me select individual events" → *Pull requests* only

### 4. Test locally with smee.io
```bash
npm install -g smee-client
smee --url https://smee.io/<id> --target http://localhost:8000/webhook
RISK_DRY_RUN=1 \
GITHUB_TOKEN=ghp_xxx \
GITHUB_WEBHOOK_SECRET=<same-as-webhook-config> \
uvicorn src.main:app --port 8000
# open a test PR → watch logs; comment prints to stdout instead of posting
```

## Option B: Real GitHub App (proper permissions model)

1. Settings → Developer settings → **GitHub Apps** → New GitHub App
2. Configure:
   - **Webhook URL / Secret**: as above
   - **Permissions**: Pull requests: Read & write; Contents: Read-only (diff access)
   - **Subscribe to events**: Pull request
3. After creation, generate a private key (.pem) and note the **App ID**
4. Install the App on your repos ("Install App" page)
5. Swap token minting in `src/github_client.py` for a JWT → installation-token flow:
   ```python
   import time, jwt
   from github import Github, Auth

   def get_client():
       app_id = os.environ["GITHUB_APP_ID"]
       key = open(os.environ["GITHUB_APP_PEM"]).read()
       payload = {"iat": int(time.time()) - 60, "exp": int(time.time()) + 540, "iss": app_id}
       jwt_token = jwt.encode(payload, key, algorithm="RS256")
       # exchange per-installation via GET /app/installations → POST access_tokens
       ...
   ```
   (PyGithub supports `github.Auth.AppAuth(app_id, private_key)` which handles this.)

Why upgrade: installation tokens are scoped per-repo and expire hourly; a leaked PAT is
a bigger blast radius. Interviewers may ask why you'd bother — that's the answer.

## Verifying the loop end-to-end

```bash
curl -s https://<service>/health          # {"status":"ok"}
curl -s -X POST https://<service>/analyze-diff \
     --data-binary @tests/data/sample_diffs/auth_gut.diff | jq
```

Then open a PR containing:
```python
- verify_token(session)
+ API_KEY = 'sk_test_abcdef123456'
```
Expected: one CRITICAL comment listing both findings.
