import requests
import psycopg2

API_URL = "https://archive-api.open-meteo.com/v1/archive"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "meteo",
    "user": "root",
    "password": "root",
}

PARAMS = {
    "latitude": 47.3769,
    "longitude": 8.5417,
    "start_date": "2024-01-01",
    "end_date": "2024-01-07",
    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
    "timezone": "Europe/Zurich",
}

CITY_NAME = "Zurich"


def fetch_weather():
    response = requests.get(API_URL, params=PARAMS, timeout=30)
    response.raise_for_status()
    return response.json()


def insert_data(data):
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    insert_query = """
    INSERT INTO historical_weather (
        city,
        date,
        temperature_max,
        temperature_min,
        precipitation_sum
    )
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (city, date) DO NOTHING
    """

    for row in zip(dates, tmax, tmin, precip):
        cur.execute(insert_query, (CITY_NAME, row[0], row[1], row[2], row[3]))

    conn.commit()
    cur.close()
    conn.close()


def main():
    data = fetch_weather()
    insert_data(data)
    print("Wetterdaten erfolgreich geladen.")


if __name__ == "__main__":
    main()