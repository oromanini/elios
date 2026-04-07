locals {
  project_id           = "elios-492418"
  backend_service_name = "elios-api"
  frontend_service_name = "elios-web"
  # Imagens dinâmicas para não quebrar o deploy inicial
  backend_image = var.backend_image != "" ? var.backend_image : "${var.region}-docker.pkg.dev/${local.project_id}/${var.artifact_registry_repository_id}/backend:latest"
  frontend_image = var.frontend_image != "" ? var.frontend_image : "${var.region}-docker.pkg.dev/${local.project_id}/${var.artifact_registry_repository_id}/frontend:latest"
}

resource "google_storage_bucket" "terraform_state" {
  name          = "elios-terraform-state-${var.project_id}"
  location      = var.region
  force_destroy = false
  storage_class = "STANDARD"

  versioning {
    enabled = true
  }
}

# --- RECURSO: ARTIFACT REGISTRY ---
resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.artifact_registry_repository_id
  description   = "Container images for ELIOS Cloud Run services"
  format        = "DOCKER"
}

# --- RECURSO: SERVICE ACCOUNT ---
resource "google_service_account" "github_actions" {
  account_id   = "github-actions-deployer"
  display_name = "GitHub Actions Cloud Run deployer"
}

# --- PERMISSÕES DE IAM (O ESSENCIAL) ---
resource "google_project_iam_member" "github_actions_run_admin" {
  project = local.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_actions_artifact_registry_writer" {
  project = local.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_actions_sa_user" {
  project = local.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# --- WORKLOAD IDENTITY FEDERATION (O APERTO DE MÃO) ---
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions Pool"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.actor"      = "assertion.actor"
    "attribute.ref"        = "assertion.ref"
  }
  attribute_condition = "assertion.repository == \"oromanini/elios\""
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_wif_user" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/oromanini/elios"
}
