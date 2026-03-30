import argparse
import requests
import pandas as pd
from sqlalchemy import create_engine

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default="5433")
    parser.add_argument("--db", default="meteo")
    parser.add_argument("--table", default="historical_weather")
    parser.add_argument("--latitude", required=True)
    parser.add_argument("--longitude", required=True)
    parser.add_argument("--start_date", required=True)
    parser.add_argument("--end_date", required=True)
    args = parser.parse_args()

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": args.latitude,
        "longitude": args.longitude,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "hourly": "temperature_2m,precipitation,windspeed_10m",
        "timezone": "Europe/Berlin"
    }

    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame({
        "time": data["hourly"]["time"],
        "temperature_2m": data["hourly"]["temperature_2m"],
        "precipitation": data["hourly"]["precipitation"],
        "windspeed_10m": data["hourly"]["windspeed_10m"],
    })

    df["time"] = pd.to_datetime(df["time"])

    engine = create_engine(
        f"postgresql://{args.user}:{args.password}@{args.host}:{args.port}/{args.db}"
    )

    df.to_sql(args.table, engine, if_exists="replace", index=False)
    print(df.head())
    print(f"{len(df)} Zeilen in {args.db}.{args.table} geschrieben")

if __name__ == "__main__":
    main()