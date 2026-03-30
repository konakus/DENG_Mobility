
## Quick Start für Teammitglieder

Diese Kurzanleitung zeigt, wie das Projekt von GitHub geklont, gestartet und für SQL-Abfragen vorbereitet wird.

### 1. Repository klonen

```bash
git clone <REPOSITORY-URL>
cd project_mobile
````

### 2. Aktuellen Stand von GitHub holen

Falls das Repository bereits lokal vorhanden ist:

```bash
git pull
```

Falls geprüft werden soll, ob lokale Änderungen vorhanden sind:

```bash
git status
```

### 3. Docker-Umgebung starten

```bash
docker compose up -d
```

Prüfen, ob die Container laufen:

```bash
docker compose ps
```

### 4. Ingestion-Image bauen

```bash
docker build -f Dockerfile.ingest -t project_ingest:dev .
```

### 5. Docker-Netzwerk prüfen

```bash
docker network ls
```

In der Regel heisst das Netzwerk:

```text
project_mobile_default
```


### 6. Meteo-Daten laden

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

### 7. Traffic Zürich laden

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

### 8. Traffic Basel laden

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

### 9. pgAdmin öffnen

Im Browser:

```text
http://localhost:8085
```

### 10. Login in pgAdmin

* **Email**: `admin@admin.com`
* **Passwort**: `admin123`

### 11. PostgreSQL-Server in pgAdmin verbinden

**General**

* **Name**: `meteo-postgres`

**Connection**

* **Host name/address**: `pgdatabase`
* **Port**: `5432`
* **Maintenance database**: `meteo`
* **Username**: `root`
* **Password**: `meteo123`

### 12. SQL-Abfragen ausführen

#### Meteo

```sql
SELECT COUNT(*) FROM historical_weather;
```

#### Traffic Zürich

```sql
SELECT COUNT(*) FROM traffic_data;
```

#### Traffic Basel

```sql
SELECT COUNT(*) FROM traffic_data;
```

#### Aktuelle Datenbank prüfen

```sql
SELECT current_database();
```

### 13. Projekt stoppen

```bash
docker compose down
```

### 14. Wichtig für GitHub-Zusammenarbeit

Vor dem Arbeiten immer zuerst prüfen:

```bash
git pull
```

Nach Änderungen:

```bash
git status
git add .
git commit -m "Beschreibung der Änderung"
git push
```

### 15. Wichtige Hinweise

* **pgAdmin-Login** ist nicht dasselbe wie der PostgreSQL-Login

* **pgAdmin-Weblogin**:

  * `admin@admin.com`
  * `admin123`

* **PostgreSQL-Login**:

  * `root`
  * `meteo123`

* **Lokal vom Terminal aus**:

  * Host: `localhost`
  * Port: `5433`

* **Innerhalb des Docker-Netzwerks**:

  * Host: `pgdatabase`
  * Port: `5432`

```
