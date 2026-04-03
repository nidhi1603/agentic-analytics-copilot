from app.orchestration.router import classify_route, extract_metric_name, extract_region


def test_classify_route_for_hybrid_question() -> None:
    route = classify_route(
        "Why did delivery success rate drop in Region 3 and what does the SOP suggest?"
    )

    assert route == "hybrid"


def test_extract_region_returns_expected_region() -> None:
    region = extract_region("Show anomalies for Region 4 this week")

    assert region == "Region 4"


def test_extract_metric_name_maps_human_phrase() -> None:
    metric_name = extract_metric_name("Explain the return rate spike")

    assert metric_name == "return_rate"

