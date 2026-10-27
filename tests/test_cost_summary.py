from types import SimpleNamespace

from extract_eval.cli import cost_summary, model_calls


def test_model_calls_found_on_llm_or_wrapped_llm():
    assert model_calls(SimpleNamespace(calls=3)) == 3
    assert model_calls(SimpleNamespace(llm=SimpleNamespace(calls=2))) == 2
    assert model_calls(SimpleNamespace()) == 0


def test_cost_summary_percentiles():
    lat = [float(x) for x in range(1, 101)]
    out = cost_summary(SimpleNamespace(llm=SimpleNamespace(calls=50)), lat)
    assert out["docs"] == 100 and out["model_calls_per_doc"] == 0.5
    assert out["p50_ms"] == 51.0 and out["p95_ms"] == 96.0
