import sys

import requests

API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
CURRENCIES = ("USD", "EUR", "CNY")


def fetch_rates() -> dict:
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()
    data = response.json()

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

    return {"date": data["Date"], "rates": rates}


def main():
    try:
        result = fetch_rates()
    except requests.RequestException as error:
        print(f"Не удалось получить курсы: {error}", file=sys.stderr)
        sys.exit(1)

    print(f"Курсы ЦБ РФ на {result['date'][:10]}")
    for rate in result["rates"]:
        change = rate["value"] - rate["previous"]
        print(f"{rate['code']}  {rate['name']:<12} {rate['value']:>9.4f}  ({change:+.4f})")


if __name__ == "__main__":
    main()
