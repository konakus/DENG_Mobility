import argparse
from io import StringIO

import pandas as pd
from google.cloud import bigquery
from google.cloud import storage


def read_csv_from_gcs(bucket_name: str, blob_name: str) -> pd.DataFrame:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    if not blob.exists():
        raise FileNotFoundError(f"GCS object not found: gs://{bucket_name}/{blob_name}")

    print(f"Reading gs://{bucket_name}/{blob_name}")
    content = blob.download_as_text()
    return pd.read_csv(StringIO(content))


def load_source_data(bucket_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    traffic_blobs = [
        "raw/traffic/year=2025/traffic_zurich_2025.csv",
        "raw/traffic/year=2026/traffic_zurich_2026.csv",
    ]

    weather_blobs = [
        "raw/weather/year=2025/weather_zurich_2025.csv",
        "raw/weather/year=2026/weather_zurich_2026.csv",
    ]

    traffic_frames = [read_csv_from_gcs(bucket_name, blob) for blob in traffic_blobs]
    weather_frames = [read_csv_from_gcs(bucket_name, blob) for blob in weather_blobs]

    traffic_df = pd.concat(traffic_frames, ignore_index=True)
    weather_df = pd.concat(weather_frames, ignore_index=True)

    print(f"Traffic rows loaded: {len(traffic_df)}")
    print(f"Weather rows loaded: {len(weather_df)}")

    return traffic_df, weather_df


def transform_weather_daily(df_weather: pd.DataFrame) -> pd.DataFrame:
    df = df_weather.copy()

    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"])

    df["date"] = df["time"].dt.date

    weather_daily = (
        df.groupby("date", as_index=False)
        .agg(
            avg_temperature=("temperature_2m", "mean"),
            total_precipitation=("precipitation", "sum"),
            avg_windspeed=("windspeed_10m", "mean"),
        )
    )

    return weather_daily


def transform_traffic_daily(df_traffic: pd.DataFrame) -> pd.DataFrame:
    df = df_traffic.copy()

    df["DATUM"] = pd.to_datetime(df["DATUM"], errors="coerce")
    df = df.dropna(subset=["DATUM"])

    count_cols = ["VELO_IN", "VELO_OUT", "FUSS_IN", "FUSS_OUT"]

    for col in count_cols:
        if col not in df.columns:
            raise ValueError(f"Missing expected traffic column: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["date"] = df["DATUM"].dt.date

    df["velo_total_row"] = df["VELO_IN"] + df["VELO_OUT"]
    df["fuss_total_row"] = df["FUSS_IN"] + df["FUSS_OUT"]

    traffic_daily = (
        df.groupby("date", as_index=False)
        .agg(
            total_velo=("velo_total_row", "sum"),
            total_fuss=("fuss_total_row", "sum"),
        )
    )

    return traffic_daily


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    dt_series = pd.to_datetime(out["date"], errors="coerce")
    out = out.loc[dt_series.notna()].copy()
    dt_series = pd.to_datetime(out["date"], errors="coerce")

    out["date"] = dt_series.dt.date
    out["year"] = dt_series.dt.year
    out["month"] = dt_series.dt.month
    out["day_of_week"] = dt_series.dt.day_name()
    out["is_weekend"] = dt_series.dt.dayofweek >= 5

    return out


def build_final_dataset(traffic_df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    print("Transforming weather data to daily level...")
    weather_daily = transform_weather_daily(weather_df)
    print(f"Weather daily rows: {len(weather_daily)}")

    print("Transforming traffic data to daily level...")
    traffic_daily = transform_traffic_daily(traffic_df)
    print(f"Traffic daily rows: {len(traffic_daily)}")

    print("Joining traffic and weather data...")
    final_df = pd.merge(traffic_daily, weather_daily, on="date", how="left")

    print("Adding calendar features...")
    final_df = add_calendar_features(final_df)

    final_df["avg_temperature"] = final_df["avg_temperature"].round(1)
    final_df["total_precipitation"] = final_df["total_precipitation"].round(1)
    final_df["avg_windspeed"] = final_df["avg_windspeed"].round(1)

    final_df["total_velo"] = final_df["total_velo"].round(0).astype("int64")
    final_df["total_fuss"] = final_df["total_fuss"].round(0).astype("int64")

    final_df = final_df[
        [
            "date",
            "year",
            "month",
            "day_of_week",
            "is_weekend",
            "avg_temperature",
            "total_precipitation",
            "avg_windspeed",
            "total_velo",
            "total_fuss",
        ]
    ]

    final_df = final_df.sort_values("date").reset_index(drop=True)

    print("Preview of final dataset:")
    print(final_df.head(10))
    print(f"Final rows: {len(final_df)}")

    return final_df


def load_dataframe_to_bigquery(
    df: pd.DataFrame,
    project_id: str,
    dataset_id: str,
    table_id: str,
) -> None:
    client = bigquery.Client(project=project_id)

    full_table_id = f"{project_id}.{dataset_id}.{table_id}"

    schema = [
        bigquery.SchemaField("date", "DATE"),
        bigquery.SchemaField("year", "INTEGER"),
        bigquery.SchemaField("month", "INTEGER"),
        bigquery.SchemaField("day_of_week", "STRING"),
        bigquery.SchemaField("is_weekend", "BOOLEAN"),
        bigquery.SchemaField("avg_temperature", "FLOAT"),
        bigquery.SchemaField("total_precipitation", "FLOAT"),
        bigquery.SchemaField("avg_windspeed", "FLOAT"),
        bigquery.SchemaField("total_velo", "INTEGER"),
        bigquery.SchemaField("total_fuss", "INTEGER"),
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        time_partitioning=bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="date",
        ),
        clustering_fields=["year", "month", "is_weekend"],
    )

    print(f"Loading final dataset to BigQuery table: {full_table_id}")

    load_job = client.load_table_from_dataframe(
        df,
        full_table_id,
        job_config=job_config,
    )

    load_job.result()

    table = client.get_table(full_table_id)
    print(f"Loaded {table.num_rows} rows into {full_table_id}")
    print("BigQuery load completed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transform raw GCS data and load final Zurich mobility table into BigQuery."
    )

    parser.add_argument("--bucket_name", required=True)
    parser.add_argument("--project_id", required=True)
    parser.add_argument("--dataset_id", required=True)
    parser.add_argument("--table_id", required=True)

    args = parser.parse_args()

    traffic_df, weather_df = load_source_data(args.bucket_name)
    final_df = build_final_dataset(traffic_df, weather_df)

    load_dataframe_to_bigquery(
        df=final_df,
        project_id=args.project_id,
        dataset_id=args.dataset_id,
        table_id=args.table_id,
    )


if __name__ == "__main__":
    main()