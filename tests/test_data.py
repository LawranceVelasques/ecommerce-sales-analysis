"""Checks on the cleaned data and on the analysis numbers."""
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import clean  # noqa: E402


@pytest.fixture(scope="module")
def tables():
    t, _ = clean.clean()
    return t


@pytest.fixture(scope="module")
def conn(tables):
    c = sqlite3.connect(":memory:")
    for name, df in tables.items():
        df.to_sql(name, c, index=False)
    yield c
    c.close()


def test_no_duplicate_lines(tables):
    assert not tables["order_items"].duplicated().any()


def test_prices_and_quantities_are_positive(tables):
    items = tables["order_items"]
    assert (items["unit_price"] > 0).all()
    assert (items["quantity"] >= 1).all()
    assert items["discount"].between(0, 1).all()


def test_no_missing_values_left(tables):
    for name, df in tables.items():
        assert not df.isna().any().any(), name


def test_city_names_are_standardised(tables):
    assert sorted(tables["customers"]["city"].unique()) == sorted(
        ["Jakarta", "Tangerang", "Bekasi", "Bandung", "Surabaya", "Medan", "Semarang", "Makassar", "Yogyakarta"])


def test_every_line_has_an_order_and_every_order_a_customer(tables):
    assert tables["order_items"]["order_id"].isin(tables["orders"]["order_id"]).all()
    assert tables["orders"]["customer_id"].isin(tables["customers"]["customer_id"]).all()


def test_all_orders_are_in_2025(tables):
    assert (tables["orders"]["order_ts"].dt.year == 2025).all()


def test_sql_revenue_matches_pandas(tables, conn):
    """Cross-check: the SQL query and an independent pandas calculation agree."""
    sql = pd.read_sql((ROOT / "sql" / "01_monthly_revenue.sql").read_text(), conn)
    items = tables["order_items"]
    expected = (items["quantity"] * items["unit_price"] * (1 - items["discount"])).round(0)[~items["returned"]].sum()
    assert sql["revenue"].sum() == pytest.approx(expected)


def test_category_shares_add_to_100(conn):
    cat = pd.read_sql((ROOT / "sql" / "02_category_performance.sql").read_text(), conn)
    assert cat["revenue_share_pct"].sum() == pytest.approx(100, abs=0.2)


def test_deciles_cover_every_customer_once(conn, tables):
    dec = pd.read_sql((ROOT / "sql" / "05_customer_concentration.sql").read_text(), conn)
    assert dec["customers"].sum() == tables["orders"]["customer_id"].nunique()
    assert dec["revenue_share_pct"].sum() == pytest.approx(100, abs=0.2)
