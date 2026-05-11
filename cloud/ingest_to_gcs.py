import argparse
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from google.cloud import storage


OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"


def upload_string_to_gcs(bucket_name: str, destination_blob: str, content: str, content_type: str = "text/csv") -> None:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)
    blob.upload_from_string(content, content_type=content_type)
    print(f"Uploaded text content to gs://{bucket_name}/{destination_blob}")


def upload_file_to_gcs(bucket_name: str, source_file: str, destination_blob: str) -> None:
    source_path = Path(source_file)

    if not source_path.exists():
        raise FileNotFoundError(f"Source file does not exist: {source_file}")

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)
    blob.upload_from_filename(str(source_path))
    print(f"Uploaded file {source_file} to gs://{bucket_name}/{destination_blob}")


def fetch_weather_as_dataframe(latitude: float, longitude: float, start_date: str, end_date: str) -> pd.DataFrame:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,precipitation,windspeed_10m",
        "timezone": "Europe/Berlin",
    }

    response = requests.get(OPEN_METEO_URL, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(
        {
            "time": data["hourly"]["time"],
            "temperature_2m": data["hourly"]["temperature_2m"],
            "precipitation": data["hourly"]["precipitation"],
            "windspeed_10m": data["hourly"]["windspeed_10m"],
        }
    )

    df["time"] = pd.to_datetime(df["time"])
    return df


def ingest_weather_to_gcs(
    bucket_name: str,
    destination_blob: str,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> None:
    df = fetch_weather_as_dataframe(latitude, longitude, start_date, end_date)

    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)

    upload_string_to_gcs(
        bucket_name=bucket_name,
        destination_blob=destination_blob,
        content=csv_buffer.getvalue(),
        content_type="text/csv",
    )

    print(f"Weather rows uploaded: {len(df)}")


def main():
    parser = argparse.ArgumentParser(description="Ingest Zurich source data into Google Cloud Storage data lake.")

    parser.add_argument("--mode", choices=["traffic", "weather"], required=True)
    parser.add_argument("--bucket_name", required=True)
    parser.add_argument("--destination_blob", required=True)

    parser.add_argument("--traffic_csv", required=False)

    parser.add_argument("--latitude", type=float, required=False)
    parser.add_argument("--longitude", type=float, required=False)
    parser.add_argument("--start_date", required=False)
    parser.add_argument("--end_date", required=False)

    args = parser.parse_args()

    if args.mode == "traffic":
        if not args.traffic_csv:
            raise ValueError("--traffic_csv is required when mode=traffic")

        upload_file_to_gcs(
            bucket_name=args.bucket_name,
            source_file=args.traffic_csv,
            destination_blob=args.destination_blob,
        )

    elif args.mode == "weather":
        required_weather_args = [args.latitude, args.longitude, args.start_date, args.end_date]
        if any(value is None for value in required_weather_args):
            raise ValueError("--latitude, --longitude, --start_date and --end_date are required when mode=weather")

        ingest_weather_to_gcs(
            bucket_name=args.bucket_name,
            destination_blob=args.destination_blob,
            latitude=args.latitude,
            longitude=args.longitude,
            start_date=args.start_date,
            end_date=args.end_date,
        )


if __name__ == "__main__":
    main()