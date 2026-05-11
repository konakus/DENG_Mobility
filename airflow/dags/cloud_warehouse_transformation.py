from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "deng-team",
    "depends_on_past": False,
    "retries": 1,
}


with DAG(
    dag_id="cloud_warehouse_transformation",
    default_args=default_args,
    description="Transform GCS data lake files and load final Zurich mobility table into BigQuery",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["final", "bigquery", "warehouse", "zurich"],
) as dag:

    transform_gcs_to_bigquery = BashOperator(
        task_id="transform_gcs_to_bigquery",
        bash_command="""
        python /opt/airflow/project/cloud/transform_gcs_to_bigquery.py \
          --bucket_name=project-mobile-zurich-data-lake-494518 \
          --project_id=projectmobile-494518 \
          --dataset_id=zurich_mobility_warehouse \
          --table_id=mobility_weather_daily
        """,
    )