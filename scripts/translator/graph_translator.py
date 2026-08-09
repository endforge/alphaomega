"""
File: graph_translator.py

Purpose:
    Executes the Translator stage for Microsoft Graph sources.

The GraphTranslator converts raw Microsoft Graph data preserved by the
Connector stage into AlphaOmega's canonical synchronization model.

Microsoft-specific structure is understood only by the GraphTranslator
and its mapping module. Downstream synchronization stages operate only
on TranslatorRecord objects.
"""

from scripts.translator.base_translator import BaseTranslator
from scripts.translator.graph_translator_mappings import (
    GRAPH_FIELD_MAPPING,
    RESERVED_GRAPH_FIELDS,
    get_canonical_object_type,
    get_nested_value,
)
from scripts.translator.translator_record import TranslatorRecord
from scripts.translator.translator_section import TranslatorSection
from scripts.sync.sync_exceptions import UnsupportedObjectTypeError
from collections.abc import Mapping
from collections.abc import Sequence

class GraphTranslator(BaseTranslator):
    """
    Translator for Microsoft Graph sources.
    """

    def run(self, connector_section):
        """
        Execute the Translator stage.

        Parameters
        ----------
        connector_section : ConnectorSection
            Completed ConnectorSection containing the raw Microsoft
            Graph response.

        Returns
        -------
        TranslatorSection
            Completed and locked TranslatorSection containing
            successfully translated records and any record-level errors.

        Notes
        -----
        Record-level errors affect only the individual source object.
        Remaining objects continue processing.

        Stage-level errors are not suppressed and will propagate to the
        synchronization orchestrator.
        """

        translator_section = TranslatorSection()

        raw_objects = self._get_source_objects(
            connector_section.raw_objects
        )

        for raw_object in raw_objects:

            try:
                translator_record = self._translate_record(
                    source_name=connector_section.source_name,
                    source_object_type=connector_section.object_type,
                    raw_object=raw_object,
                )

                translator_section.translated_records.append(
                    translator_record
                )

            except UnsupportedObjectTypeError as error:

                translator_section.record_errors.append(
                    self._build_record_error(
                        source_name=connector_section.source_name,
                        raw_object=raw_object,
                        error=error,
                    )
                )

        translator_section.translation_succeeded = True

        translator_section.lock()

        return translator_section

    def _get_source_objects(self, raw_data):
        """
        Return individual Microsoft Graph source objects.

        Microsoft Graph may return either:

        - A collection response containing a "value" list.
        - A single object response.

        Parameters
        ----------
        raw_data : dict
            Raw Microsoft Graph response preserved by Connector.

        Returns
        -------
        list
            Individual Microsoft Graph objects.

        Raises
        ------
        TypeError
            If Connector output does not contain a valid Microsoft
            Graph response structure.
        """

        if not isinstance(raw_data, Mapping):
            raise TypeError(
                "Translator stage received invalid Microsoft Graph "
                "Connector output. Expected a mapping."
            )

        if "value" in raw_data:

            objects = raw_data["value"]

            if (
                not isinstance(objects, Sequence)
                or isinstance(objects, (str, bytes))
            ):
                raise TypeError(
                    "Translator stage received invalid Microsoft Graph "
                    "collection data. The 'value' field must contain "
                    "a sequence."
                )

            return objects

        return [raw_data]

    def _translate_record(self, source_name, source_object_type, raw_object,):
        """
        Translate one Microsoft Graph object into a TranslatorRecord.

        Parameters
        ----------
        source_name : str
            Source of Truth that produced the object.

        raw_object : dict
            Individual raw Microsoft Graph object.

        Returns
        -------
        TranslatorRecord
            AlphaOmega canonical synchronization record.

        Raises
        ------
        UnsupportedObjectTypeError
            If the Microsoft Graph object cannot be mapped to an
            AlphaOmega canonical object type.
        """

        canonical_object_type = get_canonical_object_type(
            source_object_type
        )

        if canonical_object_type is None:
            raise UnsupportedObjectTypeError(
                stage="Translator",
                source_name=source_name,
                object_type=source_object_type,
                object_id=raw_object.get("id"),
                object_name=(
                    raw_object.get("displayName")
                    or raw_object.get("name")
                ),
            )

        record = TranslatorRecord()

        record.source_name = source_name
        record.object_type = canonical_object_type

        for source_field, canonical_field in GRAPH_FIELD_MAPPING.items():

            value = get_nested_value(
                raw_object,
                source_field,
            )

            if value is None:
                continue

            #
            # Some Microsoft Graph object types use "displayName"
            # while others use "name". Both map to AlphaOmega's
            # canonical "name" field.
            #
            if (
                canonical_field == "name"
                and record.name is not None
            ):
                continue

            setattr(
                record,
                canonical_field,
                value,
            )

        record.metadata = {
            key: value
            for key, value in raw_object.items()
            if key not in RESERVED_GRAPH_FIELDS
        }

        return record

    def _build_record_error(
        self,
        source_name,
        raw_object,
        error,
    ):
        """
        Build the diagnostic record for a record-level exception.

        Parameters
        ----------
        source_name : str
            Source of Truth.

        raw_object : dict
            Source object that failed translation.

        error : Exception
            Exception raised while processing the object.

        Returns
        -------
        dict
            Structured diagnostic information for later reporting
            and persistence by the synchronization orchestrator.
        """

        return {
            "stage": "Translator",
            "source": source_name,
            "object_id": raw_object.get("id"),
            "object_name": (
                raw_object.get("displayName")
                or raw_object.get("name")
            ),
            "object_type": raw_object.get("@odata.type"),
            "exception_type": error.__class__.__name__,
            "failure_reason": str(error),
            "recommended_action": (
                "Review the Microsoft Graph object type and add the "
                "required mapping to graph_translator_mappings.py."
            ),
        }