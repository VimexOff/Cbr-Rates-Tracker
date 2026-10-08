import pandas as pd
import pytest

from analysis import summarize


def make_rates(values: dict[str, dict[str, float]]) -> pd.DataFrame:
    # Таблица в том же виде, что возвращает load_rates: строки — даты, колонки — валюты
    rates = pd.DataFrame.from_dict(values, orient="index")
    rates.index = pd.to_datetime(rates.index)
    return rates.sort_index()


def test_day_change():
    rates = make_rates({
        "2026-10-07": {"USD": 80.0, "EUR": 90.0, "CNY": 12.0},
        "2026-10-08": {"USD": 82.0, "EUR": 89.1, "CNY": 12.0},
    })
    summary = summarize(rates)

    assert summary.loc["USD", "value"] == 82.0
    assert summary.loc["USD", "day_change"] == pytest.approx(2.0)
    assert summary.loc["USD", "day_change_pct"] == pytest.approx(2.5)
    assert summary.loc["EUR", "day_change_pct"] == pytest.approx(-1.0)
    assert summary.loc["CNY", "day_change"] == 0


def test_day_change_uses_previous_row_across_weekend():
    # После субботы следующий курс начинает действовать во вторник
    rates = make_rates({
        "2026-10-03": {"USD": 80.0, "EUR": 90.0, "CNY": 12.0},
        "2026-10-06": {"USD": 84.0, "EUR": 90.0, "CNY": 12.0},
    })
    summary = summarize(rates)

    assert summary.loc["USD", "day_change"] == pytest.approx(4.0)


def test_week_change():
    rates = make_rates({
        "2026-10-01": {"USD": 80.0, "EUR": 90.0, "CNY": 12.0},
        "2026-10-07": {"USD": 83.0, "EUR": 91.0, "CNY": 12.5},
        "2026-10-08": {"USD": 84.0, "EUR": 99.0, "CNY": 12.0},
    })
    summary = summarize(rates)

    assert summary.loc["USD", "week_change_pct"] == pytest.approx(5.0)
    assert summary.loc["EUR", "week_change_pct"] == pytest.approx(10.0)
    assert summary.loc["CNY", "week_change_pct"] == pytest.approx(0.0)


def test_week_change_falls_back_to_earlier_date():
    # Ровно неделю назад (04.10, воскресенье) курса нет, берётся последний до этой даты
    rates = make_rates({
        "2026-10-03": {"USD": 80.0, "EUR": 90.0, "CNY": 12.0},
        "2026-10-06": {"USD": 90.0, "EUR": 90.0, "CNY": 12.0},
        "2026-10-10": {"USD": 88.0, "EUR": 90.0, "CNY": 12.0},
        "2026-10-11": {"USD": 84.0, "EUR": 90.0, "CNY": 12.0},
    })
    summary = summarize(rates)

    assert summary.loc["USD", "week_change_pct"] == pytest.approx(5.0)


def test_week_change_is_empty_without_history():
    rates = make_rates({
        "2026-10-07": {"USD": 80.0, "EUR": 90.0, "CNY": 12.0},
        "2026-10-08": {"USD": 82.0, "EUR": 89.1, "CNY": 12.0},
    })
    summary = summarize(rates)

    assert summary["week_change_pct"].isna().all()


def test_currencies_in_fixed_order():
    rates = make_rates({
        "2026-10-07": {"CNY": 12.0, "EUR": 90.0, "USD": 80.0},
        "2026-10-08": {"CNY": 12.0, "EUR": 90.0, "USD": 80.0},
    })

    assert list(summarize(rates).index) == ["USD", "EUR", "CNY"]


def test_needs_at_least_two_days():
    rates = make_rates({"2026-10-08": {"USD": 80.0, "EUR": 90.0, "CNY": 12.0}})

    with pytest.raises(ValueError):
        summarize(rates)
