from pathlib import Path

import duckdb

from app.core.config import get_settings


def get_duckdb_path() -> Path:
    return Path(get_settings().duckdb_path)


def get_connection() -> duckdb.DuckDBPyConnection:
    db_path = get_duckdb_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))

