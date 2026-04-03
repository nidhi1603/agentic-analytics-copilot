from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CURATED_DIR = PROJECT_ROOT / "data" / "structured" / "source"


class DataQualityError(RuntimeError):
    pass


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise DataQualityError(message)


def run_quality_checks() -> list[str]:
    daily_kpis = load_csv(CURATED_DIR / "daily_kpis.csv")
    shipment_events = load_csv(CURATED_DIR / "shipment_events.csv")
    incidents = load_csv(CURATED_DIR / "incident_log.csv")
    metric_definitions = load_csv(CURATED_DIR / "metric_definitions.csv")
    access_policies = load_csv(CURATED_DIR / "access_policies.csv")

    messages: list[str] = []

    kpi_keys = {(row["metric_date"], row["region"], row["metric_name"]) for row in daily_kpis}
    ensure(len(kpi_keys) == len(daily_kpis), "daily_kpis contains duplicate region-day-metric rows")
    ensure(
        all(row["freshness_status"] in {"fresh", "lagging", "stale"} for row in daily_kpis),
        "daily_kpis contains unexpected freshness_status values",
    )
    ensure(
        all(0.0 <= float(row["completeness_pct"]) <= 1.0 for row in daily_kpis),
        "daily_kpis contains completeness_pct outside [0, 1]",
    )
    messages.append("daily_kpis: uniqueness, freshness, and completeness checks passed")

    shipment_ids = {row["event_id"] for row in shipment_events}
    ensure(len(shipment_ids) == len(shipment_events), "shipment_events contains duplicate event_id rows")
    ensure(
        all(row["region"].startswith("Region ") for row in shipment_events),
        "shipment_events contains unnormalized region values",
    )
    messages.append("shipment_events: dedupe and region normalization checks passed")

    incident_ids = {row["incident_id"] for row in incidents}
    ensure(len(incident_ids) == len(incidents), "incident_log contains duplicate incident_id rows")
    messages.append("incident_log: dedupe checks passed")

    metrics = {row["metric_name"] for row in metric_definitions}
    ensure(metrics == {row["metric_name"] for row in daily_kpis}, "metric_definitions does not cover all KPI metrics")
    messages.append("metric_definitions: coverage checks passed")

    policy_keys = {
        (row["role"], row["resource_type"], row["resource_name"]) for row in access_policies
    }
    ensure(len(policy_keys) == len(access_policies), "access_policies contains duplicate role-resource rows")
    messages.append("access_policies: uniqueness checks passed")

    return messages


if __name__ == "__main__":
    results = run_quality_checks()
    print("Data quality checks passed.")
    for message in results:
        print(f"- {message}")
