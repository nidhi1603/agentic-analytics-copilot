from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time
from statistics import mean
from typing import Any

from app.db.duckdb_client import get_connection
from app.schemas.ask import AllowedRole
from app.services.policy_service import is_resource_allowed


THRESHOLDS = {
    "delivery_success_rate": {"green": 70, "amber": 65, "red": 0},
    "avg_delivery_hours": {"green": 0, "amber": 4, "red": 6},
    "return_rate": {"green": 0, "amber": 7, "red": 10},
    "sla_compliance": {"green": 85, "amber": 75, "red": 0},
    "open_incidents_24h": {"green": 0, "amber": 3, "red": 5},
    "incident_resolution_hours": {"green": 0, "amber": 12, "red": 24},
}

HIGHER_IS_BETTER = {"delivery_success_rate", "sla_compliance"}
ROLE_DEFAULT_REGION = {"regional_manager": "Region 3"}
ROLE_RESTRICTIONS = {
    "operations_analyst": [
        "Financial data and executive summaries are not visible in this dashboard.",
    ],
    "regional_manager": [
        "Raw shipment logs, analyst-only incident notes, and financial impact data are not visible to this role.",
    ],
    "exec_viewer": [
        "Raw incident logs, individual shipment events, operational SOPs, and runbooks are not visible to this role.",
    ],
}


def get_status(metric_name: str, value: float) -> tuple[str, str]:
    threshold = THRESHOLDS[metric_name]
    if metric_name in HIGHER_IS_BETTER:
        if value >= threshold["green"]:
            return "green", "Normal"
        if value >= threshold["amber"]:
            return "amber", "Watch"
        return "red", "Critical"

    if value <= threshold["green"]:
        return "green", "Normal"
    if value <= threshold["amber"]:
        return "amber", "Watch"
    return "red", "Critical"


def get_dashboard_for_role(role: AllowedRole) -> dict[str, Any]:
    if role == "operations_analyst":
        return get_ops_analyst_metrics()
    if role == "regional_manager":
        return get_regional_manager_metrics(ROLE_DEFAULT_REGION["regional_manager"])
    return get_exec_metrics()


def get_ops_analyst_metrics() -> dict[str, Any]:
    return _build_dashboard(role="operations_analyst", region=None)


def get_regional_manager_metrics(region: str) -> dict[str, Any]:
    return _build_dashboard(role="regional_manager", region=region)


def get_exec_metrics() -> dict[str, Any]:
    return _build_dashboard(role="exec_viewer", region=None)


def _build_dashboard(role: AllowedRole, region: str | None) -> dict[str, Any]:
    connection = get_connection()
    try:
        context = _load_dashboard_context(connection)
    finally:
        connection.close()

    if role == "operations_analyst":
        return _build_ops_dashboard(context)
    if role == "regional_manager":
        return _build_regional_dashboard(context, region or ROLE_DEFAULT_REGION["regional_manager"])
    return _build_exec_dashboard(context)


