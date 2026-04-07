terraform {
  required_version = ">= 1.5.7"

  backend "gcs" {
    bucket = "elios-terraform-state-elios-492418"
    prefix = "terraform/state"
  }

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
