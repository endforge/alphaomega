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

from collections.abc import Mapping
from collections.abc import Sequence

from common.object_types import CONTAINER
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


class GraphTranslator(BaseTranslator):
    """
    Translator for Microsoft Graph sources.
    """

    # ========================================================================
    # Public Interface
    # ========================================================================

    def run(self, connector_section):
        """
        Execute the Translator stage.

        Connector objects are individually typed by Connector.

        Record-level errors affect only the individual source object.
        Remaining objects continue processing.

        Stage-level errors propagate to the synchronization orchestrator.
        """

        translator_section = TranslatorSection()

        connector_objects = self._get_source_objects(
            connector_section.raw_objects
        )

        for connector_object in connector_objects:

            source_object_type = connector_object[
                "source_object_type"
            ]

            raw_object = connector_object[
                "raw_object"
            ]

            connector_metadata = (
                connector_object.get(
                    "connector_metadata",
                    {},
                )
            )

            try:

                translator_record = self._translate_record(
                    source_name=(
                        connector_section.source_name
                    ),
                    source_object_type=(
                        source_object_type
                    ),
                    raw_object=(
                        raw_object
                    ),
                    connector_metadata=(
                        connector_metadata
                    ),
                )

                translator_section.translated_records.append(
                    translator_record
                )

            except UnsupportedObjectTypeError as error:

                translator_section.record_errors.append(
                    self._build_record_error(
                        source_name=(
                            connector_section.source_name
                        ),
                        source_object_type=(
                            source_object_type
                        ),
                        raw_object=(
                            raw_object
                        ),
                        error=(
                            error
                        ),
                    )
                )

        translator_section.translation_succeeded = True

        translator_section.lock()

        return translator_section

    # ========================================================================
    # Connector Input Validation
    # ========================================================================

    def _get_source_objects(
        self,
        raw_data,
    ):
        """
        Validate and return Microsoft Graph objects received from Connector.
        """

        if (
            not isinstance(
                raw_data,
                Sequence,
            )
            or isinstance(
                raw_data,
                (str, bytes),
            )
        ):

            raise TypeError(
                "Translator stage received invalid Microsoft Graph "
                "Connector output. Expected a sequence of Connector "
                "objects."
            )

        for connector_object in raw_data:

            if not isinstance(
                connector_object,
                Mapping,
            ):

                raise TypeError(
                    "Translator stage received invalid Microsoft Graph "
                    "Connector object. Expected a mapping."
                )

            if (
                "source_object_type"
                not in connector_object
            ):

                raise TypeError(
                    "Translator stage received Microsoft Graph "
                    "Connector object without source_object_type."
                )

            if (
                "raw_object"
                not in connector_object
            ):

                raise TypeError(
                    "Translator stage received Microsoft Graph "
                    "Connector object without raw_object."
                )

            source_object_type = (
                connector_object[
                    "source_object_type"
                ]
            )

            raw_object = (
                connector_object[
                    "raw_object"
                ]
            )

            connector_metadata = (
                connector_object.get(
                    "connector_metadata",
                    {},
                )
            )

            if not isinstance(
                source_object_type,
                str,
            ):

                raise TypeError(
                    "Translator stage received invalid Microsoft Graph "
                    "source_object_type. Expected a string."
                )

            if not isinstance(
                raw_object,
                Mapping,
            ):

                raise TypeError(
                    "Translator stage received invalid Microsoft Graph "
                    "raw_object. Expected a mapping."
                )

            if not isinstance(
                connector_metadata,
                Mapping,
            ):

                raise TypeError(
                    "Translator stage received invalid Microsoft Graph "
                    "connector_metadata. Expected a mapping."
                )

        return raw_data

    # ========================================================================
    # Record Translation
    # ========================================================================

    def _translate_record(
        self,
        source_name,
        source_object_type,
        raw_object,
        connector_metadata,
    ):
        """
        Translate one Microsoft Graph object into a TranslatorRecord.
        """

        canonical_object_type = self._get_object_type(
            source_object_type=(
                source_object_type
            ),
            raw_object=(
                raw_object
            ),
        )

        if canonical_object_type is None:

            raise UnsupportedObjectTypeError(
                stage="Translator",
                source_name=source_name,
                object_type=source_object_type,
                object_id=raw_object.get(
                    "id"
                ),
                object_name=(
                    raw_object.get(
                        "displayName"
                    )
                    or raw_object.get(
                        "name"
                    )
                    or raw_object.get(
                        "title"
                    )
                ),
            )

        record = TranslatorRecord()

        record.source_name = (
            source_name
        )

        record.object_type = (
            canonical_object_type
        )

        # --------------------------------------------------------------------
        # Canonical Graph field mapping
        # --------------------------------------------------------------------

        for (
            source_field,
            canonical_field,
        ) in GRAPH_FIELD_MAPPING.items():

            value = get_nested_value(
                raw_object,
                source_field,
            )

            if value is None:

                continue

            if (
                canonical_field == "name"
                and record.name is not None
            ):

                continue

            # --------------------------------------------------------------------
            # Canonical Name Normalization
            # --------------------------------------------------------------------

            if canonical_field == "name":

                value = str(
                    value
                ).strip()

            setattr(
                record,
                canonical_field,
                value,
            )

        # --------------------------------------------------------------------
        # OneNote blank-page normalization
        # --------------------------------------------------------------------

        if (
            source_object_type == "page"
            and (
                record.name is None
                or not str(
                    record.name
                ).strip()
            )
        ):

            record.name = "Untitled"

        # --------------------------------------------------------------------
        # Connector-proven hierarchy
        # --------------------------------------------------------------------

        #
        # Connector-derived hierarchy overrides raw Graph hierarchy when
        # Connector has proven a more specific relationship.
        #
        # Example:
        #
        # Graph:
        #     Blueprints -> Minecraft section
        #
        # Connector page-level hierarchy:
        #     Blueprints -> My World Realms page
        #
        if (
            "source_parent_object_id"
            in connector_metadata
        ):

            record.source_parent_object_id = (
                connector_metadata.get(
                    "source_parent_object_id"
                )
            )

        if (
            "source_path"
            in connector_metadata
        ):

            record.source_path = (
                connector_metadata.get(
                    "source_path"
                )
            )

        # --------------------------------------------------------------------
        # Source metadata preservation
        # --------------------------------------------------------------------

        record.metadata = {
            key: value
            for key, value
            in raw_object.items()
            if key
            not in RESERVED_GRAPH_FIELDS
        }

        if connector_metadata:

            record.metadata[
                "connector_hierarchy"
            ] = dict(
                connector_metadata
            )

        return record

    # ========================================================================
    # Object Type Translation
    # ========================================================================

    def _get_object_type(
        self,
        source_object_type,
        raw_object,
    ):
        """
        Determine the AlphaOmega canonical object type.

        Microsoft Graph uses driveItem for both files and folders.
        Folder-faceted driveItems therefore become CONTAINER.
        """

        if (
            source_object_type
            == "driveItem"
            and "folder"
            in raw_object
        ):

            return CONTAINER

        return get_canonical_object_type(
            source_object_type
        )

    # ========================================================================
    # Record-Level Error Handling
    # ========================================================================

    def _build_record_error(
        self,
        source_name,
        source_object_type,
        raw_object,
        error,
    ):
        """
        Build diagnostic information for a record-level Translator error.
        """

        return {
            "stage":
                "Translator",

            "source":
                source_name,

            "object_id":
                raw_object.get(
                    "id"
                ),

            "object_name":
                (
                    raw_object.get(
                        "displayName"
                    )
                    or raw_object.get(
                        "name"
                    )
                    or raw_object.get(
                        "title"
                    )
                    or "Untitled"
                ),

            "object_type":
                source_object_type,

            "exception_type":
                error.__class__.__name__,

            "failure_reason":
                str(error),

            "recommended_action":
                (
                    "Review the Microsoft Graph object type and "
                    "add or correct the required Graph translation "
                    "mapping."
                ),
        }