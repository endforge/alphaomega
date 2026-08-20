"""
Credential Provider Test

Verifies that AlphaOmega can retrieve the Supabase service identity
credential through the Credential Provider abstraction.

The credential value is never displayed.
"""

from common.security.local_credential_provider import (
    LocalCredentialProvider,
)


def main():
    """Run the Credential Provider test."""

    print("Testing AlphaOmega Credential Provider...")

    provider = LocalCredentialProvider()

    try:
        credential = provider.get(
            "supabase.alphaomega"
        )

        if not credential:
            raise RuntimeError(
                "Credential Provider returned an empty credential."
            )

        print(
            "Credential Provider test succeeded."
        )

    except Exception as error:
        print(
            f"Credential Provider test failed: "
            f"{error.__class__.__name__}: {error}"
        )
        raise


if __name__ == "__main__":
    main()