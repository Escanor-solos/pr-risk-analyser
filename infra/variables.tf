variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "image" {
  type        = string
  description = "Container image, e.g. ghcr.io/owner/pr-risk-analyzer:sha"
}

variable "service_name" {
  type    = string
  default = "pr-risk-analyzer"
}

variable "github_token" {
  type        = string
  sensitive   = true
  description = "GitHub PAT used to post PR comments"
}

variable "webhook_secret" {
  type        = string
  sensitive   = true
  description = "Shared secret for verifying GitHub webhook HMAC signatures"
}
