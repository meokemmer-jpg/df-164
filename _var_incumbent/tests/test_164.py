import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
import json
from datetime import date
from importlib import import_module

import pytest

m164 = import_module("164")
PipelineRecord = m164.PipelineRecord
build_report = m164.build_report
compute_metrics = m164.compute_metrics
write_report = m164.write_report


def test_compute_metrics_and_report_write(tmp_path):
    records = [
        PipelineRecord(
            mandant_id="A1",
            status="new",
            value_eur=10000.0,
            created_at="2026-05-01",
            last_activity_at="2026-06-01",
        ),
        PipelineRecord(
            mandant_id="A2",
            status="negotiation",
            value_eur=25000.0,
            created_at="2026-02-01",
            last_activity_at="2026-02-15",
        ),
        PipelineRecord(
            mandant_id="A3",
            status="won",
            value_eur=15000.0,
            created_at="2026-05-01",
            last_activity_at="2026-05-20",
            closed_at="2026-05-25",
        ),
        PipelineRecord(
            mandant_id="A4",
            status="lost",
            value_eur=5000.0,
            created_at="2026-04-01",
            last_activity_at="2026-04-20",
            closed_at="2026-05-28",
        ),
    ]

    today = date(2026, 6, 10)
    metrics = compute_metrics(records, today=today)

    assert metrics == {
        "pipeline_value_eur_total": 35000.0,
        "new_mandanten_30d": 1,
        "conversion_rate_pct": 50.0,
        "stale_pipeline_90d": 1,
    }

    output = write_report(records, reports_dir=tmp_path, today=today, stop_flag=tmp_path / "no.stop")
    assert output.name == "df-164-2026-06-10.json"

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["mission"] == "df-164"
    assert payload["generated_at"] == "2026-06-10"
    assert payload["metrics"] == metrics
    assert len(payload["records"]) == 4


def test_build_report_respects_stop_flag(tmp_path):
    stop_flag = tmp_path / "df-164.stop"
    stop_flag.write_text("stop", encoding="utf-8")

    with pytest.raises(RuntimeError, match="STOP flag present"):
        build_report([], today=date(2026, 6, 10), stop_flag=stop_flag)

