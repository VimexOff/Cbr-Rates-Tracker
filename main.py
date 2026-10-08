import argparse
import html
import sys
from datetime import date, datetime
from typing import NoReturn

import requests

from analysis import load_rates, summarize
from fetch import fetch_rates
from notify import NotifyError, format_summary, send_summary
from storage import connect, mark_run_ok, mark_sent, save_rates, was_run_ok, was_sent


def fail(message: object, alert_after: int | None) -> NoReturn:
    print(message, file=sys.stderr)

    if alert_after is not None and datetime.now().hour >= alert_after:
        conn = connect()
        try:
            # Если сегодня уже был удачный запуск, сводка либо отправлена,
            # либо новых курсов нет. Тогда предупреждать не о чем
            already_ok = was_run_ok(conn, date.today().isoformat())
        finally:
            conn.close()

        if not already_ok:
            # Если недоступен сам Telegram, предупредить не получится: ошибка останется только в логе
            try:
                send_summary(f"⚠️ Сводка курсов сегодня не отправлена\n{html.escape(str(message)[:500])}")
                print("Предупреждение отправлено в Telegram", file=sys.stderr)
            except NotifyError as error:
                print(f"Не удалось отправить предупреждение: {error}", file=sys.stderr)

    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Получить курсы, сохранить и отправить сводку в Telegram")
    parser.add_argument("--dry-run", action="store_true", help="показать сообщение, не отправлять")
    parser.add_argument("--force", action="store_true", help="отправить, даже если сводка за эту дату уже была")
    parser.add_argument(
        "--alert-after",
        type=int,
        metavar="HOUR",
        help="начиная с этого часа при ошибке написать о ней в Telegram, если за день не было удачного запуска",
    )
    args = parser.parse_args()

    # Время в начале строки помогает разбирать лог при запуске по расписанию
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Запуск")

    try:
        result = fetch_rates()
    except requests.RequestException as error:
        fail(f"Не удалось получить курсы: {error}", args.alert_after)

    day = result["date"]
    conn = connect()
    try:
        save_rates(conn, result)
        print(f"Курсы на {day} сохранены")

        # По воскресеньям и понедельникам ЦБ не публикует новых курсов,
        # и API отдаёт субботние. Повторять ту же сводку незачем
        if was_sent(conn, day) and not (args.force or args.dry_run):
            mark_run_ok(conn, date.today().isoformat())
            print(f"Сводка за {day} уже отправлена, новых курсов нет")
            return

        rates = load_rates(conn)
        text = format_summary(rates, summarize(rates))

        if args.dry_run:
            print(text)
            return

        send_summary(text)
        mark_sent(conn, day)
        mark_run_ok(conn, date.today().isoformat())
        print(f"Сводка за {day} отправлена")
    except (ValueError, NotifyError) as error:
        fail(error, args.alert_after)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
