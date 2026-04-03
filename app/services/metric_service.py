from app.db.duckdb_client import get_connection
from app.schemas.tools import MetricDefinitionRecord


def get_metric_definition(metric_name: str) -> MetricDefinitionRecord | None:
    connection = get_connection()
    try:
        query = """
            SELECT
                metric_name,
                metric_owner,
                metric_grain,
                metric_definition,
                investigation_hint
            FROM metric_definitions
            WHERE metric_name = ?
            LIMIT 1
        """
        row = connection.execute(query, [metric_name]).fetchone()
    finally:
        connection.close()

    if row is None:
        return None

    return MetricDefinitionRecord(
        metric_name=row[0],
        metric_owner=row[1],
        metric_grain=row[2],
        metric_definition=row[3],
        investigation_hint=row[4],
    )