def _build_ops_dashboard(context: dict[str, Any]) -> dict[str, Any]:
    alerts = _build_ops_alerts(context)
    latest_kpis = context["latest_kpis"]
    recent_shipments = context["recent_shipments"]
    latest_delivery_rows = [
        row for row in latest_kpis if row["metric_name"] == "delivery_success_rate"
    ]
    overall_delivery_pct = _average_metric(latest_delivery_rows)
    avg_delivery_hours = _average_delivery_hours(recent_shipments)
    unresolved_count, over_24h_count, avg_incident_age_hours = _incident_health(
        context["incidents"], context["reference_time"]
    )
    freshness_value, freshness_status = _pipeline_freshness(context)
    return_rate_pct = _average_metric(
        [row for row in latest_kpis if row["metric_name"] == "return_rate"]
    )

    sections = [
        {
            "title": "Real-time operations",
            "metrics": [
                _metric_card(
                    "Delivery success rate",
                    overall_delivery_pct,
                    "delivery_success_rate",
                    detail="Average latest delivery success across visible regions",
                ),
                _metric_card(
                    "Avg delivery time",
                    avg_delivery_hours,
                    "avg_delivery_hours",
                    unit="hours",
                    detail="Recent shipment events in the latest operating window",
                ),
                _metric_card(
                    "Open incidents",
                    float(unresolved_count),
                    "open_incidents_24h",
                    unit="count",
                    detail=f"{over_24h_count} unresolved incident(s) older than 24h",
                ),
                {
                    "label": "Pipeline freshness",
                    "value": freshness_value,
                    "display_value": freshness_value,
                    "status": freshness_status,
                    "status_text": "Within SLA" if freshness_status == "green" else "Delayed feed",
                    "detail": f"Reference snapshot at {context['reference_time'].strftime('%Y-%m-%d %H:%M')}",
                },
            ],
        },
        {
            "title": "Regional breakdown",
            "metrics": [_region_card(row) for row in latest_delivery_rows],
        },
    ]

    shipment_allowed, _ = is_resource_allowed("operations_analyst", "structured", "shipment_events")
    if shipment_allowed:
        total_shipments = len(recent_shipments)
        failed_shipments = sum(
            1
            for row in recent_shipments
            if row["event_type"] in {"delivery_failed", "delivery_delayed"}
        )
        sections.append(
            {
                "title": "Shipment events (last 24h)",
                "metrics": [
                    _display_metric(
                        "Total shipments",
                        total_shipments,
                        "green",
                        "Normal volume",
                        "count",
                    ),
                    _display_metric(
                        "Failed deliveries",
                        failed_shipments,
                        "red" if failed_shipments else "green",
                        "Operational exceptions in latest shipment window",
                        "count",
                    ),
                    _metric_card(
                        "Return rate",
                        return_rate_pct,
                        "return_rate",
                        detail="Latest return-rate KPI",
                    ),
                    _metric_card(
                        "Incident handling age",
                        avg_incident_age_hours,
                        "incident_resolution_hours",
                        unit="hours",
                        detail="Average age of unresolved incidents",
                    ),
                ],
            }
        )

    return {
        "role": "operations_analyst",
        "role_label": "Operations analyst view",
        "badge_label": "ops analyst",
        "assigned_region": None,
        "generated_at": context["reference_time"].isoformat(),
        "auto_refresh_seconds": 60,
        "alerts": alerts,
        "sections": sections,
        "restricted": ROLE_RESTRICTIONS["operations_analyst"],
    }


