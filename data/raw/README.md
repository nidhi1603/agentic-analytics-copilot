# Raw Data Layer

This folder simulates bronze/raw operational feeds before cleaning and modeling.

The records here intentionally include:

- duplicate rows
- inconsistent region names
- inconsistent metric names
- mixed boolean encodings
- delayed extraction timestamps

Use `python scripts/build_curated_data.py` to transform these raw feeds into the
curated CSVs under `data/structured/source/`.

