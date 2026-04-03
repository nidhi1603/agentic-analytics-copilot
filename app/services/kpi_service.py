from app.db.duckdb_client import get_connection
from app.schemas.tools import KPIRecord


def get_kpi_summary(
    region: str | None = None,
    metric_name: str | None = None,
    limit: int = 10,
) -> list[KPIRecord]:
    connection = get_connection()
    try:
        query = """
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
            FROM daily_kpis
            WHERE (? IS NULL OR region = ?)
              AND (? IS NULL OR metric_name = ?)
            ORDER BY metric_date DESC, region, metric_name
            LIMIT ?
        """
        rows = connection.execute(
            query,
            [region, region, metric_name, metric_name, limit],
        ).fetchall()
    finally:
        connection.close()

    return [
        KPIRecord(
            metric_date=str(row[0]),
            region=row[1],
            metric_name=row[2],
            metric_value=row[3],
            metric_target=row[4],
            anomaly_flag=row[5],
            anomaly_severity=row[6],
            notes=row[7],
            data_as_of=str(row[8]),
            freshness_status=row[9],
            completeness_pct=row[10],
        )
        for row in rows
    ]


def get_anomaly_report(
    region: str | None = None,
    metric_name: str | None = None,
) -> list[KPIRecord]:
    connection = get_connection()
    try:
        query = """
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
            FROM daily_kpis
            WHERE anomaly_flag = TRUE
              AND (? IS NULL OR region = ?)
              AND (? IS NULL OR metric_name = ?)
            ORDER BY metric_date DESC, anomaly_severity DESC
        """
        rows = connection.execute(
            query,
            [region, region, metric_name, metric_name],
        ).fetchall()
    finally:
        connection.close()

    return [
        KPIRecord(
            metric_date=str(row[0]),
            region=row[1],
            metric_name=row[2],
            metric_value=row[3],
            metric_target=row[4],
            anomaly_flag=row[5],
            anomaly_severity=row[6],
            notes=row[7],
            data_as_of=str(row[8]),
            freshness_status=row[9],
            completeness_pct=row[10],
        )
        for row in rows
    ]
