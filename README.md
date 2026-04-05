
# Project Mobile – Docker-Based Data Pipeline with PostgreSQL and pgAdmin

## Overview

Project Mobile is a small end-to-end data engineering project built with Docker, PostgreSQL, and pgAdmin.

The goal of this project is to collect data from multiple sources, load it into PostgreSQL, and make it available for SQL-based analysis. The project demonstrates how to set up a reproducible local data pipeline using containerized services and Python-based ingestion scripts.

The pipeline processes the following three data sources:

- **Meteo** – historical weather data retrieved from the Open-Meteo API
- **Traffic Zurich** – traffic data loaded from a CSV file
- **Traffic Basel** – traffic data loaded from a CSV file

The project is based on the general workshop concept of Docker, PostgreSQL, and data ingestion, but it has been adapted into a custom scenario using weather and traffic data for Zurich and Basel.

---

## Objectives

This project demonstrates how to:

- set up a PostgreSQL database with Docker
- manage PostgreSQL and pgAdmin with Docker Compose
- initialize multiple databases automatically
- ingest both API and CSV data
- load data into PostgreSQL using Python
- run ingestion scripts both locally and inside Docker containers
- validate the results with SQL queries

---

## Tech Stack

The project uses the following technologies and tools:

- **Docker**
- **Docker Compose**
- **PostgreSQL 18**
- **pgAdmin 4**
- **Python 3.13**
- **pandas**
- **SQLAlchemy**
- **psycopg2-binary**
- **requests**
- **tqdm**
- **Git / GitHub**

---

## Project Structure

```text
project_mobile/
├── docker-compose.yml
├── Dockerfile.ingest
├── ingest_meteo.py
├── ingest_traffic.py
├── .gitignore
├── README.md
├── initdb/
│   └── create_databases.sql
└── data/
    ├── traffic_zurich.csv
    └── traffic_basel.csv
````

### Key Files

* **docker-compose.yml**
  Starts PostgreSQL and pgAdmin as Docker services.

* **Dockerfile.ingest**
  Builds a Docker image for the ingestion scripts.

* **ingest_meteo.py**
  Loads historical weather data from the Open-Meteo API into PostgreSQL.

* **ingest_traffic.py**
  Loads traffic data from CSV files into PostgreSQL.

* **initdb/create_databases.sql**
  Creates additional databases during PostgreSQL initialization.

* **data/**
  Stores the CSV files for Zurich and Basel.

---

## Databases

The project uses three separate PostgreSQL databases:

* `meteo`
* `traffic_zurich`
* `traffic_basel`

### Why multiple databases?

The databases are separated by data source so that ingestion, testing, and querying can be performed independently.

* `meteo` is created as the default database through the Docker Compose configuration
* `traffic_zurich` and `traffic_basel` are created through the SQL initialization script

---

## Prerequisites

Before starting, make sure the following tools are installed:

* Docker Desktop
* Git

Optional, but recommended:

* Visual Studio Code

---

## Quick Start

### 1. Clone the repository

```bash
git clone <REPOSITORY-URL>
cd project_mobile
```

### 2. Start the services

Run Docker Compose from the project root:

```bash
docker compose up -d
```

To verify that the containers are running:

```bash
docker compose ps
```

Expected containers:

* `meteo_pgdatabase`
* `meteo_pgadmin`

### 3. Open pgAdmin

Open pgAdmin in your browser:

```text
http://localhost:8085
```

Login credentials for pgAdmin:

* **Email:** `admin@admin.com`
* **Password:** `admin123`

> These credentials are only for the pgAdmin web interface, not for PostgreSQL itself.

---

## Connect PostgreSQL in pgAdmin

After logging into pgAdmin, create a new server connection.

### General tab

* **Name:** `meteo-postgres`

### Connection tab

* **Host name/address:** `pgdatabase`
* **Port:** `5432`
* **Maintenance database:** `meteo`
* **Username:** `root`
* **Password:** `meteo123`

### Important networking note

There are two different connection contexts in this project:

#### From pgAdmin inside Docker

Use:

* **Host:** `pgdatabase`
* **Port:** `5432`

#### From your local machine

Use:

* **Host:** `localhost`
* **Port:** `5433`

This difference exists because Docker Compose maps the PostgreSQL container port to your local machine.

---

## Database Initialization

The file `initdb/create_databases.sql` is executed only during the first initialization of PostgreSQL and creates the additional databases:

```sql
CREATE DATABASE traffic_zurich;
CREATE DATABASE traffic_basel;
```

### Important

This script runs only when the PostgreSQL volume is initialized for the first time.

If the databases are missing and you need to rebuild everything from scratch:

```bash
docker compose down -v
docker compose up -d
```

> Warning: `-v` deletes all stored database data.

---

## Data Ingestion

## Meteo Ingestion

Weather data is fetched from the **Open-Meteo API** rather than from a CSV file.

### Coordinates used

For Zurich:

* **Latitude:** `47.3769`
* **Longitude:** `8.5417`

### Example: local execution

```bash
uv run python ingest_meteo.py \
  --user=root \
  --password=meteo123 \
  --host=localhost \
  --port=5433 \
  --db=meteo \
  --table=historical_weather \
  --latitude=47.3769 \
  --longitude=8.5417 \
  --start_date=2025-01-01 \
  --end_date=2025-01-07
