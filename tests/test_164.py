import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
import importlib

m164 = importlib.import_module("164")
compute_pipeline_metrics = m164.compute_pipeline_metrics
build_report = m164.build_report


def test_compute_pipeline_metrics_and_report():
    records = [
        {"status": "open", "value_eur": 10000, "created_at": "2026-02-01"},
        {"status": "open", "value_eur": 5000, "created_at": "2026-06-01"},
        {"status": "won", "value_eur": 7000, "won_at": "2026-05-20"},
        {"status": "won", "value_eur": 9000, "won_at": "2026-04-01"},
        {"status": "lost", "value_eur": 3000, "closed_at": "2026-05-25"},
    ]

    metrics = compute_pipeline_metrics(records, as_of="2026-06-09")

    assert metrics.pipeline_value_eur_total == 15000.0
    assert metrics.new_mandanten_30d == 1
    assert metrics.conversion_rate_pct == 66.67
    assert metrics.stale_pipeline_90d == 1

    report = build_report(records, as_of="2026-06-09")

    assert report["factory"] == "df-164"
    assert report["generated_at"] == "2026-06-09"
    assert report["metrics"] == {
        "pipeline_value_eur_total": 15000.0,
        "new_mandanten_30d": 1,
        "conversion_rate_pct": 66.67,
        "stale_pipeline_90d": 1,
    }
    assert report["stop_flag_present"] is False
