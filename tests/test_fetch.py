import pytest

import fetch
from fetch import DataError, fetch_rates


def make_payload(usd=(90.0, 89.0), eur=(100.0, 99.0), cny=(125.0, 124.0), cny_nominal=10):
    def item(name, pair, nominal=1):
        return {"Name": name, "Nominal": nominal, "Value": pair[0], "Previous": pair[1]}

    return {
        "Date": "2026-10-08T11:30:00+03:00",
        "PreviousDate": "2026-10-07T11:30:00+03:00",
        "Valute": {
            "USD": item("Доллар США", usd),
            "EUR": item("Евро", eur),
            "CNY": item("Юань", cny, cny_nominal),
        },
    }


@pytest.fixture
def respond(monkeypatch):
    def set_payload(payload):
        monkeypatch.setattr(fetch, "get_json", lambda url: payload)

    return set_payload


def test_normal_response(respond):
    respond(make_payload())

    result = fetch_rates()

    assert result["date"] == "2026-10-08"
    assert result["previous_date"] == "2026-10-07"
    assert [rate["code"] for rate in result["rates"]] == ["USD", "EUR", "CNY"]
    # Курс юаня пришёл за 10 единиц
    assert result["rates"][2]["value"] == pytest.approx(12.5)
    assert result["rates"][2]["previous"] == pytest.approx(12.4)


def test_big_change_is_not_rejected(respond):
    # Резкие скачки бывают в кризис, их помечает сводка, а не отбрасывает загрузка
    respond(make_payload(usd=(120.0, 90.0)))

    assert fetch_rates()["rates"][0]["value"] == 120.0


@pytest.mark.parametrize("value", [0, -5.0, float("nan"), float("inf"), True, "90,1", None])
def test_bad_value_is_rejected(respond, value):
    respond(make_payload(eur=(value, 99.0)))

    with pytest.raises(DataError, match="EUR.Value"):
        fetch_rates()


def test_zero_nominal_is_rejected(respond):
    respond(make_payload(cny_nominal=0))

    with pytest.raises(DataError, match="CNY.Nominal"):
        fetch_rates()


def test_missing_currency_is_rejected(respond):
    payload = make_payload()
    del payload["Valute"]["EUR"]
    respond(payload)

    with pytest.raises(DataError, match="формат"):
        fetch_rates()


def test_unexpected_structure_is_rejected(respond):
    respond({"Valute": []})

    with pytest.raises(DataError, match="формат"):
        fetch_rates()


@pytest.mark.parametrize("value", ["вчера", "2026-13-40T11:30:00+03:00", None])
def test_bad_date_is_rejected(respond, value):
    payload = make_payload()
    payload["Date"] = value
    respond(payload)

    with pytest.raises(DataError, match="дата"):
        fetch_rates()
