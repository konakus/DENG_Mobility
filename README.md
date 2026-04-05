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

```bash
docker compose up -d
```

---

### 2. Access Services

| Service | URL                   |
| ------- | --------------------- |
| Airflow | http://localhost:8086 |
| pgAdmin | http://localhost:8085 |

---

### 3. Configure pgAdmin

Create a new server with:

* Host: `postgres`
* Port: `5432`
* User: `postgres`
* Password: `postgres`

---

## Running the Pipeline

### 1. Open Airflow UI

Go to:

```
http://localhost:8080
```

---

### 2. Enable the DAG

* Find: `zurich_mobility_pipeline`
* Toggle it ON (unpause)

---

### 3. Trigger the DAG

Click play button

---

### 4. Monitor execution

* All tasks should turn **green**
* Tasks:

  * ingest_weather
  * ingest_traffic
  * transform_daily

---

## Data Output

The final table:

```
mobility_weather_daily
```

Contains:

* date
* avg_temperature
* total_precipitation
* avg_windspeed
* traffic metrics (velo, fuss, etc.)
* calendar features (weekday, weekend, month)

---

## Verification

Run in pgAdmin (in the Database: traffic_zurich):

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

To reproduce the project:

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
* The pipeline is designed to be fully reproducible

---

## Future Improvements

* Extend to multiple cities (e.g., Basel)
* Add more data sources
* Improve feature engineering
* Build dashboards on top of the dataset

---

## Authors

* Susanne Pfenninger
* Diego Gonzalez
