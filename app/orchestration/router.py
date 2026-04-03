from app.orchestration.state import RouteType


KNOWN_REGIONS = ["Region 1", "Region 2", "Region 3", "Region 4", "Region 5"]
KNOWN_METRICS = [
    "delivery_success_rate",
    "on_time_delivery_rate",
    "return_rate",
]


def classify_route(question: str) -> RouteType:
    normalized = question.lower()
    structured_keywords = [
        "kpi",
        "metric",
        "drop",
        "rate",
        "trend",
        "sql",
        "anomaly",
        "incident",
        "region",
    ]
    document_keywords = [
        "sop",
        "runbook",
        "policy",
        "definition",
        "what does",
        "how should",
        "escalate",
    ]

    has_structured_intent = any(keyword in normalized for keyword in structured_keywords)
    has_document_intent = any(keyword in normalized for keyword in document_keywords)

    if has_structured_intent and has_document_intent:
        return "hybrid"
    if has_structured_intent:
        return "structured_only"
    if has_document_intent:
        return "documents_only"
    return "hybrid"


def extract_region(question: str) -> str | None:
    normalized = question.lower()
    for region in KNOWN_REGIONS:
        if region.lower() in normalized:
            return region
    return None


def extract_metric_name(question: str) -> str | None:
    normalized = question.lower()
    for metric in KNOWN_METRICS:
        if metric in normalized:
            return metric

    phrase_map = {
        "delivery success rate": "delivery_success_rate",
        "on time delivery rate": "on_time_delivery_rate",
        "return rate": "return_rate",
    }
    for phrase, metric in phrase_map.items():
        if phrase in normalized:
            return metric

    return None

