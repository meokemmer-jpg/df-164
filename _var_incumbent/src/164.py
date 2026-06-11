from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
import json


ACTIVE_STATUSES = {"new", "qualified", "proposal", "negotiation"}
CLOSED_WON = "won"
CLOSED_LOST = "lost"
DEFAULT_STOP_FLAG = Path("/tmp/df-164.stop")


@dataclass(frozen=True)
class PipelineRecord:
    mandant_id: str
    status: str
    value_eur: float
    created_at: str
    last_activity_at: str
    closed_at: str | None = None


def _to_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _normalize_record(record: PipelineRecord | dict) -> PipelineRecord:
    if isinstance(record, PipelineRecord):
        return record
    return PipelineRecord(**record)


def stop_requested(stop_flag: str | Path = DEFAULT_STOP_FLAG) -> bool:
    return Path(stop_flag).exists()


def compute_metrics(
    records: list[PipelineRecord | dict],
    *,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    normalized = [_normalize_record(record) for record in records]

    pipeline_value_eur_total = round(
        sum(record.value_eur for record in normalized if record.status in ACTIVE_STATUSES),
        2,
    )

    new_mandanten_30d = sum(
        1
        for record in normalized
        if record.status == CLOSED_WON
        and record.closed_at is not None
        and (today - _to_date(record.closed_at)).days <= 30
    )

    closed_records = [record for record in normalized if record.status in {CLOSED_WON, CLOSED_LOST}]
    won_records = [record for record in closed_records if record.status == CLOSED_WON]
    conversion_rate_pct = round(
        (len(won_records) / len(closed_records) * 100.0) if closed_records else 0.0,
        2,
    )

    stale_pipeline_90d = sum(
        1
        for record in normalized
        if record.status in ACTIVE_STATUSES
        and (today - _to_date(record.last_activity_at)).days > 90
    )

    return {
        "pipeline_value_eur_total": pipeline_value_eur_total,
        "new_mandanten_30d": new_mandanten_30d,
        "conversion_rate_pct": conversion_rate_pct,
        "stale_pipeline_90d": stale_pipeline_90d,
    }


def build_report(
    records: list[PipelineRecord | dict],
    *,
    today: date | None = None,
    stop_flag: str | Path = DEFAULT_STOP_FLAG,
) -> dict:
    if stop_requested(stop_flag):
        raise RuntimeError(f"STOP flag present: {Path(stop_flag)}")

    today = today or date.today()
    normalized = [_normalize_record(record) for record in records]

    return {
        "mission": "df-164",
        "generated_at": today.isoformat(),
        "metrics": compute_metrics(normalized, today=today),
        "records": [asdict(record) for record in normalized],
    }


def write_report(
    records: list[PipelineRecord | dict],
    *,
    reports_dir: str | Path = "reports",
    today: date | None = None,
    stop_flag: str | Path = DEFAULT_STOP_FLAG,
) -> Path:
    today = today or date.today()
    report = build_report(records, today=today, stop_flag=stop_flag)

    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)

    output_path = reports_path / f"df-164-{today.isoformat()}.json"
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return output_path
# [CRUX-MK]
