import json
from pathlib import Path

from app.orchestration.router import classify_route


def test_eval_dataset_routes_are_consistent() -> None:
    dataset_path = (
        Path(__file__).resolve().parents[1]
        / "evals"
        / "datasets"
        / "eval_questions.json"
    )
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))

    for case in cases:
        assert classify_route(case["question"]) == case["expected_route"]

