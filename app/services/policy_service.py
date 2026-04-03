from app.db.duckdb_client import get_connection
from app.schemas.tools import AccessPolicyRecord


def get_policies_for_role(role: str) -> list[AccessPolicyRecord]:
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT
                role,
                resource_type,
                resource_name,
                permission,
                restriction_reason
            FROM access_policies
            WHERE role = ?
            """,
            [role],
        ).fetchall()
    finally:
        connection.close()

    return [
        AccessPolicyRecord(
            role=row[0],
            resource_type=row[1],
            resource_name=row[2],
            permission=row[3],
            restriction_reason=row[4],
        )
        for row in rows
    ]


def is_resource_allowed(role: str, resource_type: str, resource_name: str) -> tuple[bool, str | None]:
    policies = get_policies_for_role(role)
    for policy in policies:
        if (
            policy.resource_type == resource_type
            and policy.resource_name == resource_name
        ):
            return policy.permission == "allow", None if policy.permission == "allow" else policy.restriction_reason
    return False, "no_matching_policy"
