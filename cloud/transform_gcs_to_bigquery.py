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


def prepare_traffic_base(df_traffic: pd.DataFrame) -> pd.DataFrame:
    df = df_traffic.copy()

    expected_columns = [
        "FK_STANDORT",
        "DATUM",
        "VELO_IN",
        "VELO_OUT",
        "FUSS_IN",
        "FUSS_OUT",
        "OST",
        "NORD",
    ]

    for col in expected_columns:
        if col not in df.columns:
            raise ValueError(f"Missing expected traffic column: {col}")

    df["DATUM"] = pd.to_datetime(df["DATUM"], errors="coerce")
    df = df.dropna(subset=["DATUM"])

    count_cols = ["VELO_IN", "VELO_OUT", "FUSS_IN", "FUSS_OUT"]

    for col in count_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["FK_STANDORT"] = pd.to_numeric(df["FK_STANDORT"], errors="coerce")
    df = df.dropna(subset=["FK_STANDORT"])
    df["FK_STANDORT"] = df["FK_STANDORT"].astype("int64")

    df["OST"] = pd.to_numeric(df["OST"], errors="coerce")
    df["NORD"] = pd.to_numeric(df["NORD"], errors="coerce")

    df["date"] = df["DATUM"].dt.date
    df["velo_total_row"] = df["VELO_IN"] + df["VELO_OUT"]
    df["fuss_total_row"] = df["FUSS_IN"] + df["FUSS_OUT"]

    return df


def transform_traffic_city_daily(df_traffic: pd.DataFrame) -> pd.DataFrame:
    df = prepare_traffic_base(df_traffic)

    traffic_daily = (
        df.groupby("date", as_index=False)
        .agg(
            total_velo=("velo_total_row", "sum"),
            total_fuss=("fuss_total_row", "sum"),
        )
    )

    return traffic_daily


def transform_traffic_station_daily(df_traffic: pd.DataFrame) -> pd.DataFrame:
    df = prepare_traffic_base(df_traffic)

    station_daily = (
        df.groupby(["date", "FK_STANDORT"], as_index=False)
        .agg(
            east_coord=("OST", "first"),
            north_coord=("NORD", "first"),
            total_velo=("velo_total_row", "sum"),
            total_fuss=("fuss_total_row", "sum"),
        )
    )

    station_daily = station_daily.rename(columns={"FK_STANDORT": "station_id"})

    return station_daily


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


def finalize_common_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["avg_temperature"] = out["avg_temperature"].round(1)
    out["total_precipitation"] = out["total_precipitation"].round(1)
    out["avg_windspeed"] = out["avg_windspeed"].round(1)

    out["total_velo"] = out["total_velo"].round(0).astype("int64")
    out["total_fuss"] = out["total_fuss"].round(0).astype("int64")

    return out


def build_city_dataset(traffic_df: pd.DataFrame, weather_daily: pd.DataFrame) -> pd.DataFrame:
    print("Building city-level daily dataset...")

    traffic_daily = transform_traffic_city_daily(traffic_df)
    final_df = pd.merge(traffic_daily, weather_daily, on="date", how="left")

    final_df = add_calendar_features(final_df)
    final_df = finalize_common_columns(final_df)

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

    print("Preview of city-level dataset:")
    print(final_df.head(10))
    print(f"City-level rows: {len(final_df)}")

    return final_df


def build_station_dataset(traffic_df: pd.DataFrame, weather_daily: pd.DataFrame) -> pd.DataFrame:
    print("Building station-level daily dataset...")

    station_daily = transform_traffic_station_daily(traffic_df)
    final_df = pd.merge(station_daily, weather_daily, on="date", how="left")

    final_df = add_calendar_features(final_df)
    final_df = finalize_common_columns(final_df)

    final_df["station_id"] = final_df["station_id"].astype("int64")

    final_df = final_df[
        [
            "date",
            "station_id",
            "east_coord",
            "north_coord",
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

    final_df = final_df.sort_values(["date", "station_id"]).reset_index(drop=True)

    print("Preview of station-level dataset:")
    print(final_df.head(10))
    print(f"Station-level rows: {len(final_df)}")

    return final_df


def load_dataframe_to_bigquery(
    df: pd.DataFrame,
    project_id: str,
    dataset_id: str,
    table_id: str,
    schema: list[bigquery.SchemaField],
    clustering_fields: list[str],
) -> None:
    client = bigquery.Client(project=project_id)

    full_table_id = f"{project_id}.{dataset_id}.{table_id}"

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        time_partitioning=bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="date",
        ),
        clustering_fields=clustering_fields,
    )

    print(f"Loading dataset to BigQuery table: {full_table_id}")

    load_job = client.load_table_from_dataframe(
        df,
        full_table_id,
        job_config=job_config,
    )

    load_job.result()

    table = client.get_table(full_table_id)
    print(f"Loaded {table.num_rows} rows into {full_table_id}")


def load_city_table(
    df: pd.DataFrame,
    project_id: str,
    dataset_id: str,
    table_id: str,
) -> None:
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

    load_dataframe_to_bigquery(
        df=df,
        project_id=project_id,
        dataset_id=dataset_id,
        table_id=table_id,
        schema=schema,
        clustering_fields=["year", "month", "is_weekend"],
    )


def load_station_table(
    df: pd.DataFrame,
    project_id: str,
    dataset_id: str,
    table_id: str,
) -> None:
    schema = [
        bigquery.SchemaField("date", "DATE"),
        bigquery.SchemaField("station_id", "INTEGER"),
        bigquery.SchemaField("east_coord", "FLOAT"),
        bigquery.SchemaField("north_coord", "FLOAT"),
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

    load_dataframe_to_bigquery(
        df=df,
        project_id=project_id,
        dataset_id=dataset_id,
        table_id=table_id,
        schema=schema,
        clustering_fields=["station_id", "year", "month"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transform raw GCS data and load Zurich mobility tables into BigQuery."
    )

    parser.add_argument("--bucket_name", required=True)
    parser.add_argument("--project_id", required=True)
    parser.add_argument("--dataset_id", required=True)
    parser.add_argument("--city_table_id", required=True)
    parser.add_argument("--station_table_id", required=True)

    args = parser.parse_args()

    traffic_df, weather_df = load_source_data(args.bucket_name)

    print("Transforming weather data to daily level...")
    weather_daily = transform_weather_daily(weather_df)
    print(f"Weather daily rows: {len(weather_daily)}")

    city_df = build_city_dataset(traffic_df, weather_daily)
    station_df = build_station_dataset(traffic_df, weather_daily)

    load_city_table(
        df=city_df,
        project_id=args.project_id,
        dataset_id=args.dataset_id,
        table_id=args.city_table_id,
    )

    load_station_table(
        df=station_df,
        project_id=args.project_id,
        dataset_id=args.dataset_id,
        table_id=args.station_table_id,
    )

    print("BigQuery load completed for city-level and station-level tables.")


if __name__ == "__main__":
    main()