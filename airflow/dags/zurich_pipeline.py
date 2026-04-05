from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "deng-team",
    "depends_on_past": False,
    "retries": 1,
}


with DAG(
    dag_id="zurich_mobility_pipeline",
    default_args=default_args,
    description="Zurich mobility + weather batch pipeline",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["midterm", "zurich", "mobility"],
) as dag:

    ingest_weather = BashOperator(
        task_id="ingest_weather",
        bash_command="""
        python /opt/airflow/project/ingest_meteo.py \
          --user=root \
          --password=meteo123 \
          --host=pgdatabase \
          --port=5432 \
          --db=meteo \
          --table=historical_weather \
          --latitude=47.3769 \
          --longitude=8.5417 \
          --start_date=2025-01-01 \
          --end_date=2025-12-31
        """,
    )

    ingest_traffic = BashOperator(
        task_id="ingest_traffic",
        bash_command="""
        python /opt/airflow/project/ingest_traffic.py \
          --user=root \
          --password=meteo123 \
          --host=pgdatabase \
          --port=5432 \
          --db=traffic_zurich \
          --table=traffic_data \
          --csv=/opt/airflow/project/data/traffic_zurich.csv
        """,
    )

    transform_daily = BashOperator(
        task_id="transform_daily",
        bash_command="""
        python /opt/airflow/project/transform_zurich_daily.py \
          --user=root \
          --password=meteo123 \
          --host=pgdatabase \
          --port=5432 \
          --weather_db=meteo \
          --traffic_db=traffic_zurich \
          --target_db=traffic_zurich \
          --weather_table=historical_weather \
          --traffic_table=traffic_data \
          --target_table=mobility_weather_daily
        """,
    )

    [ingest_weather, ingest_traffic] >> transform_daily