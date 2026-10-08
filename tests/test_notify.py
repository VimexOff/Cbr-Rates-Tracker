import pandas as pd

from analysis import summarize
from notify import format_summary


def make_rates(usd_previous: float, usd_latest: float) -> pd.DataFrame:
    rates = pd.DataFrame(
        {
            "USD": [usd_previous, usd_latest],
            "EUR": [90.0, 90.5],
            "CNY": [12.0, 12.1],
        },
        index=pd.to_datetime(["2026-10-07", "2026-10-08"]),
    )
    return rates


def test_summary_has_all_currencies():
    rates = make_rates(80.0, 81.0)

    text = format_summary(rates, summarize(rates))

    assert "Курсы ЦБ РФ на 08.10.2026" in text
    assert "Изменение к 07.10.2026" in text
    for code in ("USD", "EUR", "CNY"):
        assert code in text
    assert "⚠️" not in text


def test_unusual_change_adds_warning():
    rates = make_rates(80.0, 100.0)

    text = format_summary(rates, summarize(rates))

    assert "⚠️ USD: изменение +25.00% за день" in text
    assert "EUR: изменение" not in text
