"""
File: test_graph_content_retrievers.py

Purpose:
    Verify Microsoft Graph content retrievers without making
    live Microsoft Graph requests.
"""

from unittest.mock import Mock, patch

from scripts.connectors.ms_graph.onedrive_content_retriever import (
    OneDriveContentRetriever,
)
from scripts.connectors.ms_graph.onenote_content_retriever import (
    OneNoteContentRetriever,
)


def test_onedrive_retrieval():
    """
    Verify OneDrive retrieval uses the expected Graph endpoint
    and returns raw response bytes.
    """

    retriever = OneDriveContentRetriever()

    mock_response = Mock()
    mock_response.content = b"OneDrive test content"

    with patch(
        "scripts.connectors.ms_graph."
        "onedrive_content_retriever.graph_get",
        return_value=mock_response,
    ) as mock_graph_get:

        result = retriever.retrieve(
            "drive-item-123"
        )

    assert result == b"OneDrive test content"

    mock_graph_get.assert_called_once_with(
        "/me/drive/items/drive-item-123/content"
    )

    print(
        "PASS: OneDrive content retrieval routed correctly."
    )


def test_onedrive_missing_id():
    """
    Verify OneDrive retrieval rejects a missing object ID.
    """

    retriever = OneDriveContentRetriever()

    try:
        retriever.retrieve(None)

        raise AssertionError(
            "Missing OneDrive object ID was accepted."
        )

    except ValueError:
        pass

    print(
        "PASS: OneDrive missing object ID rejected."
    )


def test_onenote_retrieval():
    """
    Verify OneNote page retrieval uses the expected Graph endpoint
    and returns raw response bytes.
    """

    retriever = OneNoteContentRetriever()

    mock_response = Mock()
    mock_response.content = b"<html>OneNote test</html>"

    with patch(
        "scripts.connectors.ms_graph."
        "onenote_content_retriever.graph_get",
        return_value=mock_response,
    ) as mock_graph_get:

        result = retriever.retrieve(
            source_object_id="page-456",
            object_type="page",
        )

    assert result == b"<html>OneNote test</html>"

    mock_graph_get.assert_called_once_with(
        "/me/onenote/pages/page-456/content"
    )

    print(
        "PASS: OneNote page retrieval routed correctly."
    )


def test_onenote_missing_id():
    """
    Verify OneNote retrieval rejects a missing object ID.
    """

    retriever = OneNoteContentRetriever()

    try:
        retriever.retrieve(
            source_object_id=None,
            object_type="page",
        )

        raise AssertionError(
            "Missing OneNote object ID was accepted."
        )

    except ValueError:
        pass

    print(
        "PASS: OneNote missing object ID rejected."
    )


def test_onenote_container_rejected():
    """
    Verify OneNote containers cannot be retrieved as page content.
    """

    retriever = OneNoteContentRetriever()

    for object_type in (
        "notebook",
        "sectionGroup",
        "section",
    ):
        try:
            retriever.retrieve(
                source_object_id="container-123",
                object_type=object_type,
            )

            raise AssertionError(
                f"OneNote {object_type} was accepted "
                "for content retrieval."
            )

        except ValueError:
            pass

    print(
        "PASS: OneNote container objects rejected."
    )


def main():
    """
    Run Microsoft Graph content retriever tests.
    """

    print(
        "\nRunning Microsoft Graph "
        "content retriever tests...\n"
    )

    test_onedrive_retrieval()
    test_onedrive_missing_id()
    test_onenote_retrieval()
    test_onenote_missing_id()
    test_onenote_container_rejected()

    print(
        "\nMicrosoft Graph content "
        "retriever tests PASSED.\n"
    )


if __name__ == "__main__":
    main()