def _build_regional_dashboard(context: dict[str, Any], region: str) -> dict[str, Any]:
    latest_kpis = [row for row in context["latest_kpis"] if row["region"] == region]
    incidents = [row for row in context["incidents"] if row["region"] == region]
    delivery_pct = _latest_metric_value(latest_kpis, "delivery_success_rate")
    sla_pct = _latest_metric_value(latest_kpis, "on_time_delivery_rate")
    return_rate_pct = _latest_metric_value(latest_kpis, "return_rate")
    unresolved_count, over_24h_count, avg_incident_age_hours = _incident_health(
        incidents, context["reference_time"]
    )
    delivery_trend = _trend_summary(context["kpi_history"], "delivery_success_rate", region=region)
    return_trend = _trend_summary(context["kpi_history"], "return_rate", region=region)

    regional_values = [
        row
        for row in context["latest_kpis"]
        if row["metric_name"] == "delivery_success_rate"
    ]
    regional_average = _average_metric(regional_values)
    regional_rank = _regional_rank(regional_values, region)
    rank_status = "red" if regional_rank == len(regional_values) and regional_rank > 1 else "amber"

    alerts = []
    delivery_status = _metric_card(
        "Delivery success rate",
        delivery_pct,
        "delivery_success_rate",
        detail="Latest visible KPI snapshot",
    )
    alerts.extend(_alert_for_metric(region, delivery_status, runbook=True))

    sla_metric = _metric_card(
        "SLA compliance",
        sla_pct,
        "sla_compliance",
        detail="Derived from on-time delivery KPI for the assigned region",
    )
    if sla_metric["status"] == "red":
        alerts.append(
            _alert(
                "red",
                "Escalation threshold breached",
                f"{region} SLA compliance is {sla_pct:.1f}%, below the 75% threshold.",
                "Notify VP Operations within 4 hours if the issue remains unresolved.",
            )
        )

    if return_trend and return_trend["is_bad_trend"]:
        alerts.append(
            _alert(
                "amber",
                "Return rate trending up",
                return_trend["message"],
                "Investigate root cause and review product-quality signals.",
            )
        )

    if over_24h_count:
        alerts.append(
            _alert(
                "red",
                "Incidents unresolved for >24 hours",
                f"{over_24h_count} incident(s) in {region} have been open longer than 24 hours.",
                "Use the escalation policy and coordinate analyst follow-up.",
            )
        )

    comparison_delta = delivery_pct - regional_average
    sections = [
        {
            "title": f"My region performance ({region})",
            "metrics": [
                delivery_status,
                _display_metric(
                    "Incident resolution",
                    unresolved_count,
                    "red" if over_24h_count else "amber" if unresolved_count else "green",
                    f"{over_24h_count} incident(s) older than 24h",
                    "count",
                ),
                sla_metric,
            ],
        },
        {
            "title": "Cross-region comparison",
            "metrics": [
                _display_metric(
                    f"{region} vs avg",
                    comparison_delta,
                    "red" if comparison_delta < -10 else "amber" if comparison_delta < -3 else "green",
                    "Compared with the current cross-region delivery average",
                    "delta_pct",
                ),
                _display_metric(
                    "Rank (of visible regions)",
                    regional_rank,
                    rank_status,
                    "1 is best performing",
                    "rank",
                ),
                _display_metric(
                    "3-day trend",
                    delivery_trend["label"] if delivery_trend else "Insufficient data",
                    "red" if delivery_trend and delivery_trend["is_bad_trend"] else "green",
                    delivery_trend["message"] if delivery_trend else "Need 3 daily snapshots to score trend",
                    "text",
                ),
            ],
        },
    ]

    incident_allowed, _ = is_resource_allowed("regional_manager", "structured", "incident_log")
    if incident_allowed:
        sections.append(
            {
                "title": "Incident details",
                "metrics": [
                    _metric_card(
                        "Avg incident age",
                        avg_incident_age_hours,
                        "incident_resolution_hours",
                        unit="hours",
                        detail="Average age of unresolved incidents in the assigned region",
                    ),
                    _display_metric(
                        "Escalated incidents",
                        sum(1 for item in incidents if item["severity"] == "high"),
                        "amber" if incidents else "green",
                        "High-severity incidents requiring leadership visibility",
                        "count",
                    ),
                ],
            }
        )

    return {
        "role": "regional_manager",
        "role_label": "Regional manager view",
        "badge_label": "regional mgr",
        "assigned_region": region,
        "generated_at": context["reference_time"].isoformat(),
        "auto_refresh_seconds": 60,
        "alerts": alerts,
        "sections": sections,
        "restricted": ROLE_RESTRICTIONS["regional_manager"],
    }


def _build_exec_dashboard(context: dict[str, Any]) -> dict[str, Any]:
    latest_kpis = context["latest_kpis"]
    delivery_rows = [
        row for row in latest_kpis if row["metric_name"] == "delivery_success_rate"
    ]
    overall_delivery_pct = _average_metric(delivery_rows)
    region_states = _region_health(latest_kpis)
    critical_regions = [item for item in region_states if item["status"] == "red"]
    warning_regions = [item for item in region_states if item["status"] == "amber"]
    company_trend = _trend_summary(context["kpi_history"], "delivery_success_rate", region=None)
    active_alerts = len(critical_regions) + len(warning_regions)
    recent_shipments = context["recent_shipments"]

    alerts = []
    if critical_regions or warning_regions:
        summary_parts = []
        if critical_regions:
            summary_parts.append(
                f"{len(critical_regions)} region critical ({', '.join(item['label'] for item in critical_regions)})"
            )
        if warning_regions:
            summary_parts.append(
                f"{len(warning_regions)} region on watch ({', '.join(item['label'] for item in warning_regions)})"
            )
        alerts.append(
            _alert(
                "amber" if not critical_regions else "red",
                "Company summary",
                ". ".join(summary_parts) + ".",
                "Request an analyst briefing for raw incident detail and recommended actions.",
            )
        )

    sections = [
        {
            "title": "Company-wide KPIs",
            "metrics": [
                _metric_card(
                    "Overall delivery rate",
                    overall_delivery_pct,
                    "delivery_success_rate",
                    detail="Average latest delivery success across all visible regions",
                ),
                _display_metric(
                    "Daily orders",
                    len(recent_shipments),
                    "green",
                    "Recent shipment activity across the operating window",
                    "count",
                ),
                _display_metric(
                    "Active alerts",
                    active_alerts,
                    "red" if critical_regions else "amber" if warning_regions else "green",
                    "Critical and watch-level regions in the current snapshot",
                    "count",
                ),
            ],
        },
        {
            "title": "Region health heatmap",
            "metrics": region_states,
        },
        {
            "title": "Trend summary",
            "metrics": [
                _display_metric(
                    "3-day delivery trend",
                    company_trend["label"] if company_trend else "Insufficient data",
                    "amber" if company_trend and company_trend["is_bad_trend"] else "green",
                    company_trend["message"] if company_trend else "Need 3 snapshots to score trend",
                    "text",
                ),
                _display_metric(
                    "Regions at risk",
                    len(critical_regions),
                    "red" if critical_regions else "green",
                    "Regions in critical status from the latest KPI snapshot",
                    "count",
                ),
            ],
        },
    ]

    return {
        "role": "exec_viewer",
        "role_label": "Executive viewer",
        "badge_label": "executive",
        "assigned_region": None,
        "generated_at": context["reference_time"].isoformat(),
        "auto_refresh_seconds": 60,
        "alerts": alerts,
        "sections": sections,
        "restricted": ROLE_RESTRICTIONS["exec_viewer"],
    }


