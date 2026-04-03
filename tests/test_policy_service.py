from app.services.policy_service import get_policies_for_role, is_resource_allowed


def test_get_policies_for_role_maps_rows(monkeypatch) -> None:
    def fake_get_connection():
        class FakeConnection:
            def execute(self, *_args, **_kwargs):
                class FakeCursor:
                    @staticmethod
                    def fetchall():
                        return [
                            (
                                "operations_analyst",
                                "structured",
                                "shipment_events",
                                "allow",
                                "default_access",
                            )
                        ]

                return FakeCursor()

            @staticmethod
            def close():
                return None

        return FakeConnection()

    monkeypatch.setattr("app.services.policy_service.get_connection", fake_get_connection)

    result = get_policies_for_role("operations_analyst")

    assert len(result) == 1
    assert result[0].resource_name == "shipment_events"


def test_is_resource_allowed_returns_restriction_reason(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.policy_service.get_policies_for_role",
        lambda _role: [
            type(
                "Policy",
                (),
                {
                    "resource_type": "document",
                    "resource_name": "incident_notes",
                    "permission": "deny",
                    "restriction_reason": "incident_review_notes_are_analyst_only",
                },
            )()
        ],
    )

    allowed, reason = is_resource_allowed("exec_viewer", "document", "incident_notes")

    assert allowed is False
    assert reason == "incident_review_notes_are_analyst_only"
