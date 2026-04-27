terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "7.23.0"
    }
  }
}

provider "google" {
  # Credentials only needs to be set if you do not have the GOOGLE_APPLICATION_CREDENTIALS set
  credentials = file(var.credentials)
  project     = var.project #<Your GCP Project ID>    
  region      = var.region  #<Your GCP Region>
}

resource "google_storage_bucket" "data_lake" {
  name                        = var.bucket_name #<Your Unique Bucket Name>
  location                    = "EU"
  force_destroy               = true
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true


  lifecycle_rule {
    action {
      type = "AbortIncompleteMultipartUpload"
    }
    condition {
      age = 1 // days
    }
  }
}

resource "google_bigquery_dataset" "zurich_mobility_dataset" {
  dataset_id = var.dataset_name #<Your Dataset Name>
  project    = var.project      #<Your GCP Project ID>
  location   = "EU"
}