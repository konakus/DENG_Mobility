# DENG_Mobility Project – Zurich Pipeline (Final)

## Table of Contents

1. [Overview](#1-overview)
2. [Use Case](#2-use-case)
3. [Architecture](#3-architecture)
4. [Local Setup and Airflow Pipeline](#4-local-setup-and-airflow-pipeline)
5. [Ingestion and Transformation Logic](#5-ingestion-and-transformation-logic)
6. [Data Output and Verification](#6-data-output-and-verification)
7. [Reproducibility, Reset and Restart](#7-reproducibility-reset-and-restart)
8. [Cloud Infrastructure with Terraform](#8-cloud-infrastructure-with-terraform)
9. [Google Cloud Credentials and Keys](#9-google-cloud-credentials-and-keys)
10. [Airflow and Cloud Extension](#10-airflow-and-cloud-extension)
11. [Notes](#11-notes)
12. [Future Improvements](#12-future-improvements)
13. [Authors](#13-authors)

This project implements a containerized data pipeline that integrates weather and mobility data to analyze urban traffic patterns in Zurich.

## 1. Overview

The project combines weather data from APIs and mobility data from public datasets into a unified, daily aggregated dataset. 

The pipeline integrates:
* Weather data from the [Open-Meteo API](https://open-meteo.com/en/docs/historical-weather-api)
* Traffic data from [Zurich mobility datasets](https://data.stadt-zuerich.ch/dataset/ted_taz_verkehrszaehlungen_werte_fussgaenger_velo)

The data is ingested, transformed, and stored in PostgreSQL, while Apache Airflow orchestrates the pipeline execution.

---

## 2. Use Case

**Persona:** Urban Mobility Analyst

The goal is to analyze how weather conditions influence urban mobility in Zurich.
The user needs a clean, daily aggregated dataset that combines:
* weather conditions
* mobility indicators

### Problem
The data is currently:
*  distributed across multiple sources
*  inconsistent in format
*  not directly usable for analysis

### Solution

The pipeline integrates, cleans, and aggregates the data into a unified dataset.

### What this enables
This allows analysis of patterns such as:
* How precipitation and temperature affect traffic volume
* Differences between weekdays and weekends
* Seasonal mobility trends

**The following architecture and pipeline design implement this use case end-to-end.**

---

## 3. Architecture

### System Architecture (Overview)
```text
Docker Compose
│
├── PostgreSQL (pgdatabase)
│     └── stores raw + transformed data
│
├── pgAdmin
│     └── database UI (http://localhost:8085)
│
├── Airflow
│     └── orchestrates pipeline (http://localhost:8086)
│
└── Ingestion + Transformation (Python)
      ├── ingest_meteo.py
      ├── ingest_traffic.py
      └── transform_zurich_daily.py
```

### Data Flow
```text
         Open-Meteo API        CSV Files
                │                  │
                ▼                  ▼
        ingest_meteo.py    ingest_traffic.py
                │                  │
                └───────┬──────────┘
                        ▼
              PostgreSQL (raw tables)
                        ▼
           transform_zurich_daily.py
                        ▼
           mobility_weather_daily
                        ▼
                   pgAdmin UI
```
### Repository Overview

The most relevant parts of the repository are:

| Component                     | Purpose                                      |
|------------------------------|----------------------------------------------|
| `dags/`                      | Airflow DAG definition                       |
| `ingest_meteo.py`            | Weather data ingestion from API              |
| `ingest_traffic.py`          | Traffic data ingestion from CSV              |
| `transform_zurich_daily.py`  | Data transformation and aggregation          |
| `docker-compose.yml`         | Defines and runs Docker services             |
| `Dockerfile.ingest`          | Builds the ingestion container image         |
| `initdb/`                    | Database initialization scripts              |
| `data/`                      | Input dataset (Zurich traffic CSV)           |
| `terraform/`                 | Google Cloud infrastructure as code          |
| `README.md`                  | Project documentation and instructions       |

### Workflow (Airflow DAG)
```text
ingest_weather
ingest_traffic
        ↓
transform_daily
        ↓
mobility_weather_daily
```

### Project Structure

```text
DENG_Mobility/
│
├── dags/
│   └── zurich_pipeline.py
│
├── ingest_meteo.py
├── ingest_traffic.py
├── transform_zurich_daily.py
│
├── docker-compose.yml
├── Dockerfile.ingest
│
├── initdb/
│   └── create_databases.sql
│
├── data/
│   └── traffic_zurich.csv
│
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   └── terraform.tfvars.example
│
└── README.md
```

---

## 4. Local Setup and Airflow Pipeline

### Setup Instructions

#### 1. Prerequisites

- Docker Desktop installed and running
- (Optional) Python 3.x for manual execution

#### 2. Start the system

```bash
docker compose up -d
```

#### 3. Configure pgAdmin
```text
http://localhost:8085
```

Login-Data:
- Email: admin@admin.com
- PWD: admin123

Create a new server with:

**General**
* **Name:** `meteo-postgres`

**Connection**
* **Host name/address:** `pgdatabase`
* **Port:** `5432`
* **Maintenance database:** `meteo`
* **Username:** `root`
* **Password:** `meteo123`

Note: The project uses multiple databases. `meteo` is used for raw weather data, while `traffic_zurich` stores the transformed and aggregated dataset.

---

### Running the Pipeline

#### 1. Open Airflow UI

Go to:

```text
http://localhost:8086
```

* Username: `admin`
* Password: `admin`

---

#### 2. Enable and Trigger the DAG

* Find the instance: `zurich_mobility_pipeline`
1) Toggle it ON (unpause)
2) Click the play button
3) Click on the DAG name to see the pipeline run

![Screenshot](images/airflow_howto.png)

---

#### 3. Monitor execution

* All of the three tasks should turn **green** after some time.
* Tasks:

  * ingest_weather
  * ingest_traffic
  * transform_daily

![Screenshot](images/airflow_tasks.png)

* If all tasks are **green**, the table is built and can be queried in pgAdmin in the database **traffic_zurich**.

### Manual Execution (Fallback)

If Airflow is not available, the pipeline can be executed manually.  
This approach is mainly intended for debugging or development purposes, while the primary execution is handled via Airflow.

```bash
python ingest_meteo.py
python ingest_traffic.py
python transform_zurich_daily.py
```

---

## 5. Ingestion and Transformation Logic

### Ingestion Pipeline

The ingestion pipeline ensures that raw data is reliably loaded into PostgreSQL as the foundation for downstream transformations.

#### Scripts
- ingest_meteo.py → API ingestion
- ingest_traffic.py → CSV ingestion

#### Characteristics
The ingestion pipeline is batch-based, modular, reusable, and well-documented, ensuring maintainability and flexibility.

#### Process
The ingestion process fetches data from APIs and CSV files, converts it into pandas DataFrames, and loads it into PostgreSQL for further analysis.

#### Dockerfile.ingest
`Dockerfile.ingest` is used to build a dedicated Docker image for the ingestion scripts. It provides the required Python environment and dependencies and copies the ingestion files into the container. This allows the ingestion process to run in a reproducible and isolated environment.

---

### Transformations

After ingestion, both datasets undergo transformation and aggregation steps before being stored in the final table. These transformations directly support the use case by enabling daily analysis of mobility patterns under different weather conditions.

#### Weather Data
- Aggregated to a daily level (e.g., average temperature and wind speed)
- Renamed and standardized column names
- Rounded numerical values to one decimal place for consistency

#### Traffic Data
- Selected relevant columns (e.g., location, date, traffic counts)
- Standardized column names and formats
- Ensured correct data types (e.g., dates, numeric values)

#### Final Dataset
- Joined weather and traffic data on the date field
- Created a unified dataset for downstream analysis
- Ensured a clean and consistent schema across all columns

The resulting dataset is structured, consistent, and ready for analysis and visualization.


---

## 6. Data Output and Verification

### Data Output

The final table: **mobility_weather_daily**


Contains:

* date
* avg_temperature
* total_precipitation
* avg_windspeed
* traffic metrics (velo, fuss, etc.)
* calendar features (weekday, weekend, month)

---

### Verification

Run in pgAdmin (in the Database: **traffic_zurich**):

```sql
SELECT COUNT(*) FROM mobility_weather_daily;
```

Expected:

```
365 rows
```

---

## 7. Reproducibility, Reset and Restart

This section provides a short checklist for reviewers to run and verify the local pipeline.

### 7.1 Reproduce the local pipeline

1. Clone the repository:

```bash
   git clone https://github.com/konakus/DENG_Mobility.git
   cd DENG_Mobility
```

2. Start the Docker environment:

   ```bash
   docker compose up -d
   ```
3. Open Airflow
```
   http://localhost:8086
```

4. Trigger DAG
```
   zurich_mobility_pipeline
```

5. Wait until all tasks are green:
```
   ingest_weather
   ingest_traffic
   transform_daily
```

6. Open pgAdmin:
```
   http://localhost:8085
```

7. Validate the result in the database traffic_zurich:

```sql
   SELECT COUNT(*) FROM mobility_weather_daily;
```

   Expected result:
```
   365 rows
```


### 7.2 Stop the project 

```bash
docker compose down
```
This stops the containers but keeps the stored data in Docker volumes.


### 7.3 Reset the project completely

```bash
docker compose down -v
```

> Warning: This deletes all Docker volumes, including the PostgreSQL database.

After a full reset (`-v`), restart the Docker environment and rerun the Airflow DAG to recreate the data.

### 7.4 Restart the project

```bash
docker compose up -d
```
---


## 8. Cloud Infrastructure with Terraform

In addition to the local Docker/PostgreSQL setup, the project contains a minimal Terraform setup for Google Cloud.

Terraform provisions:

* a Google Cloud Storage bucket as a data lake
* a BigQuery dataset as a data warehouse

Created resources:

```text
Cloud Storage Bucket:
project-mobile-zurich-data-lake-494518

BigQuery Dataset:
zurich_mobility_warehouse

Google Cloud Project:
projectmobile-494518
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

### Terraform files on GitHub

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

---

## 9. Google Cloud Credentials and Keys

Terraform needs credentials to create or modify resources in Google Cloud.

### 9.1 For project contributors

Team members who want to run Terraform or modify the Google Cloud infrastructure need their own Google Cloud service account key.

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
5. Required roles for this simple Terraform setup:

   ```text
   Storage Admin
   BigQuery Admin
   ```

6. Create a JSON key:

   ```text
   Service Account → Keys → Add key → Create new key → JSON
   ```

7. Store the downloaded key locally as:

   ```text
   terraform/keys/my-creds.json
   ```

8. Create the local Terraform variable file:

   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   ```

9. The local `terraform.tfvars` should contain:

   ```hcl
   credentials = "keys/my-creds.json"
   ```

10. Run Terraform:

   ```bash
   terraform init
   terraform fmt
   terraform validate
   terraform plan
   terraform apply
   ```

The key file is local only and must never be uploaded to GitHub.

### 9.2 For people who only want to view the project

People who only want to review the code or documentation do not need a Google Cloud key.

They can clone the repository and inspect the code without creating credentials:

```bash
git clone https://github.com/konakus/DENG_Mobility.git
cd DENG_Mobility
```

They only need a key if they want to run Terraform or deploy/change resources on Google Cloud.

---
## 10. Airflow and Cloud Extension

The current Airflow pipeline runs locally and stores the final table `mobility_weather_daily` in PostgreSQL.

The Terraform setup already provides the required cloud resources. In a next step, the existing Airflow DAG can be extended with cloud export tasks:


```text
transform_daily
        ↓
export_to_gcs
        ↓
load_to_bigquery
```
Google Cloud credentials must never be committed to GitHub.

Users who only review the code or run the local Docker/Airflow pipeline do not need a Google Cloud key.

---


## 11. Notes (noch anpassen)

* This project focuses on the Zurich mobility and weather pipeline.
* Basel-related components are not used.
* The local pipeline uses Docker, PostgreSQL and Airflow.
* The cloud infrastructure is provisioned with Terraform on Google Cloud.
* The pipeline is designed to be reproducible.


---

## 12. Future Improvements (noch anpassen)

* Extend the Airflow DAG with tasks for exporting data to Cloud Storage and loading it into BigQuery.
* Extend to multiple cities (e.g., Basel).
* Add more data sources.
* Improve feature engineering.
* Build dashboards on top of the BigQuery dataset.

---

## 13. Authors

* Susanne Pfenninger
* Diego Gonzalez

