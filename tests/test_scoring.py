from extract_eval.scoring import field_correct, regressions, score

EXPECTED = {"borrower": "Oak Owner LLC", "property_address": "1 Main Street, Austin, TX 78701",
            "loan_amount": 12_500_000, "interest_rate": 6.25, "maturity_date": "2031-03-01",
            "ltv": 65.0, "noi": 1_234_000, "units": 120}


def test_equivalent_formats_score_correct():
    assert field_correct("loan_amount", "$12.5MM", 12_500_000)
    assert field_correct("interest_rate", "625 bps", 6.25)
    assert not field_correct("interest_rate", "1.00%", 6.25)


def test_score_counts_blanks_separately_from_wrong_values():
    predicted = dict(EXPECTED, units=None, noi="$9,999")
    summary = score([{"doc": "d", "layout": "x", "expected": EXPECTED, "predicted": predicted}])
    assert summary["accuracy"] == 0.75
    assert summary["wrong_not_blank"] == 1


def test_regression_gate():
    base = {"per_field": {"ltv": 0.95, "noi": 0.90}}
    cur = {"per_field": {"ltv": 0.80, "noi": 0.89}}
    assert regressions(cur, base, max_drop=0.02) == {"ltv": (0.95, 0.80)}
