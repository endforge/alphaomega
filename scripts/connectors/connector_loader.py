"""
File: connector_loader.py

Purpose:
    Loads the appropriate connector for a requested Source of Truth.
"""

from scripts.connectors.graph_connector import GraphConnector

ONEDRIVE = "onedrive"
ONENOTE = "onenote"

def load_connector(source_name):
    """
    Return the connector associated with a source.

    Raises:
        ValueError:
            If the requested source is unsupported.
    """

    source = source_name.lower()

    if source == ONEDRIVE:
        return GraphConnector()

    if source == ONENOTE:
        return GraphConnector()

    raise ValueError(
        f"Unsupported source: '{source_name}'."
    )