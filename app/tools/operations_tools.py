from app.schemas.tools import (
    IncidentRecord,
    KPIRecord,
    MetricDefinitionRecord,
    RetrievedDocument,
    ShipmentFailureBreakdown,
)
from app.services.incident_service import get_failure_breakdown, get_incidents
from app.services.kpi_service import get_anomaly_report, get_kpi_summary
from app.services.metric_service import get_metric_definition
from app.services.retrieval_service import retrieve_documents


def tool_get_kpi_summary(
    region: str | None = None,
    metric_name: str | None = None,
    limit: int = 10,
) -> list[KPIRecord]:
    return get_kpi_summary(region=region, metric_name=metric_name, limit=limit)


def tool_get_anomaly_report(
    region: str | None = None,
    metric_name: str | None = None,
) -> list[KPIRecord]:
    return get_anomaly_report(region=region, metric_name=metric_name)


def tool_get_incidents(region: str | None = None, limit: int = 10) -> list[IncidentRecord]:
    return get_incidents(region=region, limit=limit)


def tool_get_failure_breakdown(region: str | None = None) -> list[ShipmentFailureBreakdown]:
    return get_failure_breakdown(region=region)


def tool_get_metric_definition(metric_name: str) -> MetricDefinitionRecord | None:
    return get_metric_definition(metric_name=metric_name)


def tool_retrieve_documents(query_text: str, limit: int = 4) -> list[RetrievedDocument]:
    return retrieve_documents(query_text=query_text, limit=limit)

