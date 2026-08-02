"""
File: graph_connector.py

Purpose:
    Executes the Connector stage for Microsoft Graph sources.
"""

from scripts.connectors.base_connector import BaseConnector
from scripts.graph_connection import graph_get


ONEDRIVE = "onedrive"
ONENOTE = "onenote"

ONEDRIVE_ENDPOINT = "/me/drive/root"
ONENOTE_ENDPOINT = "/me/onenote/notebooks"


class GraphConnector(BaseConnector):
    """
    Connector for Microsoft Graph sources.
    """

    def run(self, source_name, processing_job):
        """
        Execute the Connector stage.

        Returns:
            ConnectorSection
        """

        source = source_name.lower()

        if source == ONEDRIVE:
            endpoint = ONEDRIVE_ENDPOINT

        elif source == ONENOTE:
            endpoint = ONENOTE_ENDPOINT

        else:
            raise ValueError(
                f"Unsupported Microsoft Graph source: '{source_name}'."
            )

        response = graph_get(endpoint)

        # TODO:
        # Create ConnectorSection

        # TODO:
        # Store raw Graph response

        # TODO:
        # Lock ConnectorSection

        # TODO:
        # Return ConnectorSection