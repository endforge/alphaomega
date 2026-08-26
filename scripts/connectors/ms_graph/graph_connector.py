"""
File: graph_connector.py

Purpose:
    Executes the Connector stage for Microsoft Graph Sources of Truth.

Responsibilities:
    - Completely enumerate the requested Microsoft Graph source.
    - Preserve raw Microsoft Graph objects.
    - Preserve each object's Microsoft Graph source type.
    - Handle Microsoft Graph paging.
    - Use source-specific retrieval strategies.
    - Recover from transient Microsoft Graph failures.
    - Respect Microsoft Graph throttling.
    - Preserve source hierarchy information when Microsoft Graph
      provides enough information to prove that hierarchy.
    - Preserve the containing OneNote Section modification timestamp
      with OneNote Page connector metadata for downstream synchronization
      comparison.
    - Return Connector output only after complete enumeration succeeds.

This module does NOT:
    - Normalize Microsoft Graph objects into AlphaOmega objects.
    - Determine synchronization state.
    - Extract canonical content.
    - Persist Knowledge Objects.
"""

import time
import requests

from scripts.connectors.base_connector import BaseConnector
from scripts.connectors.ms_graph.graph_connection import graph_get
from scripts.connectors.connector_section import ConnectorSection


# ============================================================================
# Supported Sources
# ============================================================================

ONEDRIVE = "onedrive"
ONENOTE = "onenote"


# ============================================================================
# Microsoft Graph Endpoints
# ============================================================================

ONEDRIVE_DELTA_ENDPOINT = "/me/drive/root/delta"

ONENOTE_NOTEBOOKS_ENDPOINT = (
    "/me/onenote/notebooks"
    "?$expand=sections,sectionGroups($expand=sections)"
)


# ============================================================================
# Retrieval Configuration
# ============================================================================

MAX_REQUEST_ATTEMPTS = 5
STANDARD_RETRY_DELAY_SECONDS = 2

ONENOTE_PAGE_SIZE = 100


# ============================================================================
# Throttling Configuration
# ============================================================================

THROTTLE_INITIAL_DELAY_SECONDS = 5
THROTTLE_MAX_DELAY_SECONDS = 60
THROTTLE_MAX_TOTAL_WAIT_SECONDS = 600