```

### What the script does

`ingest_meteo.py`:

* retrieves historical weather data from the Open-Meteo API
* converts the response into a pandas DataFrame
* creates or replaces the target table
* loads the data into PostgreSQL

Target database and table:

* **Database:** `meteo`
* **Table:** `historical_weather`

---

## Traffic Ingestion

Traffic data for Zurich and Basel is loaded from CSV files.

### Example: local execution for Zurich

```bash
uv run python ingest_traffic.py \
  --user=root \
  --password=meteo123 \
  --host=localhost \
  --port=5433 \
  --db=traffic_zurich \
  --table=traffic_data \
  --csv=./data/traffic_zurich.csv
```

### Example: local execution for Basel

```bash
uv run python ingest_traffic.py \
  --user=root \
  --password=meteo123 \
  --host=localhost \
  --port=5433 \
  --db=traffic_basel \
  --table=traffic_data \
  --csv=./data/traffic_basel.csv
```

### What the script does

`ingest_traffic.py`:

* reads a CSV file with pandas
* processes the data in chunks
* creates or replaces the target table
* loads the data into PostgreSQL

---

## Docker Image for Ingestion

The project includes a separate Docker image for running the ingestion scripts.

### `Dockerfile.ingest`

```dockerfile
FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir pandas sqlalchemy psycopg2-binary requests tqdm

COPY ingest_meteo.py /app/ingest_meteo.py
COPY ingest_traffic.py /app/ingest_traffic.py
COPY data /app/data

ENTRYPOINT ["python"]
```

### Build the ingestion image

```bash
docker build -f Dockerfile.ingest -t project_ingest:dev .
```

Once the image has been built successfully, it can be used for all ingestion runs.

---

## Docker Network

Because the ingestion container must run in the same Docker network as PostgreSQL, first inspect the available networks:

```bash
docker network ls
```

In most cases, the network name will be:

```text
project_mobile_default
```

If the project folder has a different name, the network name may differ as well.

---

## Run Ingestion Inside Docker

## Meteo

```bash
docker run --rm --network=project_mobile_default project_ingest:dev /app/ingest_meteo.py \
  --user=root \
  --password=meteo123 \
  --host=pgdatabase \
  --port=5432 \
  --db=meteo \
  --table=historical_weather \
  --latitude=47.3769 \
  --longitude=8.5417 \
  --start_date=2025-01-01 \
  --end_date=2025-01-07
```

## Traffic Zurich

```bash
docker run --rm --network=project_mobile_default project_ingest:dev /app/ingest_traffic.py \
  --user=root \
  --password=meteo123 \
  --host=pgdatabase \
  --port=5432 \
  --db=traffic_zurich \
  --table=traffic_data \
  --csv=/app/data/traffic_zurich.csv
```

## Traffic Basel

```bash
docker run --rm --network=project_mobile_default project_ingest:dev /app/ingest_traffic.py \
  --user=root \
  --password=meteo123 \
  --host=pgdatabase \
  --port=5432 \
  --db=traffic_basel \
  --table=traffic_data \
  --csv=/app/data/traffic_basel.csv
