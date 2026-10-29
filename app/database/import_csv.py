
import csv
import sqlite3
from pathlib import Path

from app.database.connection import get_connection

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def import_csv(connection, filename, table_name):
    csv_path = DATA_DIR / filename

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(f"No headers found in {filename}")

        columns = reader.fieldnames
        column_sql = ", ".join(f'"{column}" TEXT' for column in columns)
        placeholders = ", ".join("?" for _ in columns)
        columns_sql = ", ".join(f'"{column}"' for column in columns)

        connection.execute(
            f'CREATE TABLE IF NOT EXISTS "{table_name}" '
            f'({column_sql})'
        )

        rows = [
            tuple(row[column] for column in columns)
            for row in reader
        ]

        if rows:
            connection.executemany(
                f'INSERT INTO "{table_name}" ({columns_sql}) '
                f'VALUES ({placeholders})',
                rows,
            )

        print(f"{filename}: {len(rows)} rows imported")


def main():
    with get_connection() as connection:
        import_csv(
            connection,
            "persona_profiles.csv",
            "personas",
        )
        import_csv(
            connection,
            "research_sources.csv",
            "research_sources",
        )

    print("CSV import completed successfully.")


if __name__ == "__main__":
    main()
