from app.db.bootstrap import initialize_database


if __name__ == "__main__":
    initialize_database()
    print("DuckDB database initialized with seed data.")

