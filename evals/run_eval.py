import json
from pathlib import Path

from app.core.logging import configure_logging
from app.services.workflow_service import run_question_workflow


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "evals" / "datasets" / "eval_questions.json"


def load_eval_cases() -> list[dict]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def evaluate_case(case: dict) -> dict:
    response = run_question_workflow(case["question"], case["role"])

    route_in_trace = next(
        (item for item in response.trace if item.startswith("classify_request:")),
        "",
    )

    checks = {
        "citation_present": (len(response.citations) > 0)
        if case["expected_needs_citation"]
        else True,
        "trace_depth_ok": len(response.trace) >= case["expected_min_trace_steps"],
        "region_detected": (
            case["expected_region"] in route_in_trace
            if case["expected_region"] is not None
            else True
        ),
        "metric_detected": (
            case["expected_metric"] in route_in_trace
            if case["expected_metric"] is not None
            else True
        ),
        "route_detected": case["expected_route"] in route_in_trace,
        "answer_present": len(response.answer.strip()) > 0,
        "freshness_detected": response.freshness_status == case["expected_freshness_status"],
        "blocked_sources_expected": len(response.blocked_sources) >= case["expected_min_blocked_sources"],
    }

    passed = sum(1 for value in checks.values() if value)
    total = len(checks)

    return {
        "question": case["question"],
        "checks": checks,
        "score": round(passed / total, 2),
        "confidence": response.confidence,
        "needs_analyst_review": response.needs_analyst_review,
        "role": response.role,
        "blocked_sources": response.blocked_sources,
    }


def main() -> None:
    configure_logging()
    results = [evaluate_case(case) for case in load_eval_cases()]
    average_score = round(sum(item["score"] for item in results) / len(results), 2)

    print("Evaluation Summary")
    print("==================")
    print(f"Cases: {len(results)}")
    print(f"Average score: {average_score}")
    print("")

    for result in results:
        print(f"Question: {result['question']}")
        print(f"Score: {result['score']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Needs analyst review: {result['needs_analyst_review']}")
        print(f"Checks: {result['checks']}")
        print("")


if __name__ == "__main__":
    main()
