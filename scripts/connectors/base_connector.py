"""
File: base_connector.py

Purpose:
    Defines the contract all connectors must follow.
"""


class BaseConnector:
    """
    Base class for all AlphaOmega connectors.
    """

    def run(self, processing_job):
        """
        Execute the connector.

        Returns:
            ConnectorSection:
                A completed connector section.

        Raises:
            NotImplementedError:
                If the connector does not implement this method.
        """

        raise NotImplementedError(
            "All connectors must implement the 'run()' method."
        )