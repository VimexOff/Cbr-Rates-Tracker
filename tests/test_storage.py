import pytest

from storage import connect, mark_run_ok, mark_sent, save_rates, was_run_ok, was_sent


@pytest.fixture
def conn():
    conn = connect(":memory:")
    yield conn
    conn.close()


def make_result(usd: float) -> dict:
    return {
        "date": "2026-10-08",
        "previous_date": "2026-10-07",
        "rates": [{"code": "USD", "name": "Доллар США", "value": usd, "previous": 80.0}],
    }


def test_repeated_save_does_not_create_duplicates(conn):
    save_rates(conn, make_result(82.0))
    save_rates(conn, make_result(82.0))

    assert conn.execute("SELECT COUNT(*) FROM rates").fetchone()[0] == 2


def test_repeated_save_updates_value(conn):
    save_rates(conn, make_result(82.0))
    save_rates(conn, make_result(83.0))

    value = conn.execute("SELECT value FROM rates WHERE date = '2026-10-08'").fetchone()[0]
    assert value == 83.0


def test_sent_summaries(conn):
    assert not was_sent(conn, "2026-10-08")

    mark_sent(conn, "2026-10-08")
    mark_sent(conn, "2026-10-08")

    assert was_sent(conn, "2026-10-08")
    assert conn.execute("SELECT COUNT(*) FROM sent_summaries").fetchone()[0] == 1


def test_successful_runs(conn):
    assert not was_run_ok(conn, "2026-10-08")

    mark_run_ok(conn, "2026-10-08")

    assert was_run_ok(conn, "2026-10-08")
    assert not was_run_ok(conn, "2026-10-09")
