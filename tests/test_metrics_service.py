from app.services.metrics_service import get_dashboard_for_role


def test_ops_dashboard_includes_role_scoped_sections() -> None:
    payload = get_dashboard_for_role("operations_analyst")

    assert payload["role"] == "operations_analyst"
    section_titles = [section["title"] for section in payload["sections"]]
    assert "Real-time operations" in section_titles
    assert "Shipment events (last 24h)" in section_titles
    assert payload["restricted"]


def test_regional_manager_dashboard_is_scoped_to_default_region() -> None:
    payload = get_dashboard_for_role("regional_manager")

    assert payload["role"] == "regional_manager"
    assert payload["assigned_region"] == "Region 3"
    assert any("Region 3" in section["title"] for section in payload["sections"])
    assert any("raw shipment logs" in item.lower() for item in payload["restricted"])


def test_exec_dashboard_hides_operational_detail_sections() -> None:
    payload = get_dashboard_for_role("exec_viewer")

    assert payload["role"] == "exec_viewer"
    section_titles = [section["title"] for section in payload["sections"]]
    assert "Company-wide KPIs" in section_titles
    assert "Region health heatmap" in section_titles
    assert "Incident details" not in section_titles
    assert any("runbooks" in item.lower() for item in payload["restricted"])
