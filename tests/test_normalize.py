import pytest

from extract_eval.normalize import parse_date, parse_int, parse_money, parse_percent, parse_text


@pytest.mark.parametrize("raw", ["$12,500,000", "USD 12.5 million", "$12.5MM", "12500000", 12_500_000])
def test_money_formats_agree(raw):
    assert parse_money(raw) == 12_500_000


def test_money_rejects_unknown_suffix():
    assert parse_money("12 widgets") is None


@pytest.mark.parametrize("raw,expected", [("6.25%", 6.25), ("625 bps", 6.25), ("6.25 percent", 6.25), (6.25, 6.25)])
def test_percent(raw, expected):
    assert parse_percent(raw) == expected


@pytest.mark.parametrize("raw", ["2031-03-01", "March 1, 2031", "1 Mar 2031", "03/01/2031"])
def test_dates(raw):
    assert parse_date(raw) == "2031-03-01"


def test_int_and_text():
    assert parse_int("1,204 units") == 1204
    assert parse_text("  Harbor Point   Holdings LLC. ") == "harbor point holdings llc"
