terraform {
  required_version = ">= 1.5.7"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.25.0"
    }
  }
}

provider "google" {
  project = "elios-492418"
  region  = var.region
}
