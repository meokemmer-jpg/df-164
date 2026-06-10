from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Mapping, Any


REPORT_DIR = Path("reports")
STOP_FLAG = Path("/tmp/df-164.stop")


@dataclass(frozen=True)
class PipelineMetrics:
    pipeline_value_eur_total: float
    new_mandanten_30d: int
    conversion_rate_pct: float
    stale_pipeline_90d: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_value_eur_total": self.pipeline_value_eur_total,
            "new_mandanten_30d": self.new_mandanten_30d,
            "conversion_rate_pct": self.conversion_rate_pct,
            "stale_pipeline_90d": self.stale_pipeline_90d,
        }


def _to_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"Unsupported date value: {value!r}")


def compute_pipeline_metrics(
    records: Iterable[Mapping[str, Any]],
    *,
    as_of: date | str | datetime | None = None,
) -> PipelineMetrics:
    today = _to_date(as_of) or date.today()
    recent_cutoff = today - timedelta(days=30)
    stale_cutoff = today - timedelta(days=90)

    pipeline_value = 0.0
    new_mandanten = 0
    stale_pipeline = 0
    won = 0
    lost = 0

    for record in records:
        status = str(record.get("status", "")).strip().lower()
        value_eur = float(record.get("value_eur", 0) or 0)
        created_at = _to_date(record.get("created_at"))
        won_at = _to_date(record.get("won_at"))
        closed_at = _to_date(record.get("closed_at"))

        if status == "open":
            pipeline_value += value_eur
            if created_at is not None and created_at <= stale_cutoff:
                stale_pipeline += 1
        elif status == "won":
            won += 1
            effective_won_date = won_at or closed_at
            if effective_won_date is not None and effective_won_date >= recent_cutoff:
                new_mandanten += 1
        elif status == "lost":
            lost += 1

    decisions = won + lost
    conversion_rate = round((won / decisions) * 100, 2) if decisions else 0.0

    return PipelineMetrics(
        pipeline_value_eur_total=round(pipeline_value, 2),
        new_mandanten_30d=new_mandanten,
        conversion_rate_pct=conversion_rate,
        stale_pipeline_90d=stale_pipeline,
    )


def build_report(
    records: Iterable[Mapping[str, Any]],
    *,
    as_of: date | str | datetime | None = None,
) -> dict[str, Any]:
    metrics = compute_pipeline_metrics(records, as_of=as_of)
    report_date = (_to_date(as_of) or date.today()).isoformat()
    return {
        "factory": "df-164",
        "domain": "LexVance Revenue + Mandanten-Pipeline",
        "generated_at": report_date,
        "stop_flag_present": STOP_FLAG.exists(),
        "metrics": metrics.to_dict(),
    }


def write_report(
    records: Iterable[Mapping[str, Any]],
    *,
    as_of: date | str | datetime | None = None,
    report_dir: Path | str = REPORT_DIR,
) -> Path:
    report = build_report(records, as_of=as_of)
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    output_path = report_dir / f"df-164-{report['generated_at']}.json"
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return output_path
# [CRUX-MK]
