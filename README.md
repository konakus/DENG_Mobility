# DENG Mobility Project – Zurich Pipeline

Final project for the Data Engineering module at HSLU.  
Project status: May 28, 2026.

## Table of Contents

1. [Overview](#1-overview)
2. [Use Case](#2-use-case)
3. [Architecture](#3-architecture)
4. [Local Pipeline: PostgreSQL and pgAdmin](#4-local-pipeline-postgresql-and-pgadmin)
5. [Cloud Pipeline: Data Lake and BigQuery](#5-cloud-pipeline-data-lake-and-bigquery)
6. [Transformation Logic](#6-transformation-logic)
7. [Verification](#7-verification)
8. [Reproducibility Guide](#8-reproducibility-guide)
9. [Cloud Infrastructure with Terraform](#9-cloud-infrastructure-with-terraform)
10. [Google Cloud Access and Credentials](#10-google-cloud-access-and-credentials)
11. [Environment Variables and Secrets](#11-environment-variables-and-secrets)
12. [Repository Structure](#12-repository-structure)
13. [Project Presentation](#13-project-presentation)
14. [Notes and Future Improvements](#14-notes-and-future-improvements)
15. [Authors](#15-authors)

---

## 1. Overview

This project implements an end-to-end batch data pipeline for Zurich mobility and weather data.

The pipeline combines:

* Weather data from the [Open-Meteo API](https://open-meteo.com/en/docs/historical-weather-api)
* Traffic data from [Zurich mobility datasets](https://data.stadt-zuerich.ch/dataset/ted_taz_verkehrszaehlungen_werte_fussgaenger_velo)

The project contains both a local and a cloud-based pipeline.

1. **Local pipeline**
   - Ingests raw data into PostgreSQL
   - Transforms the data into a daily aggregated table
   - Uses pgAdmin for local verification

2. **Cloud pipeline**
   - Ingests raw source data into a Google Cloud Storage data lake
   - Reads the raw data from the data lake
   - Transforms and loads analytical tables into BigQuery

Apache Airflow orchestrates both the local and cloud workflows.  
Terraform provisions the required Google Cloud infrastructure.  
Docker Compose is used to make the local execution environment reproducible.

---

## 2. Use Case

**Persona:** Urban Mobility Analyst at the City of Zurich

The persona wants to monitor and analyze how weather conditions influence pedestrian and bicycle mobility in Zurich.

The final analytical datasets support questions such as:

- How does precipitation affect bicycle and pedestrian traffic?
- How do mobility patterns differ between weekdays and weekends?
- How does the current year compare to the previous year?
- Are current mobility trends developing differently under similar weather conditions?
- Which counting stations show unusually high or low mobility patterns?

### Why this user needs a data pipeline

The source data is distributed across different systems:

- Traffic data is provided by the Stadt Zürich Open Data portal
- Weather data is provided by the Open-Meteo API

The raw datasets have different structures and time granularities. Therefore, they are not directly usable for analysis.

### How the processed data is used

The pipeline produces analytical BigQuery tables that combine:

- weather indicators
- bicycle and pedestrian counts
- calendar features such as year, month, weekday and weekend flag
- station-level information for more detailed spatial analysis

For the final version, the pipeline includes both:

- **2025** as a complete reference year
- **2026** as the current year

This makes the scheduled Airflow pipeline meaningful because current-year data can be refreshed regularly and compared against the previous year.

---

## 3. Architecture

### 3.1 Local Architecture

```text
Docker Compose
│
├── PostgreSQL
│     └── stores local raw and transformed tables
│
├── pgAdmin
│     └── local database UI (http://localhost:8085)
│
├── Airflow
│     └── orchestrates the local batch pipeline
│
└── Python scripts (Ingestion + Transformation)
      ├── ingest_meteo.py
      ├── ingest_traffic.py
      └── transform_zurich_daily.py
```

### 3.2 Cloud Architecture

```text
Stadt Zürich Open Data       Open-Meteo API
          │                       │
          ▼                       ▼
 cloud_data_lake_ingestion Airflow DAG
          │
          ▼
Google Cloud Storage Data Lake
          │
          ▼
cloud_warehouse_transformation Airflow DAG
          │
          ▼
BigQuery Data Warehouse
          │
          ├── mobility_weather_daily
          └── mobility_weather_daily_by_station
```

### 3.3 Airflow DAGs

The project contains three Airflow DAGs.  

| DAG                          | Purpose                   |
|------------------------------|---------------------------|
| `zurich_mobility_pipeline`   | Local PostgreSQL pipeline |
| `cloud_data_lake_ingestion`  | Loads raw traffic & weather data into GCS |
| `cloud_warehouse_transformation` | Reads raw data from GCS, transforms & loads it into BigQuery |

### 3.4 Final Cloud Data Flow

```text
Traffic 2025 CSV URL
Traffic 2026 CSV URL
Open-Meteo 2025 API
Open-Meteo 2026 API
        │
        ▼
Google Cloud Storage Data Lake
        │
        ▼
Daily aggregation and join
        │
        ▼
BigQuery tables:
projectmobile-494518.zurich_mobility_warehouse.mobility_weather_daily
projectmobile-494518.zurich_mobility_warehouse.mobility_weather_daily_by_station
```

---

## 4. Local Pipeline: PostgreSQL and pgAdmin

The local pipeline was developed first and is kept in the repository for reproducibility and development.

It loads weather and traffic data into PostgreSQL, transforms them, and creates a local final table (mobility_weather_daily).

### 4.1 Start the local Docker environment

Prerequisites:

- Docker Desktop installed and running
- Project cloned from the original [GitHub repository](https://github.com/konakus/DENG_Mobility.git)
- A local `.env` file based on `.env.example`

Start the system:

From the project folder:
- create a local `.env` file
- build the Airflow image locally
- start Docker Desktop

```bash
cp .env.example .env
docker build -f Dockerfile.airflow -t deng_airflow:2.9.3 .
docker compose up -d
```
To be sure, run:
```bash
docker compose ps
```
You should see airflow_webserver, airflow_scheduler, meteo_pgdatabase, and meteo_pgadmin running.


### 4.2 pgAdmin

Open pgAdmin:

```text
http://localhost:8085
```

The pgAdmin login is read from the local `.env` file:

```text
PGADMIN_DEFAULT_EMAIL
PGADMIN_DEFAULT_PASSWORD
```

Create a new server:

**General**

```text
Name: meteo-postgres
```

**Connection**

```text
Host name/address: pgdatabase
Port: 5432
Maintenance database: meteo
Username: value of POSTGRES_USER from .env
Password: value of POSTGRES_PASSWORD from .env
```

The local setup uses multiple databases.  
`meteo` stores weather data.  
`traffic_zurich` stores traffic data and the final transformed local table.

### 4.3 Local Airflow pipeline

Open Airflow:

```text
http://localhost:8086
```

The Airflow login is created from the local `.env` file:

```text
AIRFLOW_USERNAME
AIRFLOW_PASSWORD
```
You can see three DAGs: cloud_data_lake_ingestion,
cloud_warehouse_transformation & zurich_mobility_pipeline

Enable and trigger the DAG:

```text
zurich_mobility_pipeline
```

To the right of the zurich_mobility_pipeline line, you'll see a play icon under Actions. Click the blue play button to trigger the DAG. Then open `zurich_mobility_pipeline` to check the task status.

Expected tasks:

```text
ingest_weather
ingest_traffic
transform_daily
```

All tasks should turn green.

### 4.4 Local PostgreSQL verification

In pgAdmin, open the database:

```text
traffic_zurich
```

Run in Query Tool:

```sql
SELECT COUNT(*) FROM mobility_weather_daily;
```

For the local pipeline, the expected result is:

```text
365 rows
```

This local result is based on the 2025 dataset.

---

## 5. Cloud Pipeline: Data Lake and BigQuery

The final project version extends the local pipeline with a cloud-based data lake and data warehouse architecture.

### 5.1 Cloud Data Lake Ingestion

The Airflow DAG `cloud_data_lake_ingestion` uploads the raw source data to the Google Cloud Storage data lake.

This step represents the cloud ingestion part of the final pipeline. The raw traffic and weather files are not transformed in this step. They are only collected and stored in the cloud data lake. The transformation happens later in the BigQuery pipeline.

#### Purpose of this DAG

The DAG loads raw data from the source systems and stores it in Google Cloud Storage.

It uploads the following files:

```text
raw/traffic/year=2025/traffic_zurich_2025.csv
raw/traffic/year=2026/traffic_zurich_2026.csv
raw/weather/year=2025/weather_zurich_2025.csv
raw/weather/year=2026/weather_zurich_2026.csv
```

The 2025 files represent the complete reference year.
The 2026 files represent the current year and can be refreshed regularly through the scheduled Airflow DAG.

The target bucket is configured via the environment variable:

```text
GCS_BUCKET_NAME
```
In the current project setup, the bucket is:

```text
project-mobile-zurich-data-lake-494518
```

This bucket is the Google Cloud Storage data lake. Reviewers only need access to the Google Cloud project to verify the uploaded raw files in the bucket.

Google Cloud Storage bucket:  
[Open bucket in Google Cloud Console](https://console.cloud.google.com/storage/browser/project-mobile-zurich-data-lake-494518?project=projectmobile-494518)

Note: A local Google service account key is only required to run the cloud Airflow DAG locally. To verify the uploaded files in the Google Cloud Console, reviewers only need access to the Google Cloud project.

### 5.2 Cloud Warehouse Transformation

The Airflow DAG

```text
cloud_warehouse_transformation
```

reads the raw files from Google Cloud Storage, applies the transformation logic and loads the final analytical tables into BigQuery.

The final BigQuery dataset is configured via:

```text
BQ_DATASET_ID
```

In the current project setup, the dataset is:

```text
projectmobile-494518.zurich_mobility_warehouse
```
#### Verification

After the DAG has finished successfully, the task `transform_gcs_to_bigquery` should be green in Airflow.

Verify the result in BigQuery:  
[Open BigQuery](https://console.cloud.google.com/bigquery?project=projectmobile-494518)


### 5.3 Final BigQuery Tables

The pipeline creates two BigQuery tables in: 

```text
projectmobile-494518.zurich_mobility_warehouse
```

#### City-level table

```text
mobility_weather_daily
```

Granularity:

```text
one row per date
```

Purpose:

- high-level monitoring of Zurich mobility
- comparison of 2025 and 2026
- weather impact analysis at city level

#### Station-level table

```text
mobility_weather_daily_by_station
```

Granularity:

```text
one row per date and counting station
```

Purpose:

- station-level mobility analysis
- spatial comparison between counting stations
- detailed analysis using `station_id`, `east_coord` and `north_coord`

### 5.4 BigQuery Partitioning and Clustering

Both BigQuery tables are partitioned by:

```text
date
```

This improves queries that filter or aggregate data by date.

The city-level table is clustered by:

```text
year, month, is_weekend
```

The station-level table is clustered by:

```text
station_id, year, month
```

This supports common analysis patterns such as:

- comparing 2025 and 2026
- filtering by month
- comparing weekdays and weekends
- analyzing specific counting stations

---

## 6. Transformation Logic

The transformation logic converts raw traffic and weather data into analytical datasets.

### 6.1 Weather Transformation

Weather data is loaded from Open-Meteo on an hourly level and aggregated to daily level.

The following features are calculated:

- average temperature
- total precipitation
- average wind speed

### 6.2 Traffic Transformation

Traffic data is loaded from the Stadt Zürich Open Data CSV files.

The following steps are applied:

- parse timestamps from the `DATUM` column
- convert bicycle and pedestrian count columns to numeric values
- treat missing count values as zero
- calculate row-level bicycle totals from `VELO_IN` and `VELO_OUT`
- calculate row-level pedestrian totals from `FUSS_IN` and `FUSS_OUT`

### 6.3 City-Level Aggregation

The city-level table aggregates all Zurich counting stations into one daily row.

Output table:

```text
mobility_weather_daily
```

The following features are calculated:

- total bicycle traffic per day
- total pedestrian traffic per day
- daily weather indicators
- calendar features

### 6.4 Station-Level Aggregation

The station-level table keeps the station dimension.

Output table:

```text
mobility_weather_daily_by_station
```

Calculated features per date and station:
- `station_id`
- `east_coord`
- `north_coord`
- total bicycle traffic per station and day
- total pedestrian traffic per station and day
- daily weather indicators
- calendar features

This table allows more detailed spatial analysis while preserving the simpler city-level table for high-level monitoring.

### 6.5 Final Join and Calendar Features

Weather and traffic data are joined by date.

Additional calendar features:

- year
- month
- day of week
- weekend flag

The final datasets support the use case by providing clean analytical tables with both weather and mobility indicators.

---

## 7. Verification

### 7.1 Local PostgreSQL Verification

Open pgAdmin:

```text
http://localhost:8085
```

Use the database:

```text
traffic_zurich
```

Run:

```sql
SELECT COUNT(*) FROM mobility_weather_daily;
```

For the local pipeline, the expected result is:

```text
365 rows
```

### 7.2 Cloud Storage Verification

Open Google Cloud Console and navigate to:

```text
Cloud Storage → Buckets → project-mobile-zurich-data-lake-494518
```

The following files should exist:

```text
raw/traffic/year=2025/traffic_zurich_2025.csv
raw/traffic/year=2026/traffic_zurich_2026.csv
raw/weather/year=2025/weather_zurich_2025.csv
raw/weather/year=2026/weather_zurich_2026.csv
```

### 7.3 BigQuery Verification: City-Level Table

Open BigQuery in the Google Cloud Console and navigate to:

```text
projectmobile-494518 → zurich_mobility_warehouse → mobility_weather_daily
```

Run:

```sql
SELECT
  COUNT(*) AS row_count,
  MIN(date) AS min_date,
  MAX(date) AS max_date
FROM `projectmobile-494518.zurich_mobility_warehouse.mobility_weather_daily`;
```

Expected result:

- `min_date` should be `2025-01-01`
- `max_date` should correspond to the latest loaded 2026 weather date
- `row_count` should include all daily rows from 2025 and the loaded part of 2026

Preview the final city-level table:

```sql
SELECT *
FROM `projectmobile-494518.zurich_mobility_warehouse.mobility_weather_daily`
ORDER BY date
LIMIT 20;
```

### 7.4 BigQuery Verification: Station-Level Table

Open BigQuery in the Google Cloud Console and navigate to:

```text
projectmobile-494518 → zurich_mobility_warehouse → mobility_weather_daily_by_station
```

Run:

```sql
SELECT
  COUNT(*) AS row_count,
  COUNT(DISTINCT station_id) AS station_count,
  MIN(date) AS min_date,
  MAX(date) AS max_date
FROM `projectmobile-494518.zurich_mobility_warehouse.mobility_weather_daily_by_station`;
```

Preview the station-level table:

```sql
SELECT *
FROM `projectmobile-494518.zurich_mobility_warehouse.mobility_weather_daily_by_station`
ORDER BY date, station_id
LIMIT 20;
```

Example station-level analysis:

```sql
SELECT
  station_id,
  SUM(total_velo) AS yearly_velo_total,
  SUM(total_fuss) AS yearly_fuss_total
FROM `projectmobile-494518.zurich_mobility_warehouse.mobility_weather_daily_by_station`
WHERE year = 2025
GROUP BY station_id
ORDER BY yearly_velo_total DESC
LIMIT 10;
```

### 7.5 Optional Terminal Verification for GCS

From the project root, after the Docker environment is running:

```bash
docker compose exec airflow-scheduler python -c "from google.cloud import storage; c=storage.Client(); b=c.bucket('project-mobile-zurich-data-lake-494518'); [print(x.name, x.size) for x in b.list_blobs(prefix='raw/')]"
```

Expected objects include:

```text
raw/traffic/year=2025/traffic_zurich_2025.csv
raw/traffic/year=2026/traffic_zurich_2026.csv
raw/weather/year=2025/weather_zurich_2025.csv
raw/weather/year=2026/weather_zurich_2026.csv
```

---

## 8. Reproducibility Guide

This section explains how another person can reproduce the final project in their own Google Cloud project.

The reproduction starts from a clean clone of the repository, creates the required cloud infrastructure with Terraform, runs the Airflow pipelines, and finally verifies the two BigQuery output tables.

---

### 8.1 Reproduction Goal

After completing this guide, the reviewer should have the following resources in their own Google Cloud project:

```text
Google Cloud Storage bucket:
<your-globally-unique-bucket-name>

BigQuery dataset:
zurich_mobility_warehouse

BigQuery tables:
mobility_weather_daily
mobility_weather_daily_by_station
```

The high-level workflow is:

```text
Clone repository
→ create or select a Google Cloud project
→ create a local .env file
→ create a Google Cloud service account key
→ configure Terraform variables
→ provision the GCS bucket and BigQuery dataset with Terraform
→ build the custom Airflow image
→ start Docker Compose
→ run the cloud_data_lake_ingestion DAG
→ run the cloud_warehouse_transformation DAG
→ verify both BigQuery tables
```

---

### 8.2 Prerequisites

The reviewer needs:

* Git
* Docker Desktop
* Terraform
* A Google Cloud account
* A Google Cloud project with billing enabled
* Permissions in that Google Cloud project to create:

  * a Cloud Storage bucket
  * a BigQuery dataset
  * a service account
  * a service account key

The following Google Cloud APIs should be enabled in the project:

```text
Cloud Storage API
BigQuery API
IAM API
```

If these APIs are not enabled, Terraform or the pipeline may fail with permission or API-not-enabled errors.

---

### 8.3 Clone the Repository

```bash
git clone https://github.com/konakus/DENG_Mobility.git
cd DENG_Mobility
```

---

### 8.4 Create or Select a Google Cloud Project

Create a new Google Cloud project or select an existing project that you own.

The project must have billing enabled.

In the Google Cloud Console, note the project ID. This value will be used later as:

```text
GCP_PROJECT_ID
```

Example:

```text
my-review-project-123456
```

The following Google Cloud APIs should be enabled for the project:

```text
Cloud Storage API
BigQuery API
IAM API
```

If the APIs are not enabled manually, Terraform or the pipeline may fail with permission or API-not-enabled errors.

---

### 8.5 Create a Service Account Key

Create or use a service account in your own Google Cloud project.

The service account needs permissions for:

```text
Storage Admin
BigQuery Admin
Service Account User
```

Then create a JSON key for this service account.

Store the key locally as:

```text
terraform/keys/my-creds.json
```

If the folder does not exist yet, create it first.

On macOS/Linux:

```bash
mkdir -p terraform/keys
```

On Windows PowerShell:

```powershell
mkdir terraform\keys
```

The key file must not be committed to GitHub.

---

### 8.6 Create the Local `.env` File

The repository contains an example environment file:

```text
.env.example
```

Create a local `.env` file from it.

On macOS/Linux:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Then edit `.env`.

The following values must be adapted to your own Google Cloud project:

```env
GCP_PROJECT_ID=<your-gcp-project-id>
GCS_BUCKET_NAME=<your-globally-unique-bucket-name>
BQ_DATASET_ID=zurich_mobility_warehouse
BQ_CITY_TABLE_ID=mobility_weather_daily
BQ_STATION_TABLE_ID=mobility_weather_daily_by_station
GOOGLE_APPLICATION_CREDENTIALS=/opt/airflow/project/terraform/keys/my-creds.json
```

Important: the Cloud Storage bucket name must be globally unique across Google Cloud. You cannot reuse the bucket name from another project.

Example:

```env
GCP_PROJECT_ID=my-review-project-123456
GCS_BUCKET_NAME=zurich-mobility-data-lake-reviewer-123456
BQ_DATASET_ID=zurich_mobility_warehouse
BQ_CITY_TABLE_ID=mobility_weather_daily
BQ_STATION_TABLE_ID=mobility_weather_daily_by_station
GOOGLE_APPLICATION_CREDENTIALS=/opt/airflow/project/terraform/keys/my-creds.json
```

The remaining local values such as PostgreSQL, pgAdmin and Airflow credentials can be kept as provided or changed if desired.

The `.env` file must not be committed.

---

### 8.7 Configure Terraform Variables

Go to the Terraform folder:

```bash
cd terraform
```

Create a local Terraform variable file from the example file.

On macOS/Linux:

```bash
cp terraform.tfvars.example terraform.tfvars
```

On Windows PowerShell:

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`.

Example:

```hcl
credentials  = "keys/my-creds.json"
project      = "<your-gcp-project-id>"
bucket_name  = "<your-globally-unique-bucket-name>"
dataset_name = "zurich_mobility_warehouse"
region       = "europe-west6"
```

The values should match the values used in `.env`:

```text
.env GCP_PROJECT_ID  = terraform.tfvars project
.env GCS_BUCKET_NAME = terraform.tfvars bucket_name
.env BQ_DATASET_ID   = terraform.tfvars dataset_name
```

The file `terraform.tfvars` must not be committed.

---

### 8.8 Provision Cloud Infrastructure with Terraform

From inside the `terraform/` folder, run:

```bash
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

Confirm the apply step when Terraform asks for approval.

Terraform creates:

```text
Google Cloud Storage bucket
BigQuery dataset
```

After Terraform has completed successfully, go back to the project root:

```bash
cd ..
```

---

### 8.9 Build the Custom Airflow Image

The project uses a custom Airflow image because the default Airflow image does not include all required Google Cloud Python packages.

Build the image:

```bash
docker build -f Dockerfile.airflow -t deng_airflow:2.9.3 .
```

---

### 8.10 Start Docker Compose

Start the local environment:

```bash
docker compose up -d
```

Check the running services:

```bash
docker compose ps
```

Expected services:

```text
meteo_pgdatabase
meteo_pgadmin
airflow_webserver
airflow_scheduler
```

The `airflow_init` container may show as exited. This is normal after it has initialized the Airflow database and created the Airflow user.

---

### 8.11 Check Environment Variables Inside Airflow

Run:

```bash
docker compose exec airflow-scheduler bash -lc 'echo $GCS_BUCKET_NAME && echo $GCP_PROJECT_ID && echo $BQ_CITY_TABLE_ID && echo $BQ_STATION_TABLE_ID'
```

Expected output:

```text
<your-globally-unique-bucket-name>
<your-gcp-project-id>
mobility_weather_daily
mobility_weather_daily_by_station
```

Also check that the service account key is visible inside the container:

```bash
docker compose exec airflow-scheduler ls -l /opt/airflow/project/terraform/keys
```

Expected file:

```text
my-creds.json
```

---

### 8.12 Check Airflow DAG Imports

Run:

```bash
docker compose exec airflow-scheduler airflow dags list-import-errors
```

Expected output:

```text
No data found
```

Then list the available DAGs:

```bash
docker compose exec airflow-scheduler airflow dags list
```

The following DAGs should be visible:

```text
zurich_mobility_pipeline
cloud_data_lake_ingestion
cloud_warehouse_transformation
```

---

### 8.13 Open Airflow

Open Airflow in the browser:

```text
http://localhost:8086
```

Log in with the credentials from the local `.env` file:

```text
AIRFLOW_USERNAME
AIRFLOW_PASSWORD
```

---

### 8.14 Run the Cloud Data Lake Ingestion DAG

In Airflow, enable and trigger the DAG:

```text
cloud_data_lake_ingestion
```

Expected successful tasks:

```text
upload_traffic_2025_to_gcs
upload_traffic_2026_to_gcs
upload_weather_2025_to_gcs
upload_weather_2026_to_gcs
```

This DAG downloads the raw source data and uploads it to the reviewer’s own Google Cloud Storage bucket.

The expected GCS structure is:

```text
raw/traffic/year=2025/traffic_zurich_2025.csv
raw/traffic/year=2026/traffic_zurich_2026.csv
raw/weather/year=2025/weather_zurich_2025.csv
raw/weather/year=2026/weather_zurich_2026.csv
```

---

### 8.15 Run the Cloud Warehouse Transformation DAG

After the data lake ingestion DAG has completed successfully, enable and trigger:

```text
cloud_warehouse_transformation
```

Expected successful task:

```text
transform_gcs_to_bigquery
```

This DAG reads the raw files from Google Cloud Storage, transforms the data and loads two analytical tables into BigQuery:

```text
mobility_weather_daily
mobility_weather_daily_by_station
```

---

### 8.16 Verify Cloud Storage Output

Open Google Cloud Console and navigate to:

```text
Cloud Storage → Buckets → <your-globally-unique-bucket-name>
```

The following files should exist:

```text
raw/traffic/year=2025/traffic_zurich_2025.csv
raw/traffic/year=2026/traffic_zurich_2026.csv
raw/weather/year=2025/weather_zurich_2025.csv
raw/weather/year=2026/weather_zurich_2026.csv
```

Optional terminal verification:

```bash
docker compose exec airflow-scheduler python -c "from google.cloud import storage; import os; c=storage.Client(); b=c.bucket(os.environ['GCS_BUCKET_NAME']); [print(x.name, x.size) for x in b.list_blobs(prefix='raw/')]"
```

---

### 8.17 Verify BigQuery Output

Open Google Cloud Console and navigate to:

```text
BigQuery → <your-gcp-project-id> → zurich_mobility_warehouse
```

The following two tables should exist:

```text
mobility_weather_daily
mobility_weather_daily_by_station
```

City-level table verification:

```sql
SELECT
  COUNT(*) AS row_count,
  MIN(date) AS min_date,
  MAX(date) AS max_date
FROM `<your-gcp-project-id>.zurich_mobility_warehouse.mobility_weather_daily`;
```

Station-level table verification:

```sql
SELECT
  COUNT(*) AS row_count,
  COUNT(DISTINCT station_id) AS station_count,
  MIN(date) AS min_date,
  MAX(date) AS max_date
FROM `<your-gcp-project-id>.zurich_mobility_warehouse.mobility_weather_daily_by_station`;
```

Preview the station-level table:

```sql
SELECT *
FROM `<your-gcp-project-id>.zurich_mobility_warehouse.mobility_weather_daily_by_station`
ORDER BY date, station_id
LIMIT 20;
```

---

### 8.18 Stop the Project

To stop the local Docker environment:

```bash
docker compose down
```

This stops the containers but keeps Docker volumes.

---

### 8.19 Full Local Reset

To fully reset the local Docker environment:

```bash
docker compose down -v
```

Warning: this deletes local Docker volumes, including the local PostgreSQL database.

After a full reset, restart the Docker environment and rerun the required Airflow DAGs.

---

### 8.20 Important Notes

* This guide assumes that the reviewer reproduces the project in their own Google Cloud project.
* Terraform is required because the reviewer creates the cloud infrastructure in their own project.
* The reviewer must choose their own globally unique Cloud Storage bucket name.
* The values in `.env` and `terraform/terraform.tfvars` must match.
* The service account key must be stored locally as `terraform/keys/my-creds.json`.
* The files `.env`, `terraform.tfvars`, Terraform state files and service account keys must not be committed.
* The Airflow DAGs create or overwrite the BigQuery output tables during execution.


## 9. Cloud Infrastructure with Terraform

The project contains a Terraform setup for Google Cloud.

Terraform provisions:

- a Google Cloud Storage bucket as a data lake
- a BigQuery dataset as a data warehouse

Created resources:

```text
Google Cloud Project:
projectmobile-494518

Cloud Storage Bucket:
project-mobile-zurich-data-lake-494518

BigQuery Dataset:
zurich_mobility_warehouse
```

The Terraform files are stored in:

```text
terraform/
├── main.tf
├── variables.tf
├── terraform.tfvars.example
└── .terraform.lock.hcl
```

Local files such as credentials, Terraform state and private variable files are intentionally excluded from GitHub.

### 9.1 Terraform files on GitHub

The following files are part of the repository:

```text
terraform/main.tf
terraform/variables.tf
terraform/terraform.tfvars.example
terraform/.terraform.lock.hcl
```

The following files must not be committed:

```text
terraform/terraform.tfvars
terraform/terraform.tfstate
terraform/terraform.tfstate.backup
terraform/.terraform/
terraform/keys/
terraform/keys/my-creds.json
```

These files are ignored via `.gitignore`.

### 9.2 Running Terraform

To provision or update the cloud resources:

```bash
cd terraform
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```
---
## 10. Google Cloud Access and Credentials

The repository does not include Google Cloud credentials.

Reviewers who only inspect the code or verify results in the Google Cloud Console need access to the Google Cloud project:

```text
projectmobile-494518
```
A local service account JSON key is only required to:
- run Terraform
- execute the cloud Airflow DAGs locally
- upload data to Google Cloud Storage
- load data into BigQuery

The key file must be stored locally as:

```text
terraform/keys/my-creds.json
```

This file must never be committed to GitHub.

The `.env` file should point to the key inside the Airflow container:

```text
GOOGLE_APPLICATION_CREDENTIALS=/opt/airflow/project/terraform/keys/my-creds.json
```
---

## 11. Environment Variables and Secrets

The project uses `.env.example` to document required environment variables.

Each user creates a local `.env` file: 

```bash
cp .env.example .env
```

The `.env` file contains local settings for PostgreSQL, pgAdmin, Airflow, Google Cloud and BigQuery.

The `.env` file and Google credentials are local only and must not be committed.

Not committed:

```text
.env
terraform/keys/my-creds.json
terraform/terraform.tfvars
terraform/terraform.tfstate
terraform/terraform.tfstate.backup
terraform/.terraform/
```
---

## 12. Repository Structure

```text
DENG_Mobility/
│
├── airflow/
│   └── dags/
│       ├── zurich_pipeline.py
│       ├── cloud_data_lake_ingestion.py
│       └── cloud_warehouse_transformation.py
│
├── cloud/
│   ├── ingest_to_gcs.py
│   └── transform_gcs_to_bigquery.py
│
├── data/
│    └── traffic_zurich.csv
│
├── images/
│   ├── airflow_howto.png
│   └── airflow_tasks.png
│
├── presentations/
│   └── DENG_Presentation_Final.pdf
│
├── initdb/
│   └── create_databases.sql
│
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── terraform.tfvars.example
│   └── .terraform.lock.hcl
│
├── .env.example
├── ingest_meteo.py
├── ingest_traffic.py
├── load_meteo.py
├── transform_zurich_daily.py
├── Dockerfile.ingest
├── Dockerfile.airflow
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## 13. Project Presentation

The final project presentation is available here:

[Download the final project presentation](presentations/DENG_Presentation_Final.pdf)

The presentation summarizes the Zurich mobility pipeline, including the local and cloud architecture, Terraform setup, BigQuery transformation, verification steps, and first Looker Studio dashboard insights.

The dashboard shows how the final BigQuery tables can be used to compare bicycle and pedestrian traffic by weather, weekday/weekend, year, month, and location.

---

## 14. Notes and Future Improvements

### Notes

- The final project focuses on Zurich. 
- The local pipeline is kept for reproducibility and development.
- The final cloud pipeline uses Google Cloud Storage as data lake and BigQuery as data warehouse.
- Google Cloud credentials and Terraform state files are intentionally excluded from GitHub.
- The 2026 weather end date is currently configured in the Airflow DAG.
- The cloud pipeline currently refreshes yearly raw files rather than using fully incremental daily ingestion.

### Future Improvements

- For example, add Basel as a second city for comparison.
- Make the 2026 weather end date dynamic based on the Airflow execution date.
- Add incremental loading instead of refreshing full yearly files.
- Build a dashboard on top of the BigQuery tables.
- Add data quality checks before loading into BigQuery.
- Add automated tests for transformation logic.
- Add station metadata enrichment, for example station names or district information.

---

## 15. Authors

- Susanne Pfenninger
- Diego Gonzalez