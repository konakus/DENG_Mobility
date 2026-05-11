from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


BUCKET_NAME = "project-mobile-zurich-data-lake-494518"

TRAFFIC_2025_URL = (
    "https://data.stadt-zuerich.ch/dataset/"
    "ted_taz_verkehrszaehlungen_werte_fussgaenger_velo/download/"
    "2025_verkehrszaehlungen_werte_fussgaenger_velo.csv"
)

TRAFFIC_2026_URL = (
    "https://data.stadt-zuerich.ch/dataset/"
    "ted_taz_verkehrszaehlungen_werte_fussgaenger_velo/download/"
    "2026_verkehrszaehlungen_werte_fussgaenger_velo.csv"
)


default_args = {
    "owner": "deng-team",
    "depends_on_past": False,
    "retries": 1,
}


with DAG(
    dag_id="cloud_data_lake_ingestion",
    default_args=default_args,
    description="Ingest Zurich traffic and weather source data into Google Cloud Storage",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["final", "gcs", "data-lake", "zurich"],
) as dag:

    upload_traffic_2025_to_gcs = BashOperator(
        task_id="upload_traffic_2025_to_gcs",
        bash_command=f"""
        python /opt/airflow/project/cloud/ingest_to_gcs.py \
          --mode=traffic_url \
          --bucket_name={BUCKET_NAME} \
          --source_url="{TRAFFIC_2025_URL}" \
          --destination_blob=raw/traffic/year=2025/traffic_zurich_2025.csv
        """,
    )

    upload_traffic_2026_to_gcs = BashOperator(
        task_id="upload_traffic_2026_to_gcs",
        bash_command=f"""
        python /opt/airflow/project/cloud/ingest_to_gcs.py \
          --mode=traffic_url \
          --bucket_name={BUCKET_NAME} \
          --source_url="{TRAFFIC_2026_URL}" \
          --destination_blob=raw/traffic/year=2026/traffic_zurich_2026.csv
        """,
    )

    upload_weather_2025_to_gcs = BashOperator(
        task_id="upload_weather_2025_to_gcs",
        bash_command=f"""
        python /opt/airflow/project/cloud/ingest_to_gcs.py \
          --mode=weather \
          --bucket_name={BUCKET_NAME} \
          --destination_blob=raw/weather/year=2025/weather_zurich_2025.csv \
          --latitude=47.3769 \
          --longitude=8.5417 \
          --start_date=2025-01-01 \
          --end_date=2025-12-31
        """,
    )

    upload_weather_2026_to_gcs = BashOperator(
        task_id="upload_weather_2026_to_gcs",
        bash_command=f"""
        python /opt/airflow/project/cloud/ingest_to_gcs.py \
          --mode=weather \
          --bucket_name={BUCKET_NAME} \
          --destination_blob=raw/weather/year=2026/weather_zurich_2026.csv \
          --latitude=47.3769 \
          --longitude=8.5417 \
          --start_date=2026-01-01 \
          --end_date=2026-05-05
        """,
    )

    [
        upload_traffic_2025_to_gcs,
        upload_traffic_2026_to_gcs,
        upload_weather_2025_to_gcs,
        upload_weather_2026_to_gcs,
    ]