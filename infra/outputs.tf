output "service_url" {
  value       = google_cloud_run_v2_service.analyzer.uri
  description = "Public URL — use <url>/webhook as the GitHub webhook payload URL"
}