```

### Important

Inside Docker, do **not** use `localhost:5433`.
Use:

* **Host:** `pgdatabase`
* **Port:** `5432`

This is because the connection happens inside the Docker network.

---

## SQL Validation

After ingestion, you can verify that the data was loaded successfully.

### Meteo

```sql
SELECT COUNT(*) FROM historical_weather;
```

### Traffic Zurich

```sql
SELECT COUNT(*) FROM traffic_data;
```

### Traffic Basel

```sql
SELECT COUNT(*) FROM traffic_data;
```

### Show current database

```sql
SELECT current_database();
```

---

## Access via `psql`

### Connect to `meteo`

```bash
docker exec -it meteo_pgdatabase psql -U root -d meteo
```

### Connect to `traffic_zurich`

```bash
docker exec -it meteo_pgdatabase psql -U root -d traffic_zurich
```

### Connect to `traffic_basel`

```bash
docker exec -it meteo_pgdatabase psql -U root -d traffic_basel
```

### Useful `psql` commands

Show tables:

```sql
\dt
```

Switch database:

```sql
\c meteo
\c traffic_zurich
\c traffic_basel
```

Reset incomplete input:

```sql
\r
```

Quit `psql`:

```sql
\q
```

---

## Local vs Docker Execution

### Local execution

The script runs directly on your machine:

* **Host:** `localhost`
* **Port:** `5433`

Example:

```bash
uv run python ingest_meteo.py ...
```

### Docker execution

The script runs inside a container within the Docker Compose network:

* **Host:** `pgdatabase`
* **Port:** `5432`

Example:

```bash
docker run --rm --network=project_mobile_default project_ingest:dev /app/ingest_meteo.py ...
```

---

## Stopping the Project

Stop the containers:

```bash
docker compose down
```

Stop the containers and remove volumes:

```bash
docker compose down -v
```

> Warning: `docker compose down -v` deletes all databases and tables.

---

## Common Issues and Fixes

### pgAdmin does not open

Check whether the containers are running:

```bash
docker compose ps
```

If needed, restart them:

```bash
docker compose up -d
```

---

### `root` does not work on the pgAdmin login page

**Reason:**
`root` is a PostgreSQL database user, not a pgAdmin web user.

**Solution:**
Log in with:

* `admin@admin.com`
* `admin123`

---

### `relation "..." does not exist`

Example:

```text
ERROR: relation "historical_weather" does not exist
```

**Meaning:**

* the table has not been loaded yet
* or it was deleted after `docker compose down -v`

**Solution:**
Run the ingestion again.

---

### `database "..." does not exist`

Example:

```text
FATAL: database "traffic_zurich" does not exist
```

**Meaning:**

* the initialization script did not run correctly
* or the volume was not fresh

**Solution:**

```bash
docker compose down -v
docker compose up -d
```

---

### `password authentication failed for user "root"`

**Meaning:**
The password does not match the PostgreSQL configuration.

**Solution:**

* check the Compose file
* check the pgAdmin server connection
* check the ingestion command arguments

---

### `FileNotFoundError` for CSV files

**Meaning:**
The specified file path is incorrect.

**Solution:**

* verify that the CSV files are in the `data/` folder
* check the filenames
* confirm the paths used in the command

---

### `ModuleNotFoundError: No module named 'pandas'`

**Meaning:**
The script was started in the wrong Python environment.

**Solution for local execution:**

```bash
uv add pandas sqlalchemy psycopg2-binary requests tqdm
uv run python ingest_traffic.py ...
```

Inside Docker, this issue is handled by `Dockerfile.ingest`.

---

### `idna codec / label too long` in pgAdmin

**Meaning:**
Multiple values were entered into a single field, usually the **Host** field.

**Solution:**

* enter only `pgdatabase` in the Host field
* place all other values into their correct fields

---

### `zsh: command not found: c`

**Meaning:**
A `psql` command such as `\c` was entered in the regular shell.

**Solution:**

* connect to PostgreSQL with `psql` first
* use `\c` only inside the `psql` session

---

## Repository Notes

The following files and folders should be included in the repository:

* `docker-compose.yml`
* `Dockerfile.ingest`
* `ingest_meteo.py`
* `ingest_traffic.py`
* `initdb/create_databases.sql`
* `data/traffic_zurich.csv`
* `data/traffic_basel.csv`
* `README.md`
* `.gitignore`

Do not include:

* `.venv/`
* `__pycache__/`
* `.DS_Store`
* local Docker volumes
* temporary files

### Example `.gitignore`

```gitignore
.venv/
__pycache__/
*.pyc
.DS_Store
*.parquet
```

---

## Example Workflow for Team Members

A team member can set up and run the project as follows:

1. Clone the repository
2. Change into the project folder
3. Start Docker Compose
4. Build the ingestion image
5. Load Meteo data
6. Load Traffic Zurich data
7. Load Traffic Basel data
8. Validate the results with SQL

### Short command sequence

```bash
git clone <REPOSITORY-URL>
cd project_mobile
docker compose up -d
docker build -f Dockerfile.ingest -t project_ingest:dev .
docker network ls
```

Then run the documented `docker run` commands for Meteo, Zurich, and Basel.

---

## Summary

This project provides a small but complete Docker-based data pipeline that:

* starts PostgreSQL and pgAdmin with Docker Compose
* initializes multiple databases
* loads weather data from an API into PostgreSQL
* loads traffic data from CSV files into PostgreSQL
* supports ingestion both locally and inside Docker
* allows SQL-based validation of the loaded data

It covers the core concepts of a small data engineering workflow using Docker and PostgreSQL.

---

## Authors

**Susanne Pfenninger**
**Diego Gonzalez**

---