def _load_dashboard_context(connection) -> dict[str, Any]:
    latest_kpis = [
        {
            "metric_date": row[0],
            "region": row[1],
            "metric_name": row[2],
            "metric_value": float(row[3]),
            "metric_target": float(row[4]),
            "anomaly_flag": bool(row[5]),
            "anomaly_severity": row[6],
            "notes": row[7],
            "data_as_of": row[8],
            "freshness_status": row[9],
            "completeness_pct": float(row[10]),
        }
        for row in connection.execute(
            """
            SELECT
                metric_date,
                region,
                metric_name,
                metric_value,
                metric_target,
                anomaly_flag,
                anomaly_severity,
                notes,
                data_as_of,
                freshness_status,
                completeness_pct
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY region, metric_name
                        ORDER BY metric_date DESC
                    ) AS row_num
                FROM daily_kpis
            )
            WHERE row_num = 1
            ORDER BY region, metric_name
            """
        ).fetchall()
    ]

    kpi_history = [
        {
            "metric_date": row[0],
            "region": row[1],
            "metric_name": row[2],
            "metric_value": float(row[3]),
        }
        for row in connection.execute(
            """
            SELECT metric_date, region, metric_name, metric_value
            FROM daily_kpis
            ORDER BY metric_date ASC, region, metric_name
            """
        ).fetchall()
    ]

    incidents = [
        {
            "incident_id": row[0],
            "incident_date": row[1],
            "region": row[2],
            "incident_type": row[3],
            "severity": row[4],
            "status": row[5],
            "summary": row[6],
        }
        for row in connection.execute(
            """
            SELECT incident_id, incident_date, region, incident_type, severity, status, summary
            FROM incident_log
            ORDER BY incident_date DESC, severity DESC
            """
        ).fetchall()
    ]

    recent_shipments = [
        {
            "event_id": row[0],
            "event_date": row[1],
            "ingestion_time": row[2],
            "region": row[3],
            "shipment_id": row[4],
            "event_type": row[5],
            "failure_reason": row[6],
            "delivery_hours": float(row[7]),
        }
        for row in connection.execute(
            """
            WITH latest_event AS (
                SELECT MAX(event_date) AS latest_event_date FROM shipment_events
            )
            SELECT
                event_id,
                event_date,
                ingestion_time,
                region,
                shipment_id,
                event_type,
                failure_reason,
                delivery_hours
            FROM shipment_events
            WHERE event_date >= (SELECT latest_event_date - INTERVAL 1 DAY FROM latest_event)
            ORDER BY event_date DESC, event_id
            """
        ).fetchall()
    ]

    data_as_of = [row["data_as_of"] for row in latest_kpis if row["data_as_of"] is not None]
    shipment_as_of = [row["ingestion_time"] for row in recent_shipments if row["ingestion_time"] is not None]
    reference_time = max(data_as_of + shipment_as_of)

    return {
        "latest_kpis": latest_kpis,
        "kpi_history": kpi_history,
        "incidents": incidents,
        "recent_shipments": recent_shipments,
        "reference_time": reference_time,
    }


