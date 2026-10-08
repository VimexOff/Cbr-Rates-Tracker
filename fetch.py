import sys
import time

import requests

API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
CURRENCIES = ("USD", "EUR", "CNY")
ATTEMPTS = 3
RETRY_DELAY = 5


def get_json() -> dict:
    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = requests.get(API_URL, timeout=10)
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


def fetch_rates() -> dict:
    data = get_json()

    rates = []
    for code in CURRENCIES:
        item = data["Valute"][code]
        # ЦБ может давать курс не за 1 единицу, а, например, за 10 юаней
        nominal = item["Nominal"]
        rates.append({
            "code": code,
            "name": item["Name"],
            "value": item["Value"] / nominal,
            "previous": item["Previous"] / nominal,
        })

    return {
        "date": data["Date"][:10],
        "previous_date": data["PreviousDate"][:10],
        "rates": rates,
    }


def main():
    try:
        result = fetch_rates()
    except requests.RequestException as error:
        print(f"Не удалось получить курсы: {error}", file=sys.stderr)
        sys.exit(1)

    print(f"Курсы ЦБ РФ на {result['date']}")
    for rate in result["rates"]:
        change = rate["value"] - rate["previous"]
        print(f"{rate['code']}  {rate['name']:<12} {rate['value']:>9.4f}  ({change:+.4f})")


if __name__ == "__main__":
    main()
