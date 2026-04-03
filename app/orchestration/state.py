from typing import Literal, TypedDict

from app.schemas.tools import (
    IncidentRecord,
    KPIRecord,
    MetricDefinitionRecord,
    RetrievedDocument,
    ShipmentFailureBreakdown,
)
from app.schemas.answer import SynthesizedAnswer
from app.schemas.ask import Citation


RouteType = Literal["structured_only", "documents_only", "hybrid"]


class WorkflowState(TypedDict, total=False):
    question: str
    route: RouteType
    region: str | None
    metric_name: str | None
    requires_structured: bool
    requires_documents: bool
    kpi_summary: list[KPIRecord]
    anomaly_report: list[KPIRecord]
    incidents: list[IncidentRecord]
    failure_breakdown: list[ShipmentFailureBreakdown]
    metric_definition: MetricDefinitionRecord | None
    documents: list[RetrievedDocument]
    trace: list[str]
    evidence_summary: str
    synthesized_answer: SynthesizedAnswer
    citations: list[Citation]
