from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "deng-team",
    "depends_on_past": False,
    "retries": 1,
}


with DAG(
    dag_id="cloud_data_lake_ingestion",
    default_args=default_args,
    description="Ingest Zurich source data into Google Cloud Storage data lake",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["final", "gcs", "data-lake", "zurich"],
) as dag:

    upload_weather_to_gcs = BashOperator(
        task_id="upload_weather_to_gcs",
        bash_command="""
        python /opt/airflow/project/cloud/ingest_to_gcs.py \
          --mode=weather \
          --bucket_name=project-mobile-zurich-data-lake-494518 \
          --destination_blob=raw/weather/weather_zurich_2025.csv \
          --latitude=47.3769 \
          --longitude=8.5417 \
          --start_date=2025-01-01 \
          --end_date=2025-12-31
        """,
    )

    upload_traffic_to_gcs = BashOperator(
        task_id="upload_traffic_to_gcs",
        bash_command="""
        python /opt/airflow/project/cloud/ingest_to_gcs.py \
          --mode=traffic \
          --bucket_name=project-mobile-zurich-data-lake-494518 \
          --traffic_csv=/opt/airflow/project/data/traffic_zurich.csv \
          --destination_blob=raw/traffic/traffic_zurich_2025.csv
        """,
    )

    [upload_weather_to_gcs, upload_traffic_to_gcs]