from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "bronze"
CURATED_DIR = PROJECT_ROOT / "data" / "structured" / "source"


def normalize_region(value: str) -> str:
    region = value.strip().lower().replace("_", " ").replace("-", " ")
    mapping = {
        "r1": "Region 1",
        "region 1": "Region 1",
        "r2": "Region 2",
        "region 2": "Region 2",
        "r3": "Region 3",
        "region 3": "Region 3",
        "r4": "Region 4",
        "region 4": "Region 4",
    }
    return mapping[region]


def normalize_metric(value: str) -> str:
    metric = value.strip().lower().replace(" ", "_")
    mapping = {
        "delivery_success": "delivery_success_rate",
        "delivery_success_rate": "delivery_success_rate",
        "on_time_delivery": "on_time_delivery_rate",
        "on_time_delivery_rate": "on_time_delivery_rate",
        "return rate": "return_rate",
        "return_rate": "return_rate",
    }
    return mapping.get(metric, metric)


def parse_bool(value: str) -> str:
    return str(value).strip().lower() in {"1", "true", "yes", "y"} and "true" or "false"


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_daily_kpis() -> list[dict[str, object]]:
    raw_rows = load_csv(RAW_DIR / "kpi_feed.csv")
    deduped: dict[tuple[str, str, str], dict[str, object]] = {}

    for row in raw_rows:
        metric_date = row["event_day"].strip()
        region = normalize_region(row["market"])
        metric_name = normalize_metric(row["metric_key"])
        extract_ts = parse_timestamp(row["extract_ts"])
        key = (metric_date, region, metric_name)
        candidate = {
            "metric_date": metric_date,
            "region": region,
            "metric_name": metric_name,
            "metric_value": f"{float(row['observed_value']):.2f}",
            "metric_target": f"{float(row['target_value']):.2f}",
            "anomaly_flag": parse_bool(row["anomaly_ind"]),
            "anomaly_severity": row["severity_label"].strip().lower(),
            "notes": row["note_text"].strip(),
            "data_as_of": extract_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "freshness_status": row["freshness_hint"].strip().lower(),
            "completeness_pct": f"{float(row['load_ratio']):.2f}",
            "_sort_key": extract_ts,
        }
        if key not in deduped or extract_ts > deduped[key]["_sort_key"]:
            deduped[key] = candidate

    rows = sorted(deduped.values(), key=lambda item: (item["metric_date"], item["region"], item["metric_name"]))
    for row in rows:
        row.pop("_sort_key", None)
    return rows


def build_shipment_events() -> list[dict[str, object]]:
    raw_rows = load_csv(RAW_DIR / "shipment_event_feed.csv")
    deduped: dict[str, dict[str, object]] = {}
    for row in raw_rows:
        event_id = row["event_id"].strip()
        loaded_at = parse_timestamp(row["loaded_at"])
        candidate = {
            "event_id": event_id,
            "event_date": row["event_day"].strip(),
            "ingestion_time": loaded_at.strftime("%Y-%m-%d %H:%M:%S"),
            "region": normalize_region(row["market"]),
            "shipment_id": row["shipment_ref"].strip(),
            "event_type": row["event_name"].strip(),
            "failure_reason": row["reason_code"].strip(),
            "delivery_hours": f"{float(row['delivery_hours']):.1f}",
            "source_system": row["source_name"].strip(),
            "_sort_key": loaded_at,
        }
        if event_id not in deduped or loaded_at > deduped[event_id]["_sort_key"]:
            deduped[event_id] = candidate

    rows = sorted(deduped.values(), key=lambda item: int(item["event_id"]))
    for row in rows:
        row.pop("_sort_key", None)
    return rows


def build_incidents() -> list[dict[str, object]]:
    raw_rows = load_csv(RAW_DIR / "incident_feed.csv")
    deduped: dict[str, dict[str, object]] = {}
    for row in raw_rows:
        incident_id = row["incident_ref"].strip()
        details = row["details"].strip()
        candidate = {
            "incident_id": incident_id,
            "incident_date": row["opened_on"].strip(),
            "region": normalize_region(row["market"]),
            "incident_type": row["incident_kind"].strip(),
            "severity": row["priority"].strip().lower(),
            "status": row["current_status"].strip().lower(),
            "summary": details,
            "source_team": row["owning_team"].strip(),
            "_sort_key": len(details),
        }
        if incident_id not in deduped or len(details) > deduped[incident_id]["_sort_key"]:
            deduped[incident_id] = candidate

    rows = sorted(deduped.values(), key=lambda item: item["incident_id"])
    for row in rows:
        row.pop("_sort_key", None)
    return rows


def build_metric_definitions() -> list[dict[str, object]]:
    raw_rows = load_csv(RAW_DIR / "metric_catalog.csv")
    rows: list[dict[str, object]] = []
    for row in raw_rows:
        rows.append(
            {
                "metric_name": normalize_metric(row["metric_key"]),
                "metric_owner": row["owner_name"].strip(),
                "metric_grain": row["grain_name"].strip(),
                "metric_definition": row["definition_text"].strip(),
                "investigation_hint": row["investigation_hint_text"].strip(),
                "definition_quality": row["quality_flag"].strip().lower(),
            }
        )

    return sorted(rows, key=lambda item: item["metric_name"])


def build_curated_data() -> dict[str, int]:
    CURATED_DIR.mkdir(parents=True, exist_ok=True)

    daily_kpis = build_daily_kpis()
    shipment_events = build_shipment_events()
    incidents = build_incidents()
    metric_definitions = build_metric_definitions()

    write_csv(
        CURATED_DIR / "daily_kpis.csv",
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
        daily_kpis,
    )
    write_csv(
        CURATED_DIR / "shipment_events.csv",
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
        shipment_events,
    )
    write_csv(
        CURATED_DIR / "incident_log.csv",
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
        incidents,
    )
    write_csv(
        CURATED_DIR / "metric_definitions.csv",
        [
            "metric_name",
            "metric_owner",
            "metric_grain",
            "metric_definition",
            "investigation_hint",
            "definition_quality",
        ],
        metric_definitions,
    )

    return {
        "daily_kpis": len(daily_kpis),
        "shipment_events": len(shipment_events),
        "incident_log": len(incidents),
        "metric_definitions": len(metric_definitions),
    }


if __name__ == "__main__":
    results = build_curated_data()
    print("Curated source data rebuilt from raw feeds.")
    for name, count in results.items():
        print(f"- {name}: {count} rows")
