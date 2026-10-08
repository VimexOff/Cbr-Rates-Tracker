import argparse
import sys
from datetime import datetime

import requests

from analysis import load_rates, summarize
from fetch import fetch_rates
from notify import NotifyError, format_summary, send_summary
from storage import connect, mark_sent, save_rates, was_sent


def main():
    parser = argparse.ArgumentParser(description="Получить курсы, сохранить и отправить сводку в Telegram")
    parser.add_argument("--dry-run", action="store_true", help="показать сообщение, не отправлять")
    parser.add_argument("--force", action="store_true", help="отправить, даже если сводка за эту дату уже была")
    args = parser.parse_args()

    # Время в начале строки помогает разбирать лог при запуске по расписанию
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Запуск")

    try:
        result = fetch_rates()
    except requests.RequestException as error:
        print(f"Не удалось получить курсы: {error}", file=sys.stderr)
        sys.exit(1)

    day = result["date"]
    conn = connect()
    try:
        save_rates(conn, result)
        print(f"Курсы на {day} сохранены")

        # По воскресеньям и понедельникам ЦБ не публикует новых курсов,
        # и API отдаёт субботние. Повторять ту же сводку незачем
        if was_sent(conn, day) and not (args.force or args.dry_run):
            print(f"Сводка за {day} уже отправлена, новых курсов нет")
            return

        rates = load_rates(conn)
        text = format_summary(rates, summarize(rates))

        if args.dry_run:
            print(text)
            return

        send_summary(text)
        mark_sent(conn, day)
        print(f"Сводка за {day} отправлена")
    except (ValueError, NotifyError) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
