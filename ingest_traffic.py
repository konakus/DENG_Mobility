import argparse
import pandas as pd
from sqlalchemy import create_engine


def main():
    parser = argparse.ArgumentParser(description="Load traffic CSV into PostgreSQL")
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--table", required=True)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--chunksize", type=int, default=50000)

    args = parser.parse_args()

    engine = create_engine(
        f"postgresql://{args.user}:{args.password}@{args.host}:{args.port}/{args.db}"
    )

    first_chunk = True

    for chunk in pd.read_csv(args.csv, chunksize=args.chunksize):
        # Beispielhafte Bereinigungen:
        # chunk.columns = [col.strip().lower().replace(" ", "_") for col in chunk.columns]

        if first_chunk:
            chunk.head(0).to_sql(
                name=args.table,
                con=engine,
                if_exists="replace",
                index=False
            )
            first_chunk = False

        chunk.to_sql(
            name=args.table,
            con=engine,
            if_exists="append",
            index=False
        )

    print(f"Import abgeschlossen: {args.csv} -> {args.db}.{args.table}")


if __name__ == "__main__":
    main()