import argparse
import pandas as pd
from sqlalchemy import create_engine


def make_engine(user: str, password: str, host: str, port: int, db: str):
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}")


def load_weather(engine, weather_table: str) -> pd.DataFrame:
    query = f"""
        SELECT
            time,
            temperature_2m,
            precipitation,
            windspeed_10m
        FROM {weather_table}
    """
    df = pd.read_sql(query, engine)
    return df


def load_traffic(engine, traffic_table: str) -> pd.DataFrame:
    query = f"""
        SELECT
            "FK_STANDORT",
            "DATUM",
            "VELO_IN",
            "VELO_OUT",
            "FUSS_IN",
            "FUSS_OUT",
            "OST",
            "NORD"
        FROM {traffic_table}
    """
    df = pd.read_sql(query, engine)
    return df


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

    # DATUM ist aktuell text -> in datetime umwandeln
    df["DATUM"] = pd.to_datetime(df["DATUM"], errors="coerce")
    df = df.dropna(subset=["DATUM"])

    # Nur 2025 behalten
    df = df[df["DATUM"].dt.year == 2025].copy()

    # NULL-Werte in den Zählspalten als 0 behandeln
    count_cols = ["VELO_IN", "VELO_OUT", "FUSS_IN", "FUSS_OUT"]
    for col in count_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Tagesdatum extrahieren
    df["date"] = df["DATUM"].dt.date

    # Tagessummen über ganz Zürich
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

    out["is_weekend"] = dt_series.dt.dayofweek >= 5
    out["month"] = dt_series.dt.month
    out["day_of_week"] = dt_series.dt.day_name()

    # date als echtes Datum ohne Uhrzeit speichern
    out["date"] = dt_series.dt.date

    return out


def main():
    parser = argparse.ArgumentParser(description="Transform Zurich traffic + weather to daily final table.")
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)

    parser.add_argument("--weather_db", required=True)
    parser.add_argument("--traffic_db", required=True)
    parser.add_argument("--target_db", required=True)

    parser.add_argument("--weather_table", default="historical_weather")
    parser.add_argument("--traffic_table", default="traffic_data")
    parser.add_argument("--target_table", default="mobility_weather_daily")

    args = parser.parse_args()

    weather_engine = make_engine(args.user, args.password, args.host, args.port, args.weather_db)
    traffic_engine = make_engine(args.user, args.password, args.host, args.port, args.traffic_db)
    target_engine = make_engine(args.user, args.password, args.host, args.port, args.target_db)

    print("Loading weather data...")
    df_weather = load_weather(weather_engine, args.weather_table)
    print(f"Weather rows loaded: {len(df_weather)}")

    print("Loading traffic data...")
    df_traffic = load_traffic(traffic_engine, args.traffic_table)
    print(f"Traffic rows loaded: {len(df_traffic)}")

    print("Transforming weather to daily level...")
    weather_daily = transform_weather_daily(df_weather)
    print(f"Weather daily rows: {len(weather_daily)}")

    print("Transforming traffic to daily level...")
    traffic_daily = transform_traffic_daily(df_traffic)
    print(f"Traffic daily rows: {len(traffic_daily)}")

    print("Joining weather + traffic...")
    final_df = pd.merge(traffic_daily, weather_daily, on="date", how="left")

    print("Adding calendar features...")
    final_df = add_calendar_features(final_df)

    # Rounding for presentation
    final_df["avg_temperature"] = final_df["avg_temperature"].round(1)
    final_df["avg_windspeed"] = final_df["avg_windspeed"].round(1)
    final_df["total_precipitation"] = final_df["total_precipitation"].round(1)

    # Spaltenreihenfolge
    final_df = final_df[
        [
            "date",
            "avg_temperature",
            "total_precipitation",
            "avg_windspeed",
            "total_velo",
            "total_fuss",
            "is_weekend",
            "month",
            "day_of_week",
        ]
    ]

    # Nach Datum sortieren
    final_df = final_df.sort_values("date").reset_index(drop=True)

    print("Preview of final table:")
    print(final_df.head(10))
    print(f"Final rows: {len(final_df)}")

    print(f"Writing final table to {args.target_db}.{args.target_table} ...")
    final_df.to_sql(args.target_table, target_engine, if_exists="replace", index=False)

    print("Done.")


if __name__ == "__main__":
    main()