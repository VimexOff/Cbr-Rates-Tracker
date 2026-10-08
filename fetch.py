import math
import sys
import time
from datetime import date

import requests

API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
ARCHIVE_URL = "https://www.cbr-xml-daily.ru/archive/{day:%Y/%m/%d}/daily_json.js"
CURRENCIES = ("USD", "EUR", "CNY")
ATTEMPTS = 3
RETRY_DELAY = 5


def get_json(url: str) -> dict:
    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        # Повторяем только сетевые сбои: ошибку вроде 404 повтор не исправит
        except (requests.ConnectionError, requests.Timeout) as error:
            if attempt == ATTEMPTS:
                raise
            print(
                f"Попытка {attempt} из {ATTEMPTS} не удалась ({type(error).__name__}), "
                f"повтор через {RETRY_DELAY} с",
                file=sys.stderr,
            )
            time.sleep(RETRY_DELAY)


class DataError(ValueError):
    pass


def positive_number(value, field: str) -> float:
    # bool в Python тоже число, а json пропускает NaN и Infinity, поэтому проверяем явно
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise DataError(f"{field}: ожидалось положительное число, получено {value!r}")
    return float(value)


def parse_date(value) -> str:
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except (TypeError, ValueError):
        raise DataError(f"Неверная дата в ответе: {value!r}") from None


def fetch_rates(day: date | None = None) -> dict:
    url = API_URL if day is None else ARCHIVE_URL.format(day=day)
    data = get_json(url)

    try:
        rates = []
        for code in CURRENCIES:
            item = data["Valute"][code]
            # ЦБ может давать курс не за 1 единицу, а, например, за 10 юаней
            nominal = positive_number(item["Nominal"], f"{code}.Nominal")
            rates.append({
                "code": code,
                "name": item["Name"],
                "value": positive_number(item["Value"], f"{code}.Value") / nominal,
                "previous": positive_number(item["Previous"], f"{code}.Previous") / nominal,
            })

        return {
            "date": parse_date(data["Date"]),
            "previous_date": parse_date(data["PreviousDate"]),
            "rates": rates,
        }
    except (KeyError, TypeError) as error:
        raise DataError(f"Неожиданный формат ответа ({type(error).__name__}: {error})") from None


def main():
    try:
        result = fetch_rates()
    except (requests.RequestException, DataError) as error:
        print(f"Не удалось получить курсы: {error}", file=sys.stderr)
        sys.exit(1)

    print(f"Курсы ЦБ РФ на {result['date']}")
    for rate in result["rates"]:
        change = rate["value"] - rate["previous"]
        print(f"{rate['code']}  {rate['name']:<12} {rate['value']:>9.4f}  ({change:+.4f})")


if __name__ == "__main__":
    main()
