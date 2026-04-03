import csv
from pathlib import Path

from scripts.build_curated_data import build_curated_data
from scripts.run_data_quality_checks import run_quality_checks


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_build_curated_data_normalizes_and_deduplicates(monkeypatch, tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    curated_dir = tmp_path / "curated"

    write_csv(
        raw_dir / "kpi_feed.csv",
        [
            "event_day",
            "market",
            "metric_key",
            "observed_value",
            "target_value",
            "anomaly_ind",
            "severity_label",
            "note_text",
            "extract_ts",
            "freshness_hint",
            "load_ratio",
        ],
        [
            {
                "event_day": "2026-04-01",
                "market": "r4",
                "metric_key": "return rate",
                "observed_value": "0.11",
                "target_value": "0.08",
                "anomaly_ind": "yes",
                "severity_label": "medium",
                "note_text": "Latest row",
                "extract_ts": "2026-04-02 04:10:00",
                "freshness_hint": "lagging",
                "load_ratio": "0.74",
            },
            {
                "event_day": "2026-04-01",
                "market": "Region 4",
                "metric_key": "return_rate",
                "observed_value": "0.10",
                "target_value": "0.08",
                "anomaly_ind": "true",
                "severity_label": "medium",
                "note_text": "Older duplicate",
                "extract_ts": "2026-04-02 01:10:00",
                "freshness_hint": "lagging",
                "load_ratio": "0.66",
            },
        ],
    )
    write_csv(
        raw_dir / "shipment_event_feed.csv",
        [
            "event_id",
            "event_day",
            "loaded_at",
            "market",
            "shipment_ref",
            "event_name",
            "reason_code",
            "delivery_hours",
            "source_name",
        ],
        [
            {
                "event_id": "1008",
                "event_day": "2026-04-01",
                "loaded_at": "2026-04-02 04:05:00",
                "market": "R4",
                "shipment_ref": "SHP-008",
                "event_name": "return_initiated",
                "reason_code": "damaged_packaging",
                "delivery_hours": "12.3",
                "source_name": "returns_feed",
            }
        ],
    )
    write_csv(
        raw_dir / "incident_feed.csv",
        [
            "incident_ref",
            "opened_on",
            "market",
            "incident_kind",
            "priority",
            "current_status",
            "details",
            "owning_team",
        ],
        [
            {
                "incident_ref": "INC-401",
                "opened_on": "2026-04-01",
                "market": "Region 4",
                "incident_kind": "packaging_defect",
                "priority": "medium",
                "current_status": "open",
                "details": "Packaging issue increased return requests",
                "owning_team": "customer_experience",
            }
        ],
    )
    write_csv(
        raw_dir / "metric_catalog.csv",
        [
            "metric_key",
            "owner_name",
            "grain_name",
            "definition_text",
            "investigation_hint_text",
            "quality_flag",
        ],
        [
            {
                "metric_key": "return rate",
                "owner_name": "Customer Experience",
                "grain_name": "region-day",
                "definition_text": "Returned shipments divided by completed deliveries",
                "investigation_hint_text": "Inspect packaging issues",
                "quality_flag": "under_review",
            }
        ],
    )

    monkeypatch.setattr("scripts.build_curated_data.RAW_DIR", raw_dir)
    monkeypatch.setattr("scripts.build_curated_data.CURATED_DIR", curated_dir)

    results = build_curated_data()

    assert results["daily_kpis"] == 1
    with (curated_dir / "daily_kpis.csv").open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))

    assert row["region"] == "Region 4"
    assert row["metric_name"] == "return_rate"
    assert row["metric_value"] == "0.11"
    assert row["data_as_of"] == "2026-04-02 04:10:00"


def test_run_quality_checks_validates_curated_outputs(monkeypatch, tmp_path: Path) -> None:
    curated_dir = tmp_path / "curated"

    write_csv(
        curated_dir / "daily_kpis.csv",
        [
            "metric_date",
            "region",
            "metric_name",
            "metric_value",
            "metric_target",
            "anomaly_flag",
            "anomaly_severity",
            "notes",
            "data_as_of",
            "freshness_status",
            "completeness_pct",
        ],
        [
            {
                "metric_date": "2026-04-01",
                "region": "Region 4",
                "metric_name": "return_rate",
                "metric_value": "0.11",
                "metric_target": "0.08",
                "anomaly_flag": "true",
                "anomaly_severity": "medium",
                "notes": "Packaging issue",
                "data_as_of": "2026-04-02 04:10:00",
                "freshness_status": "lagging",
                "completeness_pct": "0.74",
            }
        ],
    )
    write_csv(
        curated_dir / "shipment_events.csv",
        [
            "event_id",
            "event_date",
            "ingestion_time",
            "region",
            "shipment_id",
            "event_type",
            "failure_reason",
            "delivery_hours",
            "source_system",
        ],
        [
            {
                "event_id": "1008",
                "event_date": "2026-04-01",
                "ingestion_time": "2026-04-02 04:05:00",
                "region": "Region 4",
                "shipment_id": "SHP-008",
                "event_type": "return_initiated",
                "failure_reason": "damaged_packaging",
                "delivery_hours": "12.3",
                "source_system": "returns_feed",
            }
        ],
    )
    write_csv(
        curated_dir / "incident_log.csv",
        [
            "incident_id",
            "incident_date",
            "region",
            "incident_type",
            "severity",
            "status",
            "summary",
            "source_team",
        ],
        [
            {
                "incident_id": "INC-401",
                "incident_date": "2026-04-01",
                "region": "Region 4",
                "incident_type": "packaging_defect",
                "severity": "medium",
                "status": "open",
                "summary": "Packaging issue increased return requests",
                "source_team": "customer_experience",
            }
        ],
    )
    write_csv(
        curated_dir / "metric_definitions.csv",
        [
            "metric_name",
            "metric_owner",
            "metric_grain",
            "metric_definition",
            "investigation_hint",
            "definition_quality",
        ],
        [
            {
                "metric_name": "return_rate",
                "metric_owner": "Customer Experience",
                "metric_grain": "region-day",
                "metric_definition": "Returned shipments divided by completed deliveries",
                "investigation_hint": "Inspect packaging issues",
                "definition_quality": "under_review",
            }
        ],
    )
    write_csv(
        curated_dir / "access_policies.csv",
        ["role", "resource_type", "resource_name", "permission", "restriction_reason"],
        [
            {
                "role": "exec_viewer",
                "resource_type": "structured",
                "resource_name": "shipment_events",
                "permission": "deny",
                "restriction_reason": "shipment_level_detail_is_not_available_to_exec_viewer",
            }
        ],
    )

    monkeypatch.setattr("scripts.run_data_quality_checks.CURATED_DIR", curated_dir)

    results = run_quality_checks()

    assert len(results) == 5
    assert any("daily_kpis" in result for result in results)
