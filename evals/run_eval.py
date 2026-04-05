import json
import os
from collections import defaultdict
from pathlib import Path

from app.core.logging import configure_logging
from evals.llm_judge import judge_answer
from app.services.workflow_service import run_question_workflow


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "evals" / "datasets" / "eval_questions.json"


def load_eval_cases() -> list[dict]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def infer_doc_group_from_path(source_path: str) -> str | None:
    normalized = source_path.replace("\\", "/")
    for group in ["policies", "runbooks", "sops", "incident_notes", "metric_definitions"]:
        if f"/{group}/" in normalized:
            return group
    return None


def compute_retrieval_metrics(case: dict, response) -> dict[str, float | bool | None]:
    gold_doc_groups = case.get("gold_doc_groups", [])
    if not gold_doc_groups:
        return {
            "precision_at_5": None,
            "recall": None,
            "retrieval_precision_ok": True,
            "retrieval_recall_ok": True,
        }

    retrieved_doc_groups = [
        infer_doc_group_from_path(citation.source_path)
        for citation in response.citations
        if citation.source_type == "document"
    ]
    retrieved_doc_groups = [group for group in retrieved_doc_groups if group is not None]

    if not retrieved_doc_groups:
        return {
            "precision_at_5": 0.0,
            "recall": 0.0,
            "retrieval_precision_ok": False,
            "retrieval_recall_ok": False,
        }

    relevant_retrieved = sum(1 for group in retrieved_doc_groups if group in gold_doc_groups)
    precision_at_5 = round(relevant_retrieved / min(5, len(retrieved_doc_groups)), 2)
    recall = 1.0 if any(group in gold_doc_groups for group in retrieved_doc_groups) else 0.0

    return {
        "precision_at_5": precision_at_5,
        "recall": recall,
        "retrieval_precision_ok": precision_at_5 >= 0.5,
        "retrieval_recall_ok": recall >= 1.0,
    }


def evaluate_case(case: dict) -> dict:
    response = run_question_workflow(case["question"], case["role"])
    retrieved_evidence = "\n".join(
        [
            response.evidence_summary,
            *[citation.snippet for citation in response.citations],
        ]
    )

    route_in_trace = next(
        (item for item in response.trace if item.startswith("classify_request:")),
        "",
    )

    retrieval_metrics = compute_retrieval_metrics(case, response)
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
        "retrieval_precision_ok": retrieval_metrics["retrieval_precision_ok"],
        "retrieval_recall_ok": retrieval_metrics["retrieval_recall_ok"],
    }

    passed = sum(1 for value in checks.values() if value)
    total = len(checks)

    return {
        "question": case["question"],
        "scenario_tags": case.get("scenario_tags", []),
        "checks": checks,
        "score": round(passed / total, 2),
        "confidence": response.confidence,
        "needs_analyst_review": response.needs_analyst_review,
        "role": response.role,
        "blocked_sources": response.blocked_sources,
        "retrieval_metrics": retrieval_metrics,
        "llm_judge": judge_answer(case["question"], retrieved_evidence, response.answer),
    }


def summarize_results(results: list[dict]) -> dict:
    if not results:
        return {
            "aggregate_checks": {},
            "confidence_distribution": {},
            "scenario_summary": {},
            "avg_precision_at_5": None,
            "avg_recall": None,
        }

    check_names = list(results[0]["checks"].keys())
    aggregate_checks = {
        name: round(
            sum(1 for result in results if result["checks"][name]) / len(results),
            2,
        )
        for name in check_names
    }

    confidence_distribution: dict[str, int] = defaultdict(int)
    for result in results:
        confidence_distribution[result["confidence"]] += 1

    tagged_scores: dict[str, list[float]] = defaultdict(list)
    for result in results:
        for tag in result.get("scenario_tags", []):
            tagged_scores[tag].append(result["score"])

    scenario_summary = {
        tag: {
            "cases": len(scores),
            "avg_score": round(sum(scores) / len(scores), 2),
        }
        for tag, scores in sorted(tagged_scores.items())
    }

    retrieval_precisions = [
        result["retrieval_metrics"]["precision_at_5"]
        for result in results
        if result["retrieval_metrics"]["precision_at_5"] is not None
    ]
    retrieval_recalls = [
        result["retrieval_metrics"]["recall"]
        for result in results
        if result["retrieval_metrics"]["recall"] is not None
    ]

    return {
        "aggregate_checks": aggregate_checks,
        "confidence_distribution": dict(confidence_distribution),
        "scenario_summary": scenario_summary,
        "avg_precision_at_5": round(sum(retrieval_precisions) / len(retrieval_precisions), 2)
        if retrieval_precisions
        else None,
        "avg_recall": round(sum(retrieval_recalls) / len(retrieval_recalls), 2)
        if retrieval_recalls
        else None,
    }


def main() -> None:
    configure_logging()
    results = [evaluate_case(case) for case in load_eval_cases()]
    average_score = round(sum(item["score"] for item in results) / len(results), 2)
    summary = summarize_results(results)
    threshold_raw = os.getenv("EVAL_MIN_AVG_SCORE")
    threshold = float(threshold_raw) if threshold_raw else None

    print("Evaluation Summary")
    print("==================")
    print(f"Cases: {len(results)}")
    print(f"Average score: {average_score}")
    if summary["avg_precision_at_5"] is not None:
        print(f"Average precision@5: {summary['avg_precision_at_5']}")
    if summary["avg_recall"] is not None:
        print(f"Average recall: {summary['avg_recall']}")
    print(f"Confidence distribution: {summary['confidence_distribution']}")
    if threshold is not None:
        print(f"Required minimum score: {threshold}")
    print("")

    print("Aggregate Check Pass Rates")
    print("--------------------------")
    for name, rate in summary["aggregate_checks"].items():
        print(f"{name}: {rate}")
    print("")

    print("Scenario Summary")
    print("----------------")
    for tag, values in summary["scenario_summary"].items():
        print(f"{tag}: cases={values['cases']}, avg_score={values['avg_score']}")
    print("")

    for result in results:
        print(f"Question: {result['question']}")
        print(f"Score: {result['score']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Needs analyst review: {result['needs_analyst_review']}")
        if result["scenario_tags"]:
            print(f"Scenario tags: {result['scenario_tags']}")
        print(f"Retrieval metrics: {result['retrieval_metrics']}")
        print(f"LLM judge: {result['llm_judge']}")
        print(f"Checks: {result['checks']}")
        print("")

    if threshold is not None and average_score < threshold:
        raise SystemExit(
            f"Average eval score {average_score} is below required threshold {threshold}."
        )


if __name__ == "__main__":
    main()
