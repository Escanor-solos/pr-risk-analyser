# Cloud Deploy Guide (GCP Cloud Run + Terraform)

One-time setup ≈ 30 minutes; every deploy after that is `git push` to main.

## Prerequisites
- A GCP project with billing enabled (free tier covers this project's traffic)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed locally
- Terraform >= 1.6 (`brew install terraform` / `apt`)

## 1. One-time local setup

```bash
export PROJECT_ID=your-project-id
gcloud auth login && gcloud config set project $PROJECT_ID

# enable APIs (also done by terraform, but handy for the SA step)
gcloud services enable run.googleapis.com secretmanager.googleapis.com \
       iam.googleapis.com artifactregistry.googleapis.com \
       cloudbilling.googleapis.com

# service account used by CI deploys (not the runtime SA — terraform makes that one)
gcloud iam service-accounts create pr-risk-analyzer-deploy

for role in roles/run.admin roles/iam.serviceAccountUser \
            roles/secretmanager.admin roles/artifactregistry.writer; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member "serviceAccount:pr-risk-analyzer-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
    --role "$role"
done

gcloud iam service-accounts keys create ~/pr-risk-deploy-key.json \
  --iam-account "pr-risk-analyzer-deploy@$PROJECT_ID.iam.gserviceaccount.com"
```

## 2. Remote state bucket (recommended)

```bash
gcloud storage buckets create gs://$PROJECT_ID-pr-risk-tfstate \
  --location=us-central1 --uniform-bucket-level-access
```
Uncomment the backend block below, then `terraform init`.

## 3. GitHub repo settings

| Setting | Value |
|---|---|
| Variable `GCP_PROJECT_ID` | your project id |
| Variable `TF_STATE_BUCKET` | bucket name from step 2 |
| Secret `GCP_SA_KEY` | contents of `~/pr-risk-deploy-key.json` |
| Secret `GITHUB_TOKEN_PR_COMMENTS` | PAT from docs/GITHUB_APP_SETUP.md |
| Secret `GITHUB_WEBHOOK_SECRET` | same secret configured on the webhook |

## 4. First deploy

Push to `main`. The pipeline will:
1. Build & push `ghcr.io/<you>/pr-risk-analyzer:<sha>` 
2. `terraform apply` — creates runtime SA, secrets, Cloud Run service
3. Smoke-test `/health`

Manual equivalent:
```bash
cd infra
terraform init -backend-config="bucket=$PROJECT_ID-pr-risk-tfstate"
terraform apply \
  -var project_id=$PROJECT_ID \
  -var image=ghcr.io/<you>/pr-risk-analyzer:<tag> \
  -var github_token=$(cat /path/to/pat) \
  -var webhook_secret=$(openssl rand -hex 32)

terraform output service_url   # ← use as webhook Payload URL
```

Note: secret *versions* are written once by terraform (`data_wo`, write-only) and then
ignored — rotate values via `gcloud secrets versions add`, not terraform.

## 5. Point the webhook at it

Follow docs/GITHUB_APP_SETUP.md §3 with:
```
Payload URL: <terraform output service_url>/webhook
```

## 6. Verify

```bash
URL=$(cd infra && terraform output -raw service_url)
curl -s $URL/health
curl -s -X POST $URL/analyze-diff --data-binary @tests/data/sample_diffs/auth_gut.diff | jq .severity
# → "critical"
```

## Rollback

```bash
# redeploy a previous immutable image tag
terraform apply -var image=ghcr.io/<you>/pr-risk-analyzer:<old-sha> ... 
# or instant traffic split in the console: Cloud Run → Revisions → Manage traffic
```

## Cost expectation
Scale-to-zero, hobby traffic: effectively free (Cloud Run free tier: 2M req/mo).
With min-instances=1 running 24/7: ~$10/mo worst case.
