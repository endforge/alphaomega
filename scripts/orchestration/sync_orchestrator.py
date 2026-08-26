"""
File: sync_orchestrator.py

Purpose:
    Coordinates execution of one AlphaOmega synchronization run.

The Synchronization Orchestrator owns:
    - Processing Job lifecycle.
    - Connector execution.
    - Correlation identity creation after Connector and before Translator.
    - Cross-stage SynchronizationAssociation construction.
    - Translator execution.
    - Discovery execution.
    - Routing of eligible records.
    - Extraction execution for NEW/MODIFIED records requiring extraction.
    - Load execution for successfully extracted NEW records and
      MODIFIED records whose canonical content changed.
    - Stage-level failure control flow.

The Synchronization Orchestrator does NOT:
    - Decide what the user wants synchronized.
    - Implement source-specific retrieval logic.
    - Translate source metadata.
    - Determine synchronization state.
    - Extract canonical content.
    - Persist Knowledge Objects directly.
    - Generate stage-owned data.

A synchronization request is supplied by a future request/application
layer.
"""

from scripts.sync.sync_translation_input import (
    TranslationInput,
)

from scripts.sync.sync_association import (
    SynchronizationAssociation,
)

from scripts.sync.sync_state import (
    SyncState,
)


class SynchronizationOrchestrator:
    """
    Coordinate one AlphaOmega synchronization run.
    """

    def __init__(
        self,
        *,
        connector,
        translator,
        discovery_service,
        extraction_service,
        load_service,
        processing_job_repository,
        pipeline_version,
    ):
        """
        Initialize orchestration dependencies.
        """

        if connector is None:
            raise ValueError(
                "Connector is required."
            )

        if translator is None:
            raise ValueError(
                "Translator is required."
            )

        if discovery_service is None:
            raise ValueError(
                "DiscoveryService is required."
            )

        if extraction_service is None:
            raise ValueError(
                "ExtractionService is required."
            )

        if load_service is None:
            raise ValueError(
                "LoadService is required."
            )

        if processing_job_repository is None:
            raise ValueError(
                "ProcessingJobRepository is required."
            )

        if (
            pipeline_version is None
            or not str(
                pipeline_version
            ).strip()
        ):
            raise ValueError(
                "pipeline_version is required."
            )

        self._connector = connector
        self._translator = translator
        self._discovery_service = (
            discovery_service
        )
        self._extraction_service = (
            extraction_service
        )
        self._load_service = (
            load_service
        )
        self._processing_job_repository = (
            processing_job_repository
        )

        self._pipeline_version = (
            str(
                pipeline_version
            ).strip()
        )

    def run(
        self,
        *,
        source_name,
        job_metadata=None,
    ):
        """
        Execute one synchronization run.

        Current first-version request contract:
            source_name

        Scope selection remains a future request-layer concern.

        Returns:
            dict:
                Synchronization run outputs and summary counts.
        """

        self._validate_run_request(
            source_name
        )

        if job_metadata is None:
            job_metadata = {}

        processing_job_id = None

        try:

            # ================================================================
            # Processing Job
            # ================================================================

            processing_job_id = (
                self._processing_job_repository.create(
                    process_type="sync",
                    pipeline_version=(
                        self._pipeline_version
                    ),
                    metadata=job_metadata,
                )
            )

            # ================================================================
            # Connector
            # ================================================================

            connector_section = (
                self._connector.run(
                    source_name
                )
            )

            self._validate_locked_section(
                connector_section,
                "ConnectorSection",
            )

            # ================================================================
            # Correlation Boundary
            #
            # TranslationInput assigns one orchestration-owned
            # correlation UUID to each Connector object.
            # ================================================================

            translation_input = (
                TranslationInput(
                    connector_section
                )
            )

            # ================================================================
            # Build Associations
            #
            # Associations exist for every Connector object before
            # Translator begins.
            # ================================================================

            associations = (
                self._create_associations(
                    translation_input
                )
            )

            # ================================================================
            # Translator
            # ================================================================

            translator_section = (
                self._translator.run(
                    translation_input
                )
            )

            self._validate_locked_section(
                translator_section,
                "TranslatorSection",
            )

            self._attach_translator_records(
                associations=associations,
                translator_section=(
                    translator_section
                ),
            )

            # ================================================================
            # Discovery
            # ================================================================

            discovery_section = (
                self._discovery_service.run(
                    translator_section
                )
            )

            self._validate_locked_section(
                discovery_section,
                "DiscoverySection",
            )

            self._attach_discovery_records(
                associations=associations,
                discovery_section=(
                    discovery_section
                ),
            )

            # ================================================================
            # Extraction Routing
            # ================================================================

            extraction_associations = (
                self._select_extraction_associations(
                    associations
                )
            )

            extraction_section = None
            load_section = None

            if extraction_associations:

                extraction_inputs = [
                    association.translator_record
                    for association
                    in extraction_associations
                ]

                # ============================================================
                # Extraction
                # ============================================================

                extraction_section = (
                    self._extraction_service.run(
                        extraction_inputs
                    )
                )

                self._validate_locked_section(
                    extraction_section,
                    "ExtractionSection",
                )

                self._attach_extraction_records(
                    associations=(
                        extraction_associations
                    ),
                    extraction_section=(
                        extraction_section
                    ),
                )

                # ============================================================
                # Load Routing
                #
                # Records with Extraction record-level failures have no
                # ExtractionRecord and therefore stop here.
                #
                # MODIFIED records whose extracted content hash matches
                # the previous stored content hash also stop here because
                # canonical content did not change.
                # ============================================================

                load_associations = (
                    self._select_load_associations(
                        extraction_associations
                    )
                )

                if load_associations:

                    load_section = (
                        self._load_service.run(
                            associations=(
                                load_associations
                            ),
                            processing_job_id=(
                                processing_job_id
                            ),
                        )
                    )

                    self._validate_locked_section(
                        load_section,
                        "LoadSection",
                    )

            # ================================================================
            # Complete Processing Job
            # ================================================================

            self._processing_job_repository.complete(
                processing_job_id
            )

            return {
                "processing_job_id":
                    processing_job_id,

                "connector_section":
                    connector_section,

                "translator_section":
                    translator_section,

                "discovery_section":
                    discovery_section,

                "extraction_section":
                    extraction_section,

                "load_section":
                    load_section,

                "associations":
                    tuple(
                        associations.values()
                    ),

                "counts":
                    self._build_counts(
                        associations
                    ),
            }

        except Exception as error:

            if processing_job_id is not None:

                try:
                    self._processing_job_repository.fail(
                        processing_job_id,
                        error,
                    )

                except Exception as job_error:

                    raise RuntimeError(
                        "Synchronization failed and the "
                        "Processing Job could not be marked failed."
                    ) from job_error

            raise

    @staticmethod
    def _create_associations(
        translation_input,
    ):
        """
        Create one orchestration-owned association for every
        correlated Connector object.
        """

        associations = {}

        for correlated_object in (
            translation_input.raw_objects
        ):

            correlation_id = (
                correlated_object[
                    "correlation_id"
                ]
            )

            if correlation_id in associations:
                raise RuntimeError(
                    "Duplicate orchestration correlation_id."
                )

            associations[
                correlation_id
            ] = (
                SynchronizationAssociation(
                    correlation_id
                )
            )

        return associations

    @staticmethod
    def _attach_translator_records(
        *,
        associations,
        translator_section,
    ):
        """
        Attach successfully translated records by correlation ID.

        Translator record-level failures remain without a
        TranslatorRecord and stop downstream.
        """

        for translator_record in (
            translator_section.translated_records
        ):

            correlation_id = (
                translator_record.correlation_id
            )

            association = (
                associations.get(
                    correlation_id
                )
            )

            if association is None:
                raise RuntimeError(
                    "Translator produced an unknown "
                    "correlation_id."
                )

            association.attach_translator(
                translator_record
            )

    @staticmethod
    def _attach_discovery_records(
        *,
        associations,
        discovery_section,
    ):
        """
        Attach successfully discovered records by correlation ID.
        """

        for discovery_record in (
            discovery_section.discovery_records
        ):

            correlation_id = (
                discovery_record.correlation_id
            )

            association = (
                associations.get(
                    correlation_id
                )
            )

            if association is None:
                raise RuntimeError(
                    "Discovery produced an unknown "
                    "correlation_id."
                )

            if (
                association.translator_record
                is None
            ):
                raise RuntimeError(
                    "Discovery record has no associated "
                    "TranslatorRecord."
                )

            association.attach_discovery(
                discovery_record
            )

    @staticmethod
    def _select_extraction_associations(
        associations,
    ):
        """
        Select NEW and MODIFIED records requiring Extraction.

        UNCHANGED records stop after Discovery.
        """

        eligible = []

        for association in (
            associations.values()
        ):

            discovery_record = (
                association.discovery_record
            )

            if discovery_record is None:
                continue

            if (
                discovery_record.sync_state
                not in (
                    SyncState.NEW,
                    SyncState.MODIFIED,
                )
            ):
                continue

            if (
                discovery_record.requires_extraction
                is not True
            ):
                continue

            if (
                association.translator_record
                is None
            ):
                continue

            eligible.append(
                association
            )

        return tuple(
            eligible
        )

    @staticmethod
    def _select_load_associations(
        extraction_associations,
    ):
        """
        Select successfully extracted records eligible for Load.

        NEW records proceed to Load after successful Extraction.

        MODIFIED records proceed to Load only when the newly extracted
        canonical content hash differs from the previous stored hash.

        A MODIFIED record with matching hashes remains MODIFIED and
        retains its ExtractionRecord, but stops before Load because
        canonical content did not change.
        """

        eligible = []

        for association in (
            extraction_associations
        ):

            extraction_record = (
                association.extraction_record
            )

            if extraction_record is None:
                continue

            discovery_record = (
                association.discovery_record
            )

            if discovery_record is None:
                continue

            if (
                discovery_record.sync_state
                == SyncState.NEW
            ):
                eligible.append(
                    association
                )

                continue

            if (
                discovery_record.sync_state
                != SyncState.MODIFIED
            ):
                continue

            previous_content_hash = (
                discovery_record
                .previous_content_hash
            )

            current_content_hash = (
                extraction_record
                .content_hash
            )

            if (
                previous_content_hash
                is not None
                and
                current_content_hash
                == previous_content_hash
            ):
                continue

            eligible.append(
                association
            )

        return tuple(
            eligible
        )

    @staticmethod
    def _attach_extraction_records(
        *,
        associations,
        extraction_section,
    ):
        """
        Attach successful Extraction records by correlation ID.
        """

        association_map = {
            association.correlation_id:
                association
            for association
            in associations
        }

        for extraction_record in (
            extraction_section.extraction_records
        ):

            correlation_id = (
                extraction_record.correlation_id
            )

            association = (
                association_map.get(
                    correlation_id
                )
            )

            if association is None:
                raise RuntimeError(
                    "Extraction produced an unknown "
                    "correlation_id."
                )

            association.attach_extraction(
                extraction_record
            )

    @staticmethod
    def _validate_locked_section(
        section,
        section_name,
    ):
        """
        Verify a successfully completed stage returned locked output.
        """

        if section is None:
            raise RuntimeError(
                f"{section_name} was not produced."
            )

        if not getattr(
            section,
            "is_locked",
            False,
        ):
            raise RuntimeError(
                f"{section_name} is not locked."
            )

    @staticmethod
    def _build_counts(
        associations,
    ):
        """
        Build minimal orchestration-level synchronization counts.
        """

        values = tuple(
            associations.values()
        )

        translated = sum(
            1
            for association
            in values
            if association.translator_record
            is not None
        )

        discovered = sum(
            1
            for association
            in values
            if association.discovery_record
            is not None
        )

        extracted = sum(
            1
            for association
            in values
            if association.extraction_record
            is not None
        )

        new = sum(
            1
            for association
            in values
            if (
                association.discovery_record
                is not None
                and association.discovery_record.sync_state
                == SyncState.NEW
            )
        )

        modified = sum(
            1
            for association
            in values
            if (
                association.discovery_record
                is not None
                and association.discovery_record.sync_state
                == SyncState.MODIFIED
            )
        )

        unchanged = sum(
            1
            for association
            in values
            if (
                association.discovery_record
                is not None
                and association.discovery_record.sync_state
                == SyncState.UNCHANGED
            )
        )

        return {
            "associations":
                len(
                    values
                ),

            "translated":
                translated,

            "discovered":
                discovered,

            "extracted":
                extracted,

            "new":
                new,

            "modified":
                modified,

            "unchanged":
                unchanged,
        }

    @staticmethod
    def _validate_run_request(
        source_name,
    ):
        """
        Validate the current minimal synchronization request.
        """

        if (
            source_name is None
            or not str(
                source_name
            ).strip()
        ):
            raise ValueError(
                "source_name is required."
            )