def _pipeline_freshness(context: dict[str, Any]) -> tuple[str, str]:
    statuses = [row["freshness_status"] for row in context["latest_kpis"]]
    if "stale" in statuses:
        return "Stale", "red"
    if "lagging" in statuses:
        return "Lagging", "amber"
    return "Fresh", "green"


def _incident_health(incidents: list[dict[str, Any]], reference_time: datetime) -> tuple[int, int, float]:
    unresolved = [row for row in incidents if row["status"] != "resolved"]
    ages = []
    for item in unresolved:
        opened_at = datetime.combine(item["incident_date"], time.min)
        ages.append((reference_time - opened_at).total_seconds() / 3600)

    over_24h = sum(1 for age in ages if age > 24)
    return len(unresolved), over_24h, round(mean(ages), 1) if ages else 0.0


def _metric_card(
    label: str,
    value: float,
    metric_name: str,
    *,
    unit: str = "pct",
    detail: str,
) -> dict[str, Any]:
    status, status_text = get_status(metric_name, value)
    return {
        "label": label,
        "value": value,
        "display_value": _format_value(value, unit=unit),
        "status": status,
        "status_text": status_text,
        "detail": detail,
    }


def _display_metric(
    label: str,
    value: Any,
    status: str,
    detail: str,
    unit: str,
) -> dict[str, Any]:
    return {
        "label": label,
        "value": value,
        "display_value": _format_value(value, unit=unit),
        "status": status,
        "status_text": {"green": "Normal", "amber": "Watch", "red": "Critical"}.get(status, "Restricted"),
        "detail": detail,
    }


def _format_value(value: Any, *, unit: str) -> str:
    if unit == "pct":
        return f"{float(value):.1f}%"
    if unit == "delta_pct":
        return f"{float(value):+.1f} pts"
    if unit == "hours":
        return f"{float(value):.1f}h"
    if unit == "count":
        return f"{int(value)}"
    if unit == "rank":
        return f"#{int(value)}"
    if unit == "text":
        return str(value)
    return str(value)


def _latest_metric_value(rows: list[dict[str, Any]], metric_name: str) -> float:
    for row in rows:
        if row["metric_name"] == metric_name:
            value = float(row["metric_value"])
            if metric_name in {"delivery_success_rate", "return_rate", "on_time_delivery_rate"}:
                return round(value * 100, 1)
            return value
    return 0.0


def _average_metric(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    values = []
    for row in rows:
        value = float(row["metric_value"])
        if row["metric_name"] in {"delivery_success_rate", "return_rate", "on_time_delivery_rate"}:
            value *= 100
        values.append(value)
    return round(mean(values), 1)


def _average_delivery_hours(shipments: list[dict[str, Any]]) -> float:
    if not shipments:
        return 0.0
    return round(mean(float(row["delivery_hours"]) for row in shipments), 1)


def _trend_summary(
    history: list[dict[str, Any]],
    metric_name: str,
    *,
    region: str | None,
) -> dict[str, Any] | None:
    filtered = [
        row
        for row in history
        if row["metric_name"] == metric_name and (region is None or row["region"] == region)
    ]
    by_date: dict[Any, list[float]] = defaultdict(list)
    for row in filtered:
        value = float(row["metric_value"])
        if metric_name in {"delivery_success_rate", "return_rate", "on_time_delivery_rate"}:
            value *= 100
        by_date[row["metric_date"]].append(value)

    series = sorted((metric_date, mean(values)) for metric_date, values in by_date.items())
    if len(series) < 3:
        return None

    last_three = series[-3:]
    values = [round(item[1], 1) for item in last_three]
    is_bad_trend = False
    if metric_name in {"delivery_success_rate", "on_time_delivery_rate"}:
        is_bad_trend = values[0] > values[1] > values[2]
    else:
        is_bad_trend = values[0] < values[1] < values[2]

    if not is_bad_trend:
        return {
            "label": "Stable",
            "is_bad_trend": False,
            "message": f"Recent values: {' → '.join(f'{value:.1f}' for value in values)}",
        }

    direction = "declined" if metric_name in {"delivery_success_rate", "on_time_delivery_rate"} else "increased"
    return {
        "label": "Declining" if direction == "declined" else "Rising",
        "is_bad_trend": True,
        "message": f"{metric_name.replace('_', ' ')} {direction} for 3 consecutive days ({' → '.join(f'{value:.1f}' for value in values)}).",
    }


def _regional_rank(rows: list[dict[str, Any]], region: str) -> int:
    ranking = sorted(
        ((_latest_metric_value([row], row["metric_name"]), row["region"]) for row in rows),
        reverse=True,
    )
    for index, (_, row_region) in enumerate(ranking, start=1):
        if row_region == region:
            return index
    return len(ranking) or 1


def _region_card(row: dict[str, Any]) -> dict[str, Any]:
    value = _latest_metric_value([row], row["metric_name"])
    status, status_text = get_status("delivery_success_rate", value)
    return {
        "label": row["region"],
        "value": value,
        "display_value": f"{value:.1f}%",
        "status": status,
        "status_text": status_text,
        "detail": row["notes"] or "Latest delivery success rate snapshot",
    }


def _region_health(latest_kpis: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in latest_kpis:
        grouped[row["region"]].append(row)

    status_rank = {"green": 0, "amber": 1, "red": 2}
    heatmap = []
    for region, rows in sorted(grouped.items()):
        scored_rows = []
        for row in rows:
            metric_name = row["metric_name"]
            score_value = _latest_metric_value([row], metric_name)
            status, _ = get_status(
                "sla_compliance" if metric_name == "on_time_delivery_rate" else metric_name,
                score_value,
            )
            scored_rows.append((status_rank[status], status, metric_name, score_value))
        _, status, metric_name, score_value = max(scored_rows)
        label = "Healthy" if status == "green" else "Watch" if status == "amber" else "Critical"
        heatmap.append(
            {
                "label": region,
                "value": label,
                "display_value": label,
                "status": status,
                "status_text": label,
                "detail": f"{metric_name.replace('_', ' ')} at {score_value:.1f}{'%' if metric_name != 'avg_delivery_hours' else 'h'}",
            }
        )
    return heatmap


def _build_ops_alerts(context: dict[str, Any]) -> list[dict[str, Any]]:
    alerts = []
    latest_kpis = context["latest_kpis"]
    for row in latest_kpis:
        if row["metric_name"] != "delivery_success_rate":
            continue
        score = _latest_metric_value([row], "delivery_success_rate")
        status, _ = get_status("delivery_success_rate", score)
        if status == "red":
            alerts.append(
                _alert(
                    "red",
                    "Delivery threshold breached",
                    f"{row['region']} delivery success rate dropped to {score:.1f}%.",
                    "Check the delivery disruption runbook and review carrier + weather evidence.",
                )
            )

    unresolved_count, over_24h_count, _ = _incident_health(
        context["incidents"], context["reference_time"]
    )
    if over_24h_count:
        alerts.append(
            _alert(
                "red",
                "Long-running incidents",
                f"{over_24h_count} unresolved incident(s) have been open for more than 24 hours.",
                "Escalate through the incident runbook and analyst review path.",
            )
        )

    recent_shipments = context["recent_shipments"]
    avg_delivery_hours = _average_delivery_hours(recent_shipments)
    avg_delivery_status, _ = get_status("avg_delivery_hours", avg_delivery_hours)
    if avg_delivery_status in {"amber", "red"}:
        alerts.append(
            _alert(
                avg_delivery_status,
                "Delivery times elevated",
                f"Average delivery time is {avg_delivery_hours:.1f}h in the latest shipment window.",
                "Investigate backlog, route congestion, and carrier handoff failures.",
            )
        )

    trend = _trend_summary(context["kpi_history"], "delivery_success_rate", region=None)
    if trend and trend["is_bad_trend"]:
        alerts.append(
            _alert(
                "amber",
                "Delivery trend deteriorating",
                trend["message"],
                "Investigate root cause before the next operating cycle.",
            )
        )

    return alerts


def _alert(level: str, title: str, message: str, recommendation: str) -> dict[str, str]:
    return {
        "level": level,
        "title": title,
        "message": message,
        "recommendation": recommendation,
    }


def _alert_for_metric(region: str, metric: dict[str, Any], *, runbook: bool) -> list[dict[str, str]]:
    if metric["status"] != "red":
        return []
    recommendation = "Check the relevant runbook immediately." if runbook else "Investigate immediately."
    return [
        _alert(
            "red",
            f"{metric['label']} critical",
            f"{region} {metric['label'].lower()} is currently {metric['display_value']}.",
            recommendation,
        )
    ]
