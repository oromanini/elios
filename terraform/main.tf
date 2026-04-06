locals {
  backend_service_name = "elios-api"
  frontend_service_name = "elios-web"
  # Imagens dinâmicas para não quebrar o deploy inicial
  backend_image = var.backend_image != "" ? var.backend_image : "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repository_id}/backend:latest"
  frontend_image = var.frontend_image != "" ? var.frontend_image : "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repository_id}/frontend:latest"
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
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_actions_artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_actions_sa_user" {
  project = var.project_id
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
  }
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_wif_user" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  # Referência direta ao pool para evitar o erro de número de projeto
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_owner}/${var.github_repository}"
}

# --- SERVIÇO: BACKEND ---
resource "google_cloud_run_v2_service" "backend" {
  name     = local.backend_service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false 

  template {
    service_account = google_service_account.github_actions.email
    containers {
      image = local.backend_image

      env {
        name  = "ENV"
        value = "production"
      }
      env {
        name  = "MONGO_URL"
        value = var.mongo_url
      }
      env {
        name  = "DB_NAME"
        value = var.db_name
      }
      # JWT e GROQ REMOVIDOS CONFORME SOLICITADO
    }
  }
}

# --- SERVIÇO: FRONTEND ---
resource "google_cloud_run_v2_service" "frontend" {
  name     = local.frontend_service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.github_actions.email
    containers {
      image = local.frontend_image
      env {
        name  = "VITE_API_URL"
        value = google_cloud_run_v2_service.backend.uri
      }
    }
  }
}

# --- ACESSO PÚBLICO ---
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  for_each = toset([local.backend_service_name, local.frontend_service_name])
  location = var.region
  name     = each.value
  role     = "roles/run.invoker"
  member   = "allUsers"
  depends_on = [google_cloud_run_v2_service.backend, google_cloud_run_v2_service.frontend]
}
