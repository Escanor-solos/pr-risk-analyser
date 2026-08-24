terraform {
  backend "gcs" {
    bucket = "pr-risk-analyzer-pr-risk-tfstate"
    prefix = "pr-risk-analyzer"
  }
}
