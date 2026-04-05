output "artifact_registry_repository" {
  description = "Artifact Registry repository name"
  value       = google_artifact_registry_repository.docker.repository_id
}

output "artifact_registry_repository_url" {
  description = "Artifact Registry base URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

output "backend_service_name" {
  description = "Cloud Run backend service name"
  value       = google_cloud_run_v2_service.backend.name
}

output "backend_service_url" {
  description = "Cloud Run backend URL"
  value       = google_cloud_run_v2_service.backend.uri
}

output "frontend_service_name" {
  description = "Cloud Run frontend service name"
  value       = google_cloud_run_v2_service.frontend.name
}

output "frontend_service_url" {
  description = "Cloud Run frontend URL"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "wif_provider" {
  description = "Workload Identity Provider resource for GitHub Actions"
  value       = "projects/${var.project_number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/providers/${google_iam_workload_identity_pool_provider.github.workload_identity_pool_provider_id}"
}

output "github_actions_service_account_email" {
  description = "Service account used by GitHub Actions deploy workflow"
  value       = google_service_account.github_actions.email
}
