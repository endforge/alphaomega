"""
File: base_connector.py

Purpose:
    Defines the contract all connectors must follow.
"""


class BaseConnector:
    """
    Base class for all AlphaOmega connectors.
    """

    def run(self, source_name):
        """
        Execute the Connector stage.

        Parameters
        ----------
        source_name : str
            Name of the Source of Truth.

        Returns
        -------
        ConnectorSection
            A completed ConnectorSection.

        Raises
        ------
        NotImplementedError
            If the connector does not implement this method.
        """

        raise NotImplementedError(
            "All connectors must implement the 'run()' method."
        )