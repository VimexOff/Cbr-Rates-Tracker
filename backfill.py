import argparse
import sys
import time
from datetime import date, timedelta

import requests

from fetch import DataError, fetch_rates
from storage import connect, save_rates

# Пауза между запросами, чтобы не нагружать сервер
REQUEST_DELAY = 0.5


def main():
    parser = argparse.ArgumentParser(description="Загрузка курсов из архива ЦБ в базу")
    parser.add_argument("--days", type=int, default=14, help="за сколько последних дней (по умолчанию 14)")
    args = parser.parse_args()

    today = date.today()
    days = [today - timedelta(days=offset) for offset in range(args.days - 1, -1, -1)]

    saved = skipped = failed = 0
    conn = connect()
    try:
        for day in days:
            try:
                result = fetch_rates(day)
            except requests.HTTPError as error:
                # Архив отвечает 404 на даты, с которых не начинал действовать новый курс:
                # курс, установленный в пятницу, действует до понедельника включительно,
                # а курс перед праздниками — до конца праздников
                if error.response.status_code == 404:
                    print(f"{day}: нового курса нет, действует предыдущий")
                    skipped += 1
                else:
                    print(f"{day}: ошибка — {error}", file=sys.stderr)
                    failed += 1
                continue
            except (requests.RequestException, DataError) as error:
                print(f"{day}: ошибка — {error}", file=sys.stderr)
                failed += 1
                continue
            finally:
                time.sleep(REQUEST_DELAY)

            save_rates(conn, result)
            saved += 1
            print(f"{day}: сохранено")

        total = conn.execute("SELECT COUNT(DISTINCT date) FROM rates").fetchone()[0]
    finally:
        conn.close()

    print(f"Загружено дней: {saved}, без курсов: {skipped}, с ошибкой: {failed}")
    print(f"Всего дат в базе: {total}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
