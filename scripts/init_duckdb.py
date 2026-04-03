from build_curated_data import build_curated_data
from run_data_quality_checks import run_quality_checks

from app.db.bootstrap import initialize_database


if __name__ == "__main__":
    build_curated_data()
    run_quality_checks()
    initialize_database()
    print("DuckDB database initialized with curated seed data rebuilt from raw feeds.")
