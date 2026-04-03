from app.schemas.tools import MetricDefinitionRecord
from app.services.metric_service import get_metric_definition


def test_metric_definition_returns_none_for_unknown_metric(monkeypatch) -> None:
    def fake_get_connection():
        class FakeConnection:
            def execute(self, *_args, **_kwargs):
                class FakeCursor:
                    @staticmethod
                    def fetchone():
                        return None

                return FakeCursor()

            @staticmethod
            def close():
                return None

        return FakeConnection()

    monkeypatch.setattr("app.services.metric_service.get_connection", fake_get_connection)

    result = get_metric_definition("unknown_metric")

    assert result is None


def test_metric_definition_maps_expected_fields(monkeypatch) -> None:
    def fake_get_connection():
        class FakeConnection:
            def execute(self, *_args, **_kwargs):
                class FakeCursor:
                    @staticmethod
                    def fetchone():
                        return (
                            "delivery_success_rate",
                            "Operations Analytics",
                            "region-day",
                            "Delivered shipments divided by attempted shipments",
                            "Check failed deliveries first",
                            "verified",
                        )

                return FakeCursor()

            @staticmethod
            def close():
                return None

        return FakeConnection()

    monkeypatch.setattr("app.services.metric_service.get_connection", fake_get_connection)

    result = get_metric_definition("delivery_success_rate")

    assert isinstance(result, MetricDefinitionRecord)
    assert result.metric_owner == "Operations Analytics"
    assert result.definition_quality == "verified"
