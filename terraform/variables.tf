variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "project_number" {
  description = "GCP project number (12-digit number)"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "artifact_registry_repository_id" {
  description = "Artifact Registry Docker repository name"
  type        = string
  default     = "elios"
}

variable "github_owner" {
  description = "GitHub organization/user that owns the repository"
  type        = string
}

variable "github_repository" {
  description = "GitHub repository name"
  type        = string
}

variable "backend_image" {
  description = "Backend image reference used by Cloud Run"
  type        = string
  default     = ""
}

variable "frontend_image" {
  description = "Frontend image reference used by Cloud Run"
  type        = string
  default     = ""
}

variable "mongo_url" {
  description = "MongoDB Atlas connection string"
  type        = string
  sensitive   = true
  default     = ""
}

variable "db_name" {
  description = "MongoDB database name"
  type        = string
  default     = ""
}

variable "r2_access_key" {
  description = "Cloudflare R2 access key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "r2_secret_key" {
  description = "Cloudflare R2 secret key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "r2_endpoint" {
  description = "Cloudflare R2 S3 endpoint"
  type        = string
  default     = ""
}

variable "r2_bucket_name" {
  description = "Cloudflare R2 bucket name"
  type        = string
  default     = ""
}

variable "frontend_domain" {
  description = "Optional custom domain used by frontend service"
  type        = string
  default     = ""
}
