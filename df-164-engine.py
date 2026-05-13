"""DF-164 LexVance-Mandanten-Pipeline tracker engine."""

import re
import os
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone


DF_DIR = Path(__file__).parent
LOCK_DIR = Path("/tmp/df-164.lock")
DF_ID = "164"
DECISION_KEYWORDS_REGEX = re.compile(
    r"\b(entscheid[a-z]*|empfehl(?:e|en|t|st)|sollt(?:e|en|est)|recommend[a-z]*|decid[a-z]*|advis[a-z]*|propos[a-z]*)\b",
    re.IGNORECASE,
)


@dataclass
class TrackerOutput:
    welle: str = "25"
    df: str = "DF-164"
    iso_timestamp: str = ""
    source: str = "mock"
    leads_total: int = 0
    qualified_leads: int = 0
    conversion_rate: float = 0
    mrr_pipeline_eur: float = 0
    deal_stages: dict = field(default_factory=dict)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_stable(path, min_age_sec=300) -> bool:
    p = Path(path)
    if not p.exists():
        return False
    try:
        age_sec = time.time() - p.stat().st_mtime
    except OSError:
        return False
    return age_sec >= min_age_sec


def _remove_lock_dir() -> None:
    if not LOCK_DIR.exists():
        return
    try:
        for child in LOCK_DIR.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
        LOCK_DIR.rmdir()
    except OSError:
        pass


def acquire_lock_with_identity() -> bool:
    stale_after_sec = 6 * 60 * 60

    if LOCK_DIR.exists():
        try:
            age_sec = time.time() - LOCK_DIR.stat().st_mtime
            if age_sec >= stale_after_sec:
                _remove_lock_dir()
        except OSError:
            pass

    try:
        LOCK_DIR.mkdir(mode=0o700)
    except FileExistsError:
        return False
    except OSError:
        return False

    identity = {
        "df_id": DF_ID,
        "pid": os.getpid(),
        "cwd": str(Path.cwd()),
        "iso_timestamp": iso_now(),
    }
    try:
        (LOCK_DIR / "identity.json").write_text(
            json.dumps(identity, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        release_lock()
        return False
    return True


def release_lock() -> None:
    _remove_lock_dir()


def k17_pre_action_verification(anchors) -> dict:
    missing_anchors = []
    for anchor in anchors or []:
        if not anchor:
            continue
        path = Path(anchor)
        if not path.exists() or not _file_stable(path):
            missing_anchors.append(str(path))

    return {
        "ok": not missing_anchors,
        "missing_anchors": missing_anchors,
        "env_tag": os.environ.get("DF_164_ENV_TAG", "local"),
    }


def _is_real_api_enabled() -> bool:
    raw = os.environ.get("DF_164_REAL_API_ENABLED", "false")
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def scan_output_for_decision_keywords(text) -> list:
    if text is None:
        return []
    seen = set()
    matches = []
    for match in DECISION_KEYWORDS_REGEX.finditer(str(text)):
        value = match.group(0).lower()
        if value not in seen:
            seen.add(value)
            matches.append(match.group(0))
    return matches


def assert_no_decision_keywords(output) -> None:
    if not isinstance(output, str):
        output = json.dumps(output, ensure_ascii=False, sort_keys=True)
    matches = scan_output_for_decision_keywords(output)
    if matches:
        raise ValueError(
            "Q_0/K_0 decision keyword block triggered: " + ", ".join(matches)
        )


def _as_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _mock_tracker_output() -> TrackerOutput:
    return TrackerOutput(
        iso_timestamp=iso_now(),
        source="mock",
        leads_total=_as_int(os.environ.get("DF_164_MOCK_LEADS_TOTAL"), 0),
        qualified_leads=_as_int(os.environ.get("DF_164_MOCK_QUALIFIED_LEADS"), 0),
        conversion_rate=_as_float(os.environ.get("DF_164_MOCK_CONVERSION_RATE"), 0.0),
        mrr_pipeline_eur=_as_float(os.environ.get("DF_164_MOCK_MRR_PIPELINE_EUR"), 0.0),
        deal_stages=_load_deal_stages(os.environ.get("DF_164_MOCK_DEAL_STAGES_JSON")),
    )


def _load_deal_stages(raw) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def collect_tracker_output() -> TrackerOutput:
    if not _is_real_api_enabled():
        return _mock_tracker_output()

    raw = os.environ.get("DF_164_REAL_API_PAYLOAD_JSON", "{}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    stages = payload.get("deal_stages", {})
    if not isinstance(stages, dict):
        stages = {}

    return TrackerOutput(
        iso_timestamp=iso_now(),
        source="real",
        leads_total=_as_int(payload.get("leads_total"), 0),
        qualified_leads=_as_int(payload.get("qualified_leads"), 0),
        conversion_rate=_as_float(payload.get("conversion_rate"), 0.0),
        mrr_pipeline_eur=_as_float(payload.get("mrr_pipeline_eur"), 0.0),
        deal_stages=stages,
    )


def _report_path() -> Path:
    date_part = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return DF_DIR / "reports" / f"df-164-{date_part}.json"


def _anchors_from_env() -> list:
    raw = os.environ.get("DF_164_ANCHORS", "")
    if not raw.strip():
        return []
    return [item for item in raw.split(os.pathsep) if item.strip()]


def _write_report(report) -> None:
    report_json = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    assert_no_decision_keywords(report_json)
    path = _report_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_json + "\n", encoding="utf-8")


def main() -> int:
    if not acquire_lock_with_identity():
        return 3

    try:
        pav = k17_pre_action_verification(_anchors_from_env())
        tracker = collect_tracker_output()

        report = {
            "df_id": DF_ID,
            "report_slug": "df-164",
            "status": "ok" if pav.get("ok") else "blocked",
            "k17_pre_action_verification": pav,
            "tracker_output": asdict(tracker),
        }

        _write_report(report)
        return 0 if pav.get("ok") else 3
    except ValueError as exc:
        try:
            fallback = {
                "df_id": DF_ID,
                "report_slug": "df-164",
                "status": "blocked",
                "error": str(exc),
                "iso_timestamp": iso_now(),
            }
            path = _report_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(fallback, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        return 3
    except OSError:
        return 3
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())