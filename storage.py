import sqlite3
import sys
from pathlib import Path

import requests

from fetch import fetch_rates

DB_PATH = Path(__file__).parent / "rates.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS rates (
    date  TEXT NOT NULL,
    code  TEXT NOT NULL,
    name  TEXT NOT NULL,
    value REAL NOT NULL,
    PRIMARY KEY (date, code)
);

CREATE TABLE IF NOT EXISTS sent_summaries (
    date TEXT PRIMARY KEY
);
"""


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def save_rates(conn: sqlite3.Connection, result: dict) -> int:
    rows = []
    for rate in result["rates"]:
        rows.append((result["date"], rate["code"], rate["name"], rate["value"]))
        rows.append((result["previous_date"], rate["code"], rate["name"], rate["previous"]))

    # Повторный запуск в тот же день или в выходные, когда ЦБ не публикует
    # новые курсы, не создаёт дублей, а только обновляет существующие строки
    with conn:
        conn.executemany(
            """
            INSERT INTO rates (date, code, name, value) VALUES (?, ?, ?, ?)
            ON CONFLICT (date, code) DO UPDATE SET
                name = excluded.name,
                value = excluded.value
            """,
            rows,
        )
    return len(rows)


def was_sent(conn: sqlite3.Connection, day: str) -> bool:
    row = conn.execute("SELECT 1 FROM sent_summaries WHERE date = ?", (day,)).fetchone()
    return row is not None


def mark_sent(conn: sqlite3.Connection, day: str) -> None:
    with conn:
        conn.execute("INSERT OR IGNORE INTO sent_summaries (date) VALUES (?)", (day,))


def main():
    try:
        result = fetch_rates()
    except requests.RequestException as error:
        print(f"Не удалось получить курсы: {error}", file=sys.stderr)
        sys.exit(1)

    conn = connect()
    try:
        count = save_rates(conn, result)
        total = conn.execute("SELECT COUNT(*) FROM rates").fetchone()[0]
    finally:
        conn.close()

    print(f"Сохранено строк: {count} (за {result['previous_date']} и {result['date']})")
    print(f"Всего в базе: {total}")


if __name__ == "__main__":
    main()
