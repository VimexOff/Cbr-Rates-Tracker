import sqlite3
import sys

import pandas as pd

from fetch import CURRENCIES
from storage import connect


def load_rates(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT date, code, value FROM rates", conn, parse_dates=["date"])
    # Строки — даты, колонки — валюты: так удобно сравнивать дни между собой
    return df.pivot(index="date", columns="code", values="value").sort_index()


def summarize(rates: pd.DataFrame) -> pd.DataFrame:
    if len(rates) < 2:
        raise ValueError("Для сравнения нужны курсы хотя бы за два дня")

    latest = rates.iloc[-1]
    previous = rates.iloc[-2]
    # Последние курсы на дату не позже, чем неделю назад. ЦБ не публикует курсы
    # в выходные, поэтому точной даты в базе может не быть
    week_ago = rates.asof(rates.index[-1] - pd.Timedelta(days=7))

    summary = pd.DataFrame({
        "value": latest,
        "day_change": latest - previous,
        "day_change_pct": (latest / previous - 1) * 100,
        "week_change_pct": (latest / week_ago - 1) * 100,
    })
    return summary.reindex(list(CURRENCIES))


def main():
    conn = connect()
    try:
        rates = load_rates(conn)
    finally:
        conn.close()

    try:
        summary = summarize(rates)
    except ValueError as error:
        print(f"{error}. Сначала запусти storage.py", file=sys.stderr)
        sys.exit(1)

    latest_date = rates.index[-1].date()
    previous_date = rates.index[-2].date()
    print(f"Курсы на {latest_date}, изменение к {previous_date}")
    for code, row in summary.iterrows():
        week = "нет данных" if pd.isna(row["week_change_pct"]) else f"{row['week_change_pct']:+.2f}%"
        print(
            f"{code}  {row['value']:>9.4f}  {row['day_change']:+.4f} "
            f"({row['day_change_pct']:+.2f}%)  за неделю: {week}"
        )


if __name__ == "__main__":
    main()
