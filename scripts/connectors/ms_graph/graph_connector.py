"""
File: graph_connector.py

Purpose:
    Executes the Connector stage for Microsoft Graph sources.
"""

from scripts.connectors.base_connector import BaseConnector
from scripts.connectors.ms_graph.graph_connection import graph_get
from scripts.connectors.connector_section import ConnectorSection


ONEDRIVE = "onedrive"
ONENOTE = "onenote"

ONEDRIVE_ENDPOINT = "/me/drive/root"
ONENOTE_ENDPOINT = "/me/onenote/notebooks"


class GraphConnector(BaseConnector):
    """
    Connector for Microsoft Graph sources.
    """

    def run(self, source_name):
        """
        Execute the Connector stage.

        Parameters
        ----------
        source_name : str
            Microsoft Graph source to retrieve.

        Returns
        -------
        ConnectorSection
            Completed, validated, immutable ConnectorSection.
        """

        source = source_name.lower()

        if source == ONEDRIVE:
            endpoint = ONEDRIVE_ENDPOINT
            object_type = "driveRoot"

        elif source == ONENOTE:
            endpoint = ONENOTE_ENDPOINT
            object_type = "notebook"

        else:
            raise ValueError(
                f"Unsupported Microsoft Graph source: '{source_name}'."
            )

        response = graph_get(endpoint)

        connector_section = ConnectorSection(source)

        connector_section.object_type = object_type

        connector_section.connection_succeeded = True

        #
        # Preserve the Source of Truth exactly as returned.
        # No interpretation or normalization occurs here.
        #
        connector_section.raw_objects = response.json()

        connector_section.lock()

        return connector_section