"""
Authenticated Database Connection Test

Verifies that AlphaOmega can:

1. Retrieve its service identity credential through the Credential Provider.
2. Authenticate with Supabase.
3. Establish an authenticated database client.
4. SELECT from knowledge_objects through the configured RLS policy.

No credentials or authentication tokens are displayed.
"""

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)

from scripts.database.database_connection import (
    DatabaseConnection,
)


def main():
    """Run the authenticated database connection test."""

    print("Testing authenticated AlphaOmega database connection...")

    credential_provider = LocalCredentialProvider()

    database_connection = DatabaseConnection(
        credential_provider=credential_provider
    )

    try:
        client = database_connection.connect()

        print("Supabase authentication succeeded.")

        response = (
            client.table("knowledge_objects")
            .select("id")
            .limit(1)
            .execute()
        )

        if response.data is None:
            raise RuntimeError(
                "knowledge_objects SELECT returned no response data."
            )

        print("knowledge_objects SELECT succeeded.")
        print("Database connection test succeeded.")

    except Exception as error:
        print(
            f"Database connection test failed: "
            f"{error.__class__.__name__}: {error}"
        )
        raise


if __name__ == "__main__":
    main()