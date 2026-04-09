# DENG Mobility Project – Zurich Pipeline (Midterm)

This project implements a containerized data pipeline that integrates weather and mobility data to analyze urban traffic patterns in Zurich.

## Overview

The project combines weather data from APIs and mobility data from public datasets into a unified, daily aggregated dataset. 

The pipeline integrates:
* Weather data from the [Open-Meteo API](https://open-meteo.com/en/docs/historical-weather-api)
* Traffic data from [Zurich mobility datasets](https://data.stadt-zuerich.ch/dataset/ted_taz_verkehrszaehlungen_werte_fussgaenger_velo)

The data is ingested, transformed, and stored in PostgreSQL, while Apache Airflow orchestrates the pipeline execution.

---

## Use Case

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

## Architecture

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
project_mobile/
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
└── README.md
```
---
## Ingestion Pipeline

The ingestion pipeline ensures that raw data is reliably loaded into PostgreSQL as the foundation for downstream transformations.

### Scripts
- ingest_meteo.py → API ingestion
- ingest_traffic.py → CSV ingestion

### Characteristics
The ingestion pipeline is batch-based, modular, reusable, and well-documented, ensuring maintainability and flexibility.

### Process
The ingestion process fetches data from APIs and CSV files, converts it into pandas DataFrames, and loads it into PostgreSQL for further analysis.

### Dockerfile.ingest
`Dockerfile.ingest` is used to build a dedicated Docker image for the ingestion scripts. It provides the required Python environment and dependencies and copies the ingestion files into the container. This allows the ingestion process to run in a reproducible and isolated environment.

---

## Transformations

After ingestion, both datasets undergo transformation and aggregation steps before being stored in the final table. These transformations directly support the use case by enabling daily analysis of mobility patterns under different weather conditions.

### Weather Data
- Aggregated to a daily level (e.g., average temperature and wind speed)
- Renamed and standardized column names
- Rounded numerical values to one decimal place for consistency

### Traffic Data
- Selected relevant columns (e.g., location, date, traffic counts)
- Standardized column names and formats
- Ensured correct data types (e.g., dates, numeric values)

### Final Dataset
- Joined weather and traffic data on the date field
- Created a unified dataset for downstream analysis
- Ensured a clean and consistent schema across all columns

The resulting dataset is structured, consistent, and ready for analysis and visualization.

---

## Setup Instructions

### 1. Prerequisites

- Docker Desktop installed and running
- (Optional) Python 3.x for manual execution

### 2. Start the system

```bash
docker compose up -d
```

### 3. Configure pgAdmin
```text
http://localhost:8085
```


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

## Running the Pipeline

### 1. Open Airflow UI

Go to:

```text
http://localhost:8086
```

* Username: `admin`
* Password: `admin`

---

### 2. Enable and Trigger the DAG

* Find the instance: `zurich_mobility_pipeline`
1) Toggle it ON (unpause)
2) Click the play button
3) Click on the DAG name to see the pipeline run

![Screenshot](images/airflow_howto.png)

---

### 3. Monitor execution

* All of the three tasks should turn **green** after some time.
* Tasks:

  * ingest_weather
  * ingest_traffic
  * transform_daily

![Screenshot](images/airflow_tasks.png)

* If all tasks are **green**, the table is built and can be queried in pgAdmin in the database **traffic_zurich**.

---

## Data Output

The final table: **mobility_weather_daily**


Contains:

* date
* avg_temperature
* total_precipitation
* avg_windspeed
* traffic metrics (velo, fuss, etc.)
* calendar features (weekday, weekend, month)

---

## Verification

Run in pgAdmin (in the Database: **traffic_zurich**):

```sql
SELECT COUNT(*) FROM mobility_weather_daily;
```

Expected:

```
365 rows
```

---
## Manual Execution (Fallback)

If Airflow is not available, the pipeline can be executed manually.  
This approach is mainly intended for debugging or development purposes, while the primary execution is handled via Airflow.

```bash
python ingest_meteo.py
python ingest_traffic.py
python transform_zurich_daily.py
```

---

## Reproducibility

To reproduce the project (overview):

1. Clone repository
2. Run:

   ```bash
   docker compose up -d
   ```
3. Open Airflow
4. Trigger DAG
5. Validate results in pgAdmin

---

## Reset and Restart the Project

This section describes how to stop, reset, and restart the Docker-based environment.

### Stop the Project

To stop all running containers, use:

```bash
docker compose down
```
This stops and removes the containers but keeps the stored data (volumes).

### Reset the Project
To completely reset the project, including all stored data, use:

```bash
docker compose down -v
```

> Warning: This command deletes all Docker volumes, including the PostgreSQL database.

After a full reset (`-v`), the database is empty.  
The ingestion and transformation steps must be executed again to restore the data.

### Restart the Project
To start the system again after stopping or resetting:
```bash
docker compose up -d
```
This recreates and starts all services defined in the Docker Compose file.

---

## Notes

* This midterm focuses on the Zurich pipeline only
* Basel-related components are not used
* This midterm focuses on the local pipeline (PostgreSQL + Airflow). Cloud storage and Terraform-based infrastructure will be implemented in the final stage.
* The pipeline is designed to be fully reproducible

---

## Future Improvements

* Add cloud-storage (will be done after midterm)
* Extend to multiple cities (e.g., Basel)
* Add more data sources
* Improve feature engineering
* Build dashboards on top of the dataset

---

## Authors

* Susanne Pfenninger
* Diego Gonzalez
