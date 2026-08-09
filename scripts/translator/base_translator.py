"""
File: base_translator.py

Purpose:
    Defines the contract all translators must follow.
"""


class BaseTranslator:
    """
    Base class for all AlphaOmega translators.
    """

    def run(self, connector_section):
        """
        Execute the Translator stage.

        Parameters
        ----------
        connector_section : ConnectorSection
            Locked ConnectorSection produced by the Connector stage.

        Returns
        -------
        TranslatorSection
            A completed TranslatorSection.

        Raises
        ------
        NotImplementedError
            If the translator does not implement this method.
        """

        raise NotImplementedError(
            "All translators must implement the 'run()' method."
        )