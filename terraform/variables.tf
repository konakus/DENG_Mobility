
# Variable für das Projekt
variable "project" {
  description = "Projekt-Name in GCP"
  type        = string
  default     = "projectmobile-494518"
}

# credidentials.
variable "credentials" {
  description = "Pfad zur JSON-Datei des Service Accounts"
  type        = string
}

# Specifies the geographic location for AWS resource deployment.
# Defaulting to Stockholm (eu-north-1) to keep latency low for European users.
variable "region" {
  description = "Google Cloud region"
  type        = string
  default     = "europe-west6"

}

# The unique identifier for the S3 bucket where raw data will be stored.
# S3 bucket names must be globally unique across all AWS accounts.
variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
  default     = "project-mobile-zurich-data-lake-494518"
}

# Defines the logical grouping for metadata in the AWS Glue Catalog.
# This allows tools like Athena to query the S3 data using SQL.
variable "dataset_name" {
  description = "BigQuery dataset name"
  type        = string
  default     = "zurich_mobility_warehouse"
}
