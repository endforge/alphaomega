"""
File: onenote_content_retriever.py

Purpose:
    Retrieves the raw content of one identified OneNote page
    for downstream Extraction.

This module does NOT:
    - Enumerate OneNote.
    - Determine synchronization state.
    - Extract canonical content.
    - Generate content hashes.
    - Persist Knowledge Objects.
"""

from scripts.connectors.ms_graph.graph_connection import graph_get


class OneNoteContentRetriever:
    """
    Retrieve raw HTML content for one OneNote page.
    """

    source_name = "onenote"

    def retrieve(
        self,
        source_object_id,
        object_type,
    ):
        """
        Retrieve the raw HTML content of one OneNote page.

        Args:
            source_object_id:
                Microsoft Graph OneNote page ID.

            object_type:
                Canonical object type supplied by Translator.

        Returns:
            bytes:
                Raw OneNote page HTML.

        Raises:
            ValueError:
                If source_object_id is missing or the requested object
                is not a OneNote page.
        """

        if not source_object_id:
            raise ValueError(
                "OneNote source object ID is required."
            )

        if object_type != "page":
            raise ValueError(
                "OneNote content retrieval supports "
                "page objects only. "
                f"Received object type '{object_type}'."
            )

        endpoint = (
            "/me/onenote/pages/"
            f"{source_object_id}/content"
        )

        response = graph_get(
            endpoint
        )

        return response.content