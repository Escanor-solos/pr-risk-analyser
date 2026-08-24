resource "google_project_service" "run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secret_manager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iam" {
  service            = "iam.googleapis.com"
  disable_on_destroy = false
}

resource "google_service_account" "analyzer" {
  account_id   = var.service_name
  display_name = "PR Risk Analyzer runtime"
}

resource "google_secret_manager_secret" "github_token" {
  secret_id = "${var.service_name}-github-token"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "webhook_secret" {
  secret_id = "${var.service_name}-webhook-secret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "github_token" {
  secret      = google_secret_manager_secret.github_token.id
  data_wo     = var.github_token
  lifecycle {
    ignore_changes = [data_wo]
  }
}

resource "google_secret_manager_secret_version" "webhook_secret" {
  secret      = google_secret_manager_secret.webhook_secret.id
  data_wo     = var.webhook_secret
  lifecycle {
    ignore_changes = [data_wo]
  }
}

resource "google_secret_manager_secret_iam_member" "token_access" {
  secret_id = google_secret_manager_secret.github_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.analyzer.email}"
}

resource "google_secret_manager_secret_iam_member" "webhook_access" {
  secret_id = google_secret_manager_secret.webhook_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.analyzer.email}"
}

resource "google_cloud_run_v2_service" "analyzer" {
  name                = var.service_name
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.analyzer.email
    containers {
      image = var.image
      env {
        name  = "RISK_DRY_RUN"
        value = "0"
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "1024Mi"
        }
      }
      secrets {
        name        = "GITHUB_TOKEN"
        secret_name = google_secret_manager_secret.github_token.secret_id
      }
      secrets {
        name        = "GITHUB_WEBHOOK_SECRET"
        secret_name = google_secret_manager_secret.webhook_secret.secret_id
      }
      startup_probe {
        http_get {
          path = "/health"
        }
      }
    }
  }

  depends_on = [google_project_service.run]
}
