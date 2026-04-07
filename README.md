# DENG Mobility Project – Zurich Pipeline (Midterm)

## Overview

This project implements a data engineering pipeline to analyze how weather influences urban mobility in Zurich.

The pipeline integrates:

* Weather data from the Open-Meteo API
* Traffic data from Zurich mobility datasets

The data is ingested, transformed, and stored in a PostgreSQL database.
Apache Airflow is used to orchestrate the entire workflow.

---

## Use Case

**Persona:** Urban Mobility Analyst

The goal is to provide a clean, daily aggregated dataset that combines:

* weather conditions
* mobility indicators

This allows analysis of patterns such as:

* How precipitation and temperature affects traffic volume
* Differences between weekdays and weekends
* Seasonal mobility trends

---

## Transformations

After ingestion, both datasets undergo basic transformation steps before being stored in the final table.

### Weather Data
- Aggregated to daily level (e.g., average temperature and windspeed)
- Renamed and standardized column names
- Rounded numerical values to one decimal place for consistency

### Traffic Data
- Selected relevant columns (e.g., location, date, traffic counts)
- Standardized column names and formats
- Ensured correct data types (e.g., dates, numeric values)

### Final Dataset
- Joined weather and traffic data on the date field
- Created a unified table for downstream analysis
- Ensured clean and consistent schema across all columns

These transformations ensure that the data is clean, consistent, and ready for analysis and visualization.

---

## Architecture

The project is fully containerized using Docker Compose.

**Components:**

* PostgreSQL → data storage
* pgAdmin → database UI
* Airflow → pipeline orchestration

**Pipeline (Airflow DAG):**

```
ingest_weather  →  
                  → transform_daily → mobility_weather_daily
ingest_traffic  →
```

---

## Project Structure

```
.
├── dags/
│   └── zurich_pipeline.py
├── ingest_meteo.py
├── ingest_traffic.py
├── transform_zurich_daily.py
├── docker-compose.yml
├── Dockerfile.ingest
├── initdb/
└── README.md
```

---

## Setup Instructions

### 1. Start the system

Start Docker Desktop

```bash
docker compose up -d
```

---


### 2. Configure pgAdmin

```
http://localhost:8085
```

Create a new server with:

### General tab

* **Name:** `meteo-postgres`

### Connection tab

* **Host name/address:** `pgdatabase`
* **Port:** `5432`
* **Maintenance database:** `meteo`
* **Username:** `root`
* **Password:** `meteo123`

---

## Running the Pipeline

### 1. Open Airflow UI

Go to:

```
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

![Screenshot](images/Airflow_howto.png)

---

### 4. Monitor execution

* All of the three tasks should turn **green** after some time.
* Tasks:

  * ingest_weather
  * ingest_traffic
  * transform_daily

![Screenshot](images/Airflow_tasks.png)

* If all tasks are **green**, The table is built and can be queried in pgAdmin in the database **traffic_zurich**.

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

```sql
SELECT * FROM mobility_weather_daily LIMIT 10;
```

---

## Manual Execution (Fallback)

If Airflow is not used, scripts can be executed manually:

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
