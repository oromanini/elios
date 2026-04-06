locals {
  backend_service_name = "elios-api"
  frontend_service_name = "elios-web"
  backend_image = var.backend_image != "" ? var.backend_image : "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repository_id}/backend:latest"
  frontend_image = var.frontend_image != "" ? var.frontend_image : "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repository_id}/frontend:latest"
}

resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.artifact_registry_repository_id
  description   = "Container images for ELIOS Cloud Run services"
  format        = "DOCKER"
}

resource "google_artifact_registry_repository_cleanup_policy" "keep_last_two_tagged" {
  project    = var.project_id
  location   = google_artifact_registry_repository.docker.location
  repository = google_artifact_registry_repository.docker.repository_id

  cleanup_policy_id = "keep-last-2-tagged"
  action            = "KEEP"

  condition {
    tag_state = "TAGGED"
  }

  most_recent_versions {
    keep_count = 2
  }
}

resource "google_artifact_registry_repository_cleanup_policy" "delete_old_tagged" {
  project    = var.project_id
  location   = google_artifact_registry_repository.docker.location
  repository = google_artifact_registry_repository.docker.repository_id

  cleanup_policy_id = "delete-older-tagged"
  action            = "DELETE"

  condition {
    tag_state  = "TAGGED"
    older_than = "1d"
  }

  depends_on = [google_artifact_registry_repository_cleanup_policy.keep_last_two_tagged]
}

resource "google_service_account" "github_actions" {
  account_id   = "github-actions-deployer"
  display_name = "GitHub Actions Cloud Run deployer"
}

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

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions Pool"
  description               = "WIF pool for GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Provider"
  description                        = "OIDC provider for GitHub Actions"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.actor"      = "assertion.actor"
    "attribute.ref"        = "assertion.ref"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_condition = "assertion.repository == '${var.github_owner}/${var.github_repository}'"
}

resource "google_service_account_iam_member" "github_wif_user" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${var.project_number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/attribute.repository/${var.github_owner}/${var.github_repository}"
}

resource "google_cloud_run_v2_service" "backend" {
  name     = local.backend_service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

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


      env {
        name  = "R2_ACCESS_KEY"
        value = coalesce(var.r2_access_key, "dummy")
      }

      env {
        name  = "R2_SECRET_KEY"
        value = coalesce(var.r2_secret_key, "dummy")
      }

      env {
        name  = "R2_ENDPOINT"
        value = coalesce(var.r2_endpoint, "https://dummy.invalid")
      }

      env {
        name  = "R2_BUCKET_NAME"
        value = coalesce(var.r2_bucket_name, "dummy")
      }

      env {
        name  = "JWT_SECRET"
        value = var.jwt_secret
      }

      env {
        name  = "GROQ_API_KEY"
        value = var.groq_api_key
      }

      env {
        name  = "USER"
        value = var.user
      }

      env {
        name  = "PASSWORD"
        value = var.password
      }
    }
  }

  depends_on = [
    google_project_iam_member.github_actions_run_admin,
    google_project_iam_member.github_actions_sa_user
  ]
}

resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  project  = var.project_id
  location = google_cloud_run_v2_service.backend.location
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service" "frontend" {
  name     = local.frontend_service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

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

  depends_on = [google_cloud_run_v2_service.backend]
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  location = google_cloud_run_v2_service.frontend.location
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
