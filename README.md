# DENG Mobility Project – Zurich Pipeline (Final)

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
10. [Google Cloud Credentials and Keys](#10-google-cloud-credentials-and-keys)
11. [Environment Variables and Secrets](#11-environment-variables-and-secrets)
12. [Repository Structure](#12-repository-structure)
13. [Notes and Future Improvements](#13-notes-and-future-improvements)
14. [Authors](#14-authors)

---

## 1. Overview

This project implements an end-to-end batch data pipeline for Zurich mobility and weather data.

The pipeline combines:

- Zurich pedestrian and bicycle traffic data from the Stadt Zürich Open Data portal
- Historical weather data from the Open-Meteo API

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
│     └── local database UI
│
├── Airflow
│     └── orchestrates the local batch pipeline
│
└── Python scripts
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

The project contains three Airflow DAGs:

| DAG | Purpose |
|---|---|
| `zurich_mobility_pipeline` | Local PostgreSQL pipeline |
| `cloud_data_lake_ingestion` | Loads raw traffic and weather data into Google Cloud Storage |
| `cloud_warehouse_transformation` | Reads raw data from GCS, transforms it and loads it into BigQuery |

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

It loads weather and traffic data into PostgreSQL, transforms them, and creates a local final table.

### 4.1 Start the local Docker environment

Prerequisites:

- Docker Desktop installed and running
- Git installed
- A local `.env` file based on `.env.example`

Start the system:

```bash
docker compose up -d
```

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

Enable and trigger the DAG:

```text
zurich_mobility_pipeline
```

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

Run:

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

The Airflow DAG

```text
cloud_data_lake_ingestion
```

loads raw source data into the Google Cloud Storage data lake.

It uploads the following files:

```text
raw/traffic/year=2025/traffic_zurich_2025.csv
raw/traffic/year=2026/traffic_zurich_2026.csv
raw/weather/year=2025/weather_zurich_2025.csv
raw/weather/year=2026/weather_zurich_2026.csv
```

The target bucket is configured via the environment variable:

```text
GCS_BUCKET_NAME
```

In the current project setup, the bucket is:

```text
project-mobile-zurich-data-lake-494518
```

The 2025 files represent the complete reference year.  
The 2026 files represent the current year and can be refreshed regularly through the scheduled Airflow DAG.

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

### 5.3 Final BigQuery Tables

The pipeline creates two BigQuery tables.

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
one row per date and station
```

Purpose:

- station-level mobility analysis
- spatial comparison between counting stations
- more detailed analysis using `station_id`, `east_coord` and `north_coord`

### 5.4 BigQuery Partitioning and Clustering

Both BigQuery tables are partitioned by:

```text
date
```

This is useful because most analytical queries filter or aggregate data by time.

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

The following features are calculated per day and station:

- `station_id`
- `east_coord`
- `north_coord`
- total bicycle traffic per station and day
- total pedestrian traffic per station and day
- daily weather indicators
- calendar features

This table allows more detailed spatial analysis while preserving the simpler city-level table for high-level monitoring.

### 6.5 Final Join and Calendar Features

Weather and traffic data are joined on the date field.

Additional calendar features are added:

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

This section explains how another person can reproduce the project.

### 8.1 Clone the repository

```bash
git clone https://github.com/konakus/DENG_Mobility.git
cd DENG_Mobility
```

### 8.2 Create the local `.env` file

The repository includes an example environment file:

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

Then adjust the values in `.env` if needed.

The `.env` file is local only and must not be committed.

### 8.3 Required Google Cloud key

The repository does not include Google Cloud credentials.

To run the cloud pipeline, create or obtain a service account JSON key and store it locally as:

```text
terraform/keys/my-creds.json
```

This file must never be committed to GitHub.

The `.env` file should contain:

```text
GOOGLE_APPLICATION_CREDENTIALS=/opt/airflow/project/terraform/keys/my-creds.json
```

This is the path inside the Airflow container.

### 8.4 Build the custom Airflow image

The project uses a custom Airflow image because the default Airflow image does not include all required Google Cloud Python packages.

Build the image:

```bash
docker build -f Dockerfile.airflow -t deng_airflow:2.9.3 .
```

### 8.5 Start Docker Compose

```bash
docker compose up -d
```

Check running services:

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

### 8.6 Check environment variables inside Airflow

Run:

```bash
docker compose exec airflow-scheduler bash -lc 'echo $GCS_BUCKET_NAME && echo $BQ_CITY_TABLE_ID && echo $BQ_STATION_TABLE_ID'
```

Expected output:

```text
project-mobile-zurich-data-lake-494518
mobility_weather_daily
mobility_weather_daily_by_station
```

### 8.7 Open Airflow

```text
http://localhost:8086
```

Login with the credentials from the local `.env` file:

```text
AIRFLOW_USERNAME
AIRFLOW_PASSWORD
```

### 8.8 Run the cloud data lake ingestion DAG

In Airflow, enable and trigger:

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

### 8.9 Run the cloud warehouse transformation DAG

In Airflow, enable and trigger:

```text
cloud_warehouse_transformation
```

Expected successful task:

```text
transform_gcs_to_bigquery
```

This task creates or refreshes both BigQuery tables:

```text
mobility_weather_daily
mobility_weather_daily_by_station
```

### 8.10 Verify the result in BigQuery

City-level table:

```sql
SELECT
  COUNT(*) AS row_count,
  MIN(date) AS min_date,
  MAX(date) AS max_date
FROM `projectmobile-494518.zurich_mobility_warehouse.mobility_weather_daily`;
```

Station-level table:

```sql
SELECT
  COUNT(*) AS row_count,
  COUNT(DISTINCT station_id) AS station_count,
  MIN(date) AS min_date,
  MAX(date) AS max_date
FROM `projectmobile-494518.zurich_mobility_warehouse.mobility_weather_daily_by_station`;
```

### 8.11 Stop the project

```bash
docker compose down
```

This stops the containers but keeps Docker volumes.

### 8.12 Full reset

```bash
docker compose down -v
```

Warning: This deletes local Docker volumes, including the local PostgreSQL database.

After a full reset, restart the Docker environment and rerun the required Airflow DAGs.

---

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

## 10. Google Cloud Credentials and Keys

Terraform and the cloud pipeline need credentials to access Google Cloud.

### 10.1 For project contributors

Team members who want to run Terraform or execute the cloud pipeline need their own Google Cloud service account key.

Steps:

1. Open Google Cloud Console.
2. Select the project:

   ```text
   ProjectMobile
   projectmobile-494518
   ```

3. Go to:

   ```text
   IAM & Admin → Service Accounts
   ```

4. Create or use a service account with the required permissions.

5. Required roles for the full project:

   ```text
   Storage Admin
   BigQuery Admin
   Service Account User
   ```

6. To create service account keys, the user also needs:

   ```text
   Service Account Key Admin
   ```

7. Create a JSON key:

   ```text
   Service Account → Keys → Add key → Create new key → JSON
   ```

8. Store the downloaded key locally as:

   ```text
   terraform/keys/my-creds.json
   ```

9. Create the local Terraform variable file:

   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   ```

10. The local `terraform.tfvars` should contain:

   ```hcl
   credentials = "keys/my-creds.json"
   ```

The key file is local only and must never be uploaded to GitHub.

### 10.2 For people who only want to review the code

People who only want to review the code or documentation do not need a Google Cloud key.

They can clone the repository and inspect the code without creating credentials.

They only need a key if they want to:

- run Terraform
- execute the cloud Airflow DAGs
- upload data to Google Cloud Storage
- load data into BigQuery

---

## 11. Environment Variables and Secrets

The project uses a `.env.example` file to document required environment variables.

A local `.env` file must be created from `.env.example` before running Docker Compose.

The `.env` file contains local configuration such as:

- PostgreSQL user and password
- pgAdmin login values
- Airflow UI login values
- Google Cloud project and bucket names
- BigQuery dataset and table names
- path to the local Google Cloud service account key inside the container

The `.env` file must not be committed.

### 11.1 Why this is done

Credentials and local environment-specific values should not be hardcoded directly into Docker Compose files, Airflow DAGs or Bash commands.

Instead:

- example values are documented in `.env.example`
- local values are stored in `.env`
- Docker Compose injects them into the containers
- Airflow DAGs read them as environment variables

This improves reproducibility while avoiding committing local secrets.

### 11.2 Important files

Committed:

```text
.env.example
```

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
│   ├── traffic_zurich.csv
│   └── traffic_basel.csv
│
├── images/
│   ├── airflow_howto.png
│   └── airflow_tasks.png
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

## 13. Notes and Future Improvements

### Notes

- The final project focuses on Zurich.
- Basel data exists in the repository but is not part of the final pipeline.
- The local pipeline is kept for reproducibility and development.
- The final cloud pipeline uses Google Cloud Storage as data lake and BigQuery as data warehouse.
- Google Cloud credentials and Terraform state files are intentionally excluded from GitHub.
- The 2026 weather end date is currently configured in the Airflow DAG.
- The cloud pipeline currently refreshes yearly raw files rather than using fully incremental daily ingestion.

### Future Improvements

- Add Basel as a second city for comparison.
- Make the 2026 weather end date dynamic based on the Airflow execution date.
- Add incremental loading instead of refreshing full yearly files.
- Build a dashboard on top of the BigQuery tables.
- Add data quality checks before loading into BigQuery.
- Add automated tests for transformation logic.
- Add station metadata enrichment, for example station names or district information.

---

## 14. Authors

- Susanne Pfenninger
- Diego Gonzalez