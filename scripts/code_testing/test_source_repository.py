"""
File: test_source_repository.py

Purpose:
    Verifies authenticated Source lookup through SourceRepository.

Tests:
    1. Existing OneNote Source resolves to its AlphaOmega source_id.
    2. Existing OneDrive Source resolves to its AlphaOmega source_id.
    3. Unknown Source returns None.
"""

from common.security.local_credential_provider import LocalCredentialProvider
from scripts.database.database_connection import DatabaseConnection
from scripts.database.source_repository import SourceRepository


def main():
    print("Testing Source Repository...")

    credential_provider = LocalCredentialProvider()

    database_connection = DatabaseConnection(
        credential_provider
    )

    client = database_connection.connect()

    repository = SourceRepository(
        client
    )

    print("Authenticated repository access established.")

    # ---------------------------------------------------------
    # Test 1: OneNote
    # ---------------------------------------------------------

    onenote_source_id = repository.find_id_by_name(
        "OneNote"
    )

    if onenote_source_id is None:
        raise RuntimeError(
            "Expected OneNote Source was not found."
        )

    print(
        f"OneNote resolved to source_id: "
        f"{onenote_source_id}"
    )

    # ---------------------------------------------------------
    # Test 2: OneDrive
    # ---------------------------------------------------------

    onedrive_source_id = repository.find_id_by_name(
        "OneDrive"
    )

    if onedrive_source_id is None:
        raise RuntimeError(
            "Expected OneDrive Source was not found."
        )

    print(
        f"OneDrive resolved to source_id: "
        f"{onedrive_source_id}"
    )

    if onenote_source_id == onedrive_source_id:
        raise RuntimeError(
            "OneNote and OneDrive unexpectedly resolved "
            "to the same source_id."
        )

    # ---------------------------------------------------------
    # Test 3: Missing Source
    # ---------------------------------------------------------

    missing_source_id = repository.find_id_by_name(
        "AlphaOmega-Source-That-Does-Not-Exist"
    )

    if missing_source_id is not None:
        raise RuntimeError(
            "Repository returned an unexpected Source."
        )

    print("Nonexistent Source correctly returned None.")

    print("Source Repository test PASSED.")


if __name__ == "__main__":
    main()