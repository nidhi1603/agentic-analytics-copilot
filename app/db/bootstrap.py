from pathlib import Path

from app.db.duckdb_client import get_connection


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "data" / "structured" / "source"


CREATE_TABLE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS daily_kpis (
        metric_date DATE,
        region VARCHAR,
        metric_name VARCHAR,
        metric_value DOUBLE,
        metric_target DOUBLE,
        anomaly_flag BOOLEAN,
        anomaly_severity VARCHAR,
        notes VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS shipment_events (
        event_id BIGINT,
        event_date DATE,
        region VARCHAR,
        shipment_id VARCHAR,
        event_type VARCHAR,
        failure_reason VARCHAR,
        delivery_hours DOUBLE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS incident_log (
        incident_id VARCHAR,
        incident_date DATE,
        region VARCHAR,
        incident_type VARCHAR,
        severity VARCHAR,
        status VARCHAR,
        summary VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metric_definitions (
        metric_name VARCHAR,
        metric_owner VARCHAR,
        metric_grain VARCHAR,
        metric_definition VARCHAR,
        investigation_hint VARCHAR
    )
    """,
]


def initialize_database() -> None:
    connection = get_connection()
    try:
        for statement in CREATE_TABLE_STATEMENTS:
            connection.execute(statement)

        _load_csv_into_table(connection, "daily_kpis")
        _load_csv_into_table(connection, "shipment_events")
        _load_csv_into_table(connection, "incident_log")
        _load_csv_into_table(connection, "metric_definitions")
    finally:
        connection.close()


def _load_csv_into_table(connection, table_name: str) -> None:
    csv_path = SOURCE_DIR / f"{table_name}.csv"
    connection.execute(f"DELETE FROM {table_name}")
    connection.execute(
        f"""
        INSERT INTO {table_name}
        SELECT *
        FROM read_csv_auto(?, HEADER = TRUE)
        """,
        [str(csv_path)],
    )

