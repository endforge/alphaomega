"""
File: translator_loader.py

Purpose:
    Returns the appropriate Translator implementation for the
    requested Source of Truth.
"""

from scripts.translators.graph_translator import GraphTranslator


class TranslatorLoader:
    """
    Factory responsible for selecting the correct Translator.
    """

    def get_translator(self, source_name):
        """
        Return the Translator responsible for the specified
        Source of Truth.

        Parameters
        ----------
        source_name : str
            Name of the Source of Truth.

        Returns
        -------
        BaseTranslator
            Translator implementation for the requested source.

        Raises
        ------
        ValueError
            If no Translator exists for the specified source.
        """

        source = source_name.lower()

        #
        # Microsoft Graph Sources
        #
        if source in (
            "onedrive",
            "onenote",
            "sharepoint",
        ):
            return GraphTranslator()

        raise ValueError(
            f"No Translator registered for source '{source_name}'."
        )