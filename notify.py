import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from analysis import load_rates, summarize
from storage import connect

SEND_URL = "https://api.telegram.org/bot{token}/sendMessage"


def format_summary(rates: pd.DataFrame, summary: pd.DataFrame) -> str:
    latest_date = rates.index[-1].strftime("%d.%m.%Y")
    previous_date = rates.index[-2].strftime("%d.%m.%Y")

    lines = []
    for code, row in summary.iterrows():
        arrow = "▲" if row["day_change"] > 0 else "▼" if row["day_change"] < 0 else "="
        week = "—" if pd.isna(row["week_change_pct"]) else f"{row['week_change_pct']:+.2f}%"
        lines.append(
            f"{code}  {row['value']:>8.4f}  {arrow} {abs(row['day_change']):.4f} "
            f"({row['day_change_pct']:+.2f}%)  неделя {week}"
        )

    # <pre> выводит текст моноширинным шрифтом, чтобы колонки не съезжали
    return (
        f"<b>Курсы ЦБ РФ на {latest_date}</b>\n"
        f"Изменение к {previous_date}\n\n"
        "<pre>" + "\n".join(lines) + "</pre>"
    )


def send_message(token: str, chat_id: str, text: str) -> None:
    response = requests.post(
        SEND_URL.format(token=token),
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=10,
    )
    response.raise_for_status()


def main():
    parser = argparse.ArgumentParser(description="Отправка сводки курсов в Telegram")
    parser.add_argument("--dry-run", action="store_true", help="только показать сообщение, не отправлять")
    args = parser.parse_args()

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

    text = format_summary(rates, summary)
    if args.dry_run:
        print(text)
        return

    load_dotenv(Path(__file__).parent / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Не заданы TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID. Смотри .env.example", file=sys.stderr)
        sys.exit(1)

    # Токен входит в адрес запроса, а requests показывает адрес в тексте ошибки.
    # Поэтому печатаем только описание от Telegram или тип ошибки, без самого исключения
    try:
        send_message(token, chat_id, text)
    except requests.HTTPError as error:
        try:
            description = error.response.json().get("description", "")
        except ValueError:
            description = ""
        print(f"Telegram вернул ошибку {error.response.status_code}: {description}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as error:
        print(f"Не удалось связаться с Telegram ({type(error).__name__})", file=sys.stderr)
        sys.exit(1)

    print("Сводка отправлена")


if __name__ == "__main__":
    main()