class GraphConnector(BaseConnector):
    """
    Connector for Microsoft Graph Sources of Truth.
    """

    # ========================================================================
    # Public Interface
    # ========================================================================

    def run(self, source_name):
        """
        Execute the Connector stage.

        Nothing is returned downstream until the entire requested
        synchronization scope has been successfully enumerated.
        """

        source = source_name.lower()

        connector_section = ConnectorSection(
            source
        )

        if source == ONEDRIVE:

            raw_objects, raw_metadata = (
                self._enumerate_onedrive()
            )

        elif source == ONENOTE:

            raw_objects, raw_metadata = (
                self._enumerate_onenote()
            )

        else:

            raise ValueError(
                "Unsupported Microsoft Graph source: "
                f"'{source_name}'."
            )

        connector_section.raw_objects = (
            raw_objects
        )

        connector_section.raw_metadata = (
            raw_metadata
        )

        connector_section.connection_succeeded = (
            True
        )

        self._validate_completed_section(
            connector_section
        )

        connector_section.lock()

        return connector_section

    # ========================================================================
    # Shared Retrieval Functions
    # ========================================================================

    def _get_json(self, endpoint):
        """
        Retrieve and parse one Microsoft Graph response.

        Normal transient failures and Microsoft Graph throttling use
        separate recovery policies.
        """

        normal_attempts = 0

        last_exception = None

        throttle_delay = (
            THROTTLE_INITIAL_DELAY_SECONDS
        )

        total_throttle_wait = 0

        while True:

            try:

                response = graph_get(
                    endpoint
                )

                return response.json()

            except requests.HTTPError as exception:

                last_exception = exception

                response = exception.response

                # ============================================================
                # Microsoft Graph throttling
                # ============================================================

                if (
                    response is not None
                    and response.status_code == 429
                ):

                    retry_after = (
                        response.headers.get(
                            "Retry-After"
                        )
                    )

                    if retry_after is not None:

                        try:

                            wait_seconds = int(
                                retry_after
                            )

                        except ValueError:

                            wait_seconds = (
                                throttle_delay
                            )

                    else:

                        wait_seconds = (
                            throttle_delay
                        )

                    remaining_budget = (
                        THROTTLE_MAX_TOTAL_WAIT_SECONDS
                        - total_throttle_wait
                    )

                    if remaining_budget <= 0:

                        raise RuntimeError(
                            "Microsoft Graph remained throttled "
                            "beyond the Connector's allowed "
                            "recovery window of "
                            f"{THROTTLE_MAX_TOTAL_WAIT_SECONDS} "
                            "seconds."
                        ) from exception

                    wait_seconds = min(
                        wait_seconds,
                        remaining_budget,
                    )

                    print(
                        "Microsoft Graph throttled "
                        "the Connector. "
                        f"Waiting {wait_seconds} "
                        "seconds before retrying..."
                    )

                    time.sleep(
                        wait_seconds
                    )

                    total_throttle_wait += (
                        wait_seconds
                    )

                    if retry_after is None:

                        throttle_delay = min(
                            throttle_delay * 2,
                            THROTTLE_MAX_DELAY_SECONDS,
                        )

                    continue

                # ============================================================
                # Other HTTP errors
                # ============================================================

                normal_attempts += 1

                if (
                    normal_attempts
                    >= MAX_REQUEST_ATTEMPTS
                ):

                    break

                time.sleep(
                    STANDARD_RETRY_DELAY_SECONDS
                )

            except (
                requests.ConnectionError,
                requests.Timeout,
            ) as exception:

                last_exception = exception

                normal_attempts += 1

                if (
                    normal_attempts
                    >= MAX_REQUEST_ATTEMPTS
                ):

                    break

                time.sleep(
                    STANDARD_RETRY_DELAY_SECONDS
                )

        raise RuntimeError(
            "Microsoft Graph retrieval failed "
            f"after {MAX_REQUEST_ATTEMPTS} "
            "normal recovery attempts."
        ) from last_exception

    def _get_collection(
        self,
        endpoint,
    ):
        """
        Retrieve an entire standard Microsoft Graph collection.

        Follows @odata.nextLink until the collection is complete.
        """

        objects = []

        next_endpoint = endpoint

        while next_endpoint is not None:

            response_data = self._get_json(
                next_endpoint
            )

            page_objects = (
                response_data.get(
                    "value"
                )
            )

            if page_objects is None:

                raise RuntimeError(
                    "Microsoft Graph collection "
                    "response did not contain "
                    "the expected 'value' field."
                )

            objects.extend(
                page_objects
            )

            next_endpoint = (
                response_data.get(
                    "@odata.nextLink"
                )
            )

        return objects

    @staticmethod
    def _wrap_object(
        source_object_type,
        raw_object,
        connector_metadata=None,
    ):
        """
        Preserve a raw source object while associating it with its
        Microsoft Graph source object type.

        The raw Microsoft Graph object itself is never modified.

        connector_metadata contains Connector-derived source hierarchy
        and source context information that cannot be expressed directly
        by the raw Graph object.
        """

        if connector_metadata is None:

            connector_metadata = {}

        return {
            "source_object_type":
                source_object_type,

            "raw_object":
                raw_object,

            "connector_metadata":
                connector_metadata,
        }

    @staticmethod
    def _join_source_path(
        parent_path,
        object_name,
    ):
        """
        Construct a human-readable source hierarchy path.
        """

        if not object_name:

            return parent_path

        if not parent_path:

            return object_name

        return (
            f"{parent_path}/{object_name}"
        )

    @staticmethod
    def _get_onenote_name(
        raw_object,
        source_object_type,
    ):
        """
        Return the human-readable Microsoft OneNote object name.

        A valid OneNote page with a blank title is represented as
        Untitled for hierarchy display purposes.
        """

        if source_object_type == "page":

            title = raw_object.get(
                "title"
            )

            if (
                title is None
                or not str(title).strip()
            ):

                return "Untitled"

            return str(title).strip()

        name = (
            raw_object.get("displayName")
            or raw_object.get("name")
        )

        if name is None:

            return None

        return str(name).strip()

    # ========================================================================
    # OneDrive Enumeration
    # ========================================================================

    def _enumerate_onedrive(self):
        """
        Completely enumerate OneDrive using Microsoft Graph delta.

        Microsoft Graph delta can return the same driveItem more than once
        during a complete enumeration. The Connector therefore resolves the
        delta sequence into one current-state object per Microsoft Graph ID.

        Deleted objects are not returned downstream.
        """

        objects_by_id = {}

        next_endpoint = (
            ONEDRIVE_DELTA_ENDPOINT
        )

        delta_link = None
        pages_retrieved = 0

        while next_endpoint is not None:

            response_data = self._get_json(
                next_endpoint
            )

            page_objects = (
                response_data.get(
                    "value"
                )
            )

            if page_objects is None:

                raise RuntimeError(
                    "OneDrive delta response "
                    "did not contain the expected "
                    "'value' field."
                )

            pages_retrieved += 1

            for item in page_objects:

                item_id = item.get(
                    "id"
                )

                if not item_id:

                    raise RuntimeError(
                        "OneDrive driveItem is missing "
                        "its source object ID."
                    )

                # ============================================================
                # Deleted object
                # ============================================================

                if "deleted" in item:

                    objects_by_id.pop(
                        item_id,
                        None,
                    )

                    continue

                # ============================================================
                # Current object state
                # ============================================================

                objects_by_id[
                    item_id
                ] = self._wrap_object(
                    "driveItem",
                    item,
                )

            next_link = (
                response_data.get(
                    "@odata.nextLink"
                )
            )

            if next_link is not None:

                next_endpoint = (
                    next_link
                )

                continue

            delta_link = (
                response_data.get(
                    "@odata.deltaLink"
                )
            )

            if delta_link is None:

                raise RuntimeError(
                    "OneDrive delta enumeration "
                    "ended without returning "
                    "@odata.deltaLink. "
                    "Complete enumeration cannot "
                    "be proven."
                )

            next_endpoint = None

        raw_objects = list(
            objects_by_id.values()
        )

        raw_metadata = {
            "enumeration_complete":
                True,

            "retrieval_strategy":
                "delta",

            "objects_retrieved":
                len(raw_objects),

            "pages_retrieved":
                pages_retrieved,

            "delta_link":
                delta_link,
        }

        return (
            raw_objects,
            raw_metadata,
        )

    # ========================================================================
    # OneNote Enumeration
    # ========================================================================

    def _enumerate_onenote(self):
        """
        Completely enumerate OneNote.

        Connector preserves:
            notebook hierarchy
            section-group hierarchy
            section hierarchy
            page/subpage hierarchy when Microsoft Graph supplies
            trustworthy page ordering information

        For OneNote Pages, Connector also preserves the containing
        Section's lastModifiedDateTime as connector metadata. Microsoft
        Graph Page lastModifiedDateTime is not relied upon as the
        authoritative page-content synchronization signal.
        """

        raw_objects = []

        sections = []

        section_ids = set()
        section_group_ids = set()

        notebooks = self._get_collection(
            ONENOTE_NOTEBOOKS_ENDPOINT
        )

        for notebook in notebooks:

            notebook_id = notebook.get(
                "id"
            )

            notebook_name = (
                self._get_onenote_name(
                    notebook,
                    "notebook",
                )
            )

            if not notebook_id:

                raise RuntimeError(
                    "OneNote notebook is missing "
                    "its source object ID."
                )

            if not notebook_name:

                raise RuntimeError(
                    "OneNote notebook is missing "
                    "its display name."
                )

            raw_objects.append(
                self._wrap_object(
                    "notebook",
                    notebook,
                    connector_metadata={
                        "source_parent_object_id":
                            None,

                        "source_path":
                            None,

                        "object_path":
                            notebook_name,

                        "hierarchy_verified":
                            True,
                    },
                )
            )

            notebook_sections = (
                notebook.get(
                    "sections",
                    [],
                )
            )

            for section in notebook_sections:

                self._add_onenote_section(
                    section=section,
                    raw_objects=raw_objects,
                    sections=sections,
                    section_ids=section_ids,
                    parent_object_id=notebook_id,
                    parent_path=notebook_name,
                )

            section_groups = (
                notebook.get(
                    "sectionGroups",
                    [],
                )
            )

            for section_group in section_groups:

                self._add_onenote_section_group(
                    section_group=section_group,
                    raw_objects=raw_objects,
                    sections=sections,
                    section_ids=section_ids,
                    section_group_ids=(
                        section_group_ids
                    ),
                    parent_object_id=notebook_id,
                    parent_path=notebook_name,
                )

        for section_context in sections:

            self._enumerate_onenote_section_pages(
                section_context=section_context,
                raw_objects=raw_objects,
            )

        raw_metadata = {
            "enumeration_complete":
                True,

            "retrieval_strategy":
                "expanded_hierarchy_with_pagelevel",

            "objects_retrieved":
                len(raw_objects),

            "notebooks_retrieved":
                len(notebooks),

            "sections_retrieved":
                len(sections),

            "section_groups_retrieved":
                len(section_group_ids),

            "page_hierarchy_required":
                True,
        }

        return (
            raw_objects,
            raw_metadata,
        )

    def _add_onenote_section(
        self,
        section,
        raw_objects,
        sections,
        section_ids,
        parent_object_id,
        parent_path,
    ):
        """
        Add one OneNote section and preserve its source hierarchy.
        """

        section_id = (
            section.get(
                "id"
            )
        )

        if not section_id:

            raise RuntimeError(
                "OneNote section is missing "
                "its source object ID."
            )

        if section_id in section_ids:

            return

        section_name = (
            self._get_onenote_name(
                section,
                "section",
            )
        )

        if not section_name:

            raise RuntimeError(
                "OneNote section is missing "
                "its display name."
            )

        section_ids.add(
            section_id
        )

        section_path = (
            self._join_source_path(
                parent_path,
                section_name,
            )
        )

        raw_objects.append(
            self._wrap_object(
                "section",
                section,
                connector_metadata={
                    "source_parent_object_id":
                        parent_object_id,

                    "source_path":
                        parent_path,

                    "object_path":
                        section_path,

                    "hierarchy_verified":
                        True,
                },
            )
        )

        sections.append(
            {
                "raw_object":
                    section,

                "object_path":
                    section_path,
            }
        )

    def _add_onenote_section_group(
        self,
        section_group,
        raw_objects,
        sections,
        section_ids,
        section_group_ids,
        parent_object_id,
        parent_path,
    ):
        """
        Add one OneNote section group and recursively enumerate nested groups.
        """

        section_group_id = (
            section_group.get(
                "id"
            )
        )

        if not section_group_id:

            raise RuntimeError(
                "OneNote section group is missing "
                "its source object ID."
            )

        if (
            section_group_id
            in section_group_ids
        ):

            return

        section_group_name = (
            self._get_onenote_name(
                section_group,
                "sectionGroup",
            )
        )

        if not section_group_name:

            raise RuntimeError(
                "OneNote section group is missing "
                "its display name."
            )

        section_group_ids.add(
            section_group_id
        )

        section_group_path = (
            self._join_source_path(
                parent_path,
                section_group_name,
            )
        )

        raw_objects.append(
            self._wrap_object(
                "sectionGroup",
                section_group,
                connector_metadata={
                    "source_parent_object_id":
                        parent_object_id,

                    "source_path":
                        parent_path,

                    "object_path":
                        section_group_path,

                    "hierarchy_verified":
                        True,
                },
            )
        )

        group_sections = (
            section_group.get(
                "sections",
                [],
            )
        )

        for section in group_sections:

            self._add_onenote_section(
                section=section,
                raw_objects=raw_objects,
                sections=sections,
                section_ids=section_ids,
                parent_object_id=(
                    section_group_id
                ),
                parent_path=(
                    section_group_path
                ),
            )

        child_groups_endpoint = (
            "/me/onenote/sectionGroups/"
            f"{section_group_id}/sectionGroups"
            "?$expand=sections"
        )

        child_groups = self._get_collection(
            child_groups_endpoint
        )

        for child_group in child_groups:

            self._add_onenote_section_group(
                section_group=child_group,
                raw_objects=raw_objects,
                sections=sections,
                section_ids=section_ids,
                section_group_ids=(
                    section_group_ids
                ),
                parent_object_id=(
                    section_group_id
                ),
                parent_path=(
                    section_group_path
                ),
            )

    def _enumerate_onenote_section_pages(
        self,
        section_context,
        raw_objects,
    ):
        """
        Retrieve all pages belonging to one OneNote section.

        pagelevel=true asks Microsoft Graph for:
            level
            order

        Microsoft Graph page levels represent relative indentation.
        Numeric levels are not guaranteed to increase by exactly one.

        Example:
            Parent page: level 0
            Child page:  level 2

        Therefore a nested page's parent is the nearest preceding page
        having the highest hierarchy level lower than the current page.

        If Microsoft Graph does not provide trustworthy ordering
        information, Connector fails instead of guessing the hierarchy.

        Microsoft Graph does not reliably update a OneNote Page's
        lastModifiedDateTime when its body content changes. The containing
        Section's lastModifiedDateTime is therefore preserved with every
        Page as connector metadata for downstream synchronization use.
        """

        section = (
            section_context[
                "raw_object"
            ]
        )

        section_path = (
            section_context[
                "object_path"
            ]
        )

        section_id = (
            section.get(
                "id"
            )
        )

        if not section_id:

            raise RuntimeError(
                "OneNote section is missing "
                "its source object ID."
            )

        section_modified_at = (
            section.get(
                "lastModifiedDateTime"
            )
        )

        pages_endpoint = (
            "/me/onenote/sections/"
            f"{section_id}/pages"
            f"?$top={ONENOTE_PAGE_SIZE}"
            "&pagelevel=true"
        )

        pages = self._get_collection(
            pages_endpoint
        )

        if not pages:

            return

        self._validate_onenote_page_levels(
            pages=pages,
            section=section,
        )

        base_level = min(
            page["level"]
            for page in pages
        )

        maximum_level = max(
            page["level"]
            for page in pages
        )

        has_nested_pages = (
            maximum_level > base_level
        )

        if has_nested_pages:

            ordered_pages = (
                self._get_verified_onenote_page_order(
                    pages=pages,
                    section=section,
                )
            )

        else:

            ordered_pages = pages

        hierarchy_stack = {}

        for page in ordered_pages:

            page_id = page.get(
                "id"
            )

            if not page_id:

                raise RuntimeError(
                    "OneNote page is missing "
                    "its source object ID."
                )

            page_name = (
                self._get_onenote_name(
                    page,
                    "page",
                )
            )

            page_level = (
                page["level"]
                - base_level
            )

            # ================================================================
            # Top-level page
            # ================================================================

            if page_level == 0:

                parent_object_id = (
                    section_id
                )

                parent_path = (
                    section_path
                )

            # ================================================================
            # Nested page
            # ================================================================

            else:

                lower_levels = [
                    level
                    for level
                    in hierarchy_stack
                    if level < page_level
                ]

                if not lower_levels:

                    raise RuntimeError(
                        "OneNote page hierarchy could "
                        "not be proven. "
                        f"Page '{page_name}' reports "
                        f"hierarchy level {page_level}, "
                        "but no preceding page exists "
                        "at a lower hierarchy level."
                    )

                parent_level = max(
                    lower_levels
                )

                parent_context = (
                    hierarchy_stack[
                        parent_level
                    ]
                )

                parent_object_id = (
                    parent_context[
                        "id"
                    ]
                )

                parent_path = (
                    parent_context[
                        "object_path"
                    ]
                )

            page_object_path = (
                self._join_source_path(
                    parent_path,
                    page_name,
                )
            )

            raw_objects.append(
                self._wrap_object(
                    "page",
                    page,
                    connector_metadata={
                        "source_parent_object_id":
                            parent_object_id,

                        "source_path":
                            parent_path,

                        "object_path":
                            page_object_path,

                        "hierarchy_verified":
                            True,

                        "page_level":
                            page.get("level"),

                        "page_order":
                            page.get("order"),

                        "source_section_modified_at":
                            section_modified_at,
                    },
                )
            )

            # ================================================================
            # Update active hierarchy
            # ================================================================

            hierarchy_stack[
                page_level
            ] = {
                "id":
                    page_id,

                "object_path":
                    page_object_path,
            }

            deeper_levels = [
                level
                for level
                in hierarchy_stack
                if level > page_level
            ]

            for level in deeper_levels:

                del hierarchy_stack[
                    level
                ]

    @staticmethod
    def _validate_onenote_page_levels(
        pages,
        section,
    ):
        """
        Verify that pagelevel=true actually returned usable level values.
        """

        for page in pages:

            level = page.get(
                "level"
            )

            if not isinstance(
                level,
                int,
            ):

                raise RuntimeError(
                    "Microsoft Graph did not provide "
                    "a usable OneNote page level for "
                    f"page '{page.get('title')}'. "
                    "The page hierarchy cannot be "
                    "proven."
                )

    @staticmethod
    def _get_verified_onenote_page_order(
        pages,
        section,
    ):
        """
        Return pages sorted by Microsoft Graph order only when the
        ordering data is sufficiently trustworthy to reconstruct nested
        page hierarchy.

        Duplicate or missing order values make the hierarchy ambiguous.
        """

        orders = []

        for page in pages:

            order = page.get(
                "order"
            )

            if not isinstance(
                order,
                int,
            ):

                raise RuntimeError(
                    "Microsoft Graph did not provide "
                    "a usable OneNote page order. "
                    "Nested page hierarchy cannot "
                    "be proven."
                )

            orders.append(
                order
            )

        if (
            len(set(orders))
            != len(orders)
        ):

            section_name = (
                section.get(
                    "displayName"
                )
                or section.get(
                    "name"
                )
                or section.get(
                    "id"
                )
            )

            raise RuntimeError(
                "Microsoft Graph returned duplicate "
                "OneNote page order values for "
                f"section '{section_name}'. "
                "Nested page hierarchy cannot "
                "be reliably reconstructed, so the "
                "Connector will not guess."
            )

        return sorted(
            pages,
            key=lambda page: page["order"],
        )

    # ========================================================================
    # Validation
    # ========================================================================

    @staticmethod
    def _validate_completed_section(
        connector_section,
    ):
        """
        Validate Connector-owned output before stage completion.
        """

        if (
            not connector_section
            .connection_succeeded
        ):

            raise RuntimeError(
                "Connector did not complete "
                "successfully."
            )

        if not isinstance(
            connector_section.raw_objects,
            list,
        ):

            raise TypeError(
                "Connector raw_objects "
                "must be a list."
            )

        if not isinstance(
            connector_section.raw_metadata,
            dict,
        ):

            raise TypeError(
                "Connector raw_metadata "
                "must be a dictionary."
            )

        if (
            connector_section
            .raw_metadata
            .get(
                "enumeration_complete"
            )
            is not True
        ):

            raise RuntimeError(
                "Connector synchronization scope "
                "was not completely enumerated."
            )

        for connector_object in (
            connector_section.raw_objects
        ):

            if (
                "source_object_type"
                not in connector_object
            ):

                raise RuntimeError(
                    "Connector object is missing "
                    "source_object_type."
                )

            if (
                "raw_object"
                not in connector_object
            ):

                raise RuntimeError(
                    "Connector object is missing "
                    "raw_object."
                )

            if (
                "connector_metadata"
                not in connector_object
            ):

                raise RuntimeError(
                    "Connector object is missing "
                    "connector_metadata."
                )

        if (
            connector_section.source_name
            == ONEDRIVE
        ):

            if not (
                connector_section
                .raw_metadata
                .get(
                    "delta_link"
                )
            ):

                raise RuntimeError(
                    "Completed OneDrive Connector "
                    "output is missing its "
                    "deltaLink."
                )