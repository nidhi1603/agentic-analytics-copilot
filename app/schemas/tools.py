from pydantic import BaseModel


class KPIRecord(BaseModel):
    metric_date: str
    region: str
    metric_name: str
    metric_value: float
    metric_target: float
    anomaly_flag: bool
    anomaly_severity: str
    notes: str
    data_as_of: str
    freshness_status: str
    completeness_pct: float


class ShipmentFailureBreakdown(BaseModel):
    failure_reason: str
    event_count: int


class IncidentRecord(BaseModel):
    incident_id: str
    incident_date: str
    region: str
    incident_type: str
    severity: str
    status: str
    summary: str
    source_team: str


class MetricDefinitionRecord(BaseModel):
    metric_name: str
    metric_owner: str
    metric_grain: str
    metric_definition: str
    investigation_hint: str
    definition_quality: str


class RetrievedDocument(BaseModel):
    content: str
    source_path: str
    title: str
    doc_group: str
    distance: float | None = None


class AccessPolicyRecord(BaseModel):
    role: str
    resource_type: str
    resource_name: str
    permission: str
    restriction_reason: str
