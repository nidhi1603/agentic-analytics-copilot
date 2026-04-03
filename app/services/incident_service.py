from app.db.duckdb_client import get_connection
from app.schemas.tools import IncidentRecord, ShipmentFailureBreakdown


def get_incidents(region: str | None = None, limit: int = 10) -> list[IncidentRecord]:
    connection = get_connection()
    try:
        query = """
            SELECT
                incident_id,
                incident_date,
                region,
                incident_type,
                severity,
                status,
                summary,
                source_team
            FROM incident_log
            WHERE (? IS NULL OR region = ?)
            ORDER BY incident_date DESC, severity DESC
            LIMIT ?
        """
        rows = connection.execute(query, [region, region, limit]).fetchall()
    finally:
        connection.close()

    return [
        IncidentRecord(
            incident_id=row[0],
            incident_date=str(row[1]),
            region=row[2],
            incident_type=row[3],
            severity=row[4],
            status=row[5],
            summary=row[6],
            source_team=row[7],
        )
        for row in rows
    ]


def get_failure_breakdown(region: str | None = None) -> list[ShipmentFailureBreakdown]:
    connection = get_connection()
    try:
        query = """
            SELECT
                COALESCE(failure_reason, 'unknown') AS failure_reason,
                COUNT(*) AS event_count
            FROM shipment_events
            WHERE event_type IN ('delivery_failed', 'delivery_delayed')
              AND (? IS NULL OR region = ?)
            GROUP BY 1
            ORDER BY event_count DESC, failure_reason
        """
        rows = connection.execute(query, [region, region]).fetchall()
    finally:
        connection.close()

    return [
        ShipmentFailureBreakdown(
            failure_reason=row[0],
            event_count=row[1],
        )
        for row in rows
    ]
