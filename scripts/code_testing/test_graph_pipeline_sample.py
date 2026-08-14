"""
File: test_graph_pipeline_sample.py

Purpose:
    Deterministic Connector -> Translator regression test using small,
    known Microsoft Graph datasets.

OneDrive target:
    Writings and every descendant beneath Writings.

OneNote targets:
    Games -> Minecraft
    Mimic's Tavern -> Homebrew

The OneNote targets deliberately exercise multiple hierarchy patterns:

    Standard contiguous hierarchy:
        My World Realms - Hoesing and Park     level 0
            Blueprints                         level 1
            Storage Build                      level 1
            Coordinates                        level 1
            Super GreenHouse Tower             level 1

    Non-contiguous hierarchy:
        Selune Armor                            level 0
            Armor                               level 2

The test validates:
    - Retrieval completeness within the selected test scope.
    - Names.
    - Canonical object types.
    - Source object IDs.
    - Immediate parent IDs.
    - Source hierarchy paths.
    - Created/modified timestamps.
    - Blank OneNote page titles become Untitled.
    - Standard OneNote child-page relationships.
    - Non-contiguous OneNote child-page relationships.
    - Deep OneDrive traversal.
"""

from collections import Counter
from pprint import pprint

from scripts.connectors.ms_graph.graph_connector import (
    GraphConnector,
)
from scripts.connectors.connector_section import (
    ConnectorSection,
)
from scripts.translator.graph_translator import (
    GraphTranslator,
)


ONEDRIVE_TEST_FOLDER = "Writings"

GAMES_NOTEBOOK = "Games"
GAMES_SECTION = "Minecraft"

MIMICS_TAVERN_NOTEBOOK = "Mimic's Tavern"
MIMICS_TAVERN_SECTION = "Homebrew"


# ============================================================================
# Shared Helpers
# ============================================================================

def build_connector_section(
    source_name,
    connector_objects,
):
    """
    Build a ConnectorSection for Translator testing.
    """

    section = ConnectorSection(
        source_name
    )

    section.connection_succeeded = True

    section.raw_objects = (
        connector_objects
    )

    section.raw_metadata = {
        "enumeration_complete":
            True,

        "test_mode":
            True,

        "objects_retrieved":
            len(connector_objects),
    }

    section.lock()

    return section


def expected_name(
    source_object_type,
    raw_object,
):
    """
    Determine expected canonical name.
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

    return (
        raw_object.get(
            "displayName"
        )
        or raw_object.get(
            "name"
        )
    )


def expected_type(
    source_object_type,
    raw_object,
):
    """
    Determine expected canonical object type.
    """

    if source_object_type in (
        "notebook",
        "sectionGroup",
        "section",
        "driveRoot",
    ):

        return "CONTAINER"

    if source_object_type == "page":

        return "CONTENT"

    if source_object_type == "driveItem":

        if "folder" in raw_object:

            return "CONTAINER"

        return "CONTENT"

    return None


def find_exact_object(
    objects,
    field_name,
    field_value,
    description,
):
    """
    Find exactly one source object using a known field value.
    """

    matches = [
        item
        for item in objects
        if item.get(
            field_name
        ) == field_value
    ]

    if len(matches) != 1:

        raise RuntimeError(
            f"Expected exactly one {description} "
            f"named '{field_value}'. "
            f"Found {len(matches)}."
        )

    return matches[0]


# ============================================================================
# OneDrive Sample Retrieval
# ============================================================================

def get_onedrive_sample(
    connector,
):
    """
    Retrieve Writings and recursively retrieve every descendant.
    """

    root_children = (
        connector._get_collection(
            "/me/drive/root/children"
        )
    )

    writings_matches = [
        item
        for item in root_children
        if (
            item.get("name")
            == ONEDRIVE_TEST_FOLDER
            and "folder"
            in item
        )
    ]

    if len(writings_matches) != 1:

        raise RuntimeError(
            "Expected exactly one OneDrive "
            "Writings folder."
        )

    raw_objects = []

    def crawl(
        item,
    ):
        """
        Recursively crawl every descendant of Writings.
        """

        raw_objects.append(
            connector._wrap_object(
                "driveItem",
                item,
            )
        )

        if "folder" not in item:

            return

        item_id = item.get(
            "id"
        )

        if not item_id:

            raise RuntimeError(
                "OneDrive folder is missing "
                "its object ID."
            )

        children = (
            connector._get_collection(
                "/me/drive/items/"
                f"{item_id}/children"
            )
        )

        for child in children:

            crawl(
                child
            )

    crawl(
        writings_matches[0]
    )

    return build_connector_section(
        "onedrive",
        raw_objects,
    )


# ============================================================================
# OneNote Sample Retrieval Helpers
# ============================================================================

def get_onenote_notebook(
    connector,
    notebook_name,
):
    """
    Retrieve one exact OneNote notebook including its sections and
    section groups.
    """

    notebooks = (
        connector._get_collection(
            "/me/onenote/notebooks"
            "?$expand=sections,"
            "sectionGroups($expand=sections)"
        )
    )

    return find_exact_object(
        notebooks,
        "displayName",
        notebook_name,
        "OneNote notebook",
    )


def add_notebook(
    connector,
    notebook,
    raw_objects,
    sections,
    section_ids,
    section_group_ids,
    only_section_name=None,
):
    """
    Add a notebook and selected section hierarchy using the same
    production Connector hierarchy functions.

    only_section_name limits this deterministic test to a known small
    section when supplied.
    """

    notebook_id = (
        notebook.get(
            "id"
        )
    )

    notebook_name = (
        notebook.get(
            "displayName"
        )
    )

    if not notebook_id:

        raise RuntimeError(
            f"Notebook '{notebook_name}' "
            "is missing its ID."
        )

    raw_objects.append(
        connector._wrap_object(
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

    if only_section_name is not None:

        notebook_sections = [
            section
            for section
            in notebook_sections
            if section.get(
                "displayName"
            ) == only_section_name
        ]

        if len(notebook_sections) != 1:

            raise RuntimeError(
                f"Expected exactly one section "
                f"'{only_section_name}' in notebook "
                f"'{notebook_name}'. "
                f"Found {len(notebook_sections)}."
            )

    for section in notebook_sections:

        connector._add_onenote_section(
            section=section,
            raw_objects=raw_objects,
            sections=sections,
            section_ids=section_ids,
            parent_object_id=(
                notebook_id
            ),
            parent_path=(
                notebook_name
            ),
        )

    #
    # Section groups are retained when the entire notebook is requested.
    # The two current regression targets are direct notebook sections,
    # so section groups are not needed when only_section_name is supplied.
    #

    if only_section_name is None:

        for section_group in notebook.get(
            "sectionGroups",
            [],
        ):

            connector._add_onenote_section_group(
                section_group=(
                    section_group
                ),
                raw_objects=raw_objects,
                sections=sections,
                section_ids=section_ids,
                section_group_ids=(
                    section_group_ids
                ),
                parent_object_id=(
                    notebook_id
                ),
                parent_path=(
                    notebook_name
                ),
            )


def get_onenote_sample(
    connector,
):
    """
    Retrieve two known OneNote regression datasets.

    1. Games -> Minecraft
       Tests normal level 0 -> level 1 hierarchy.

    2. Mimic's Tavern -> Homebrew
       Tests the known level 0 -> level 2 hierarchy involving
       Selune Armor -> Armor.
    """

    raw_objects = []

    sections = []

    section_ids = set()
    section_group_ids = set()

    # ------------------------------------------------------------------------
    # Games -> Minecraft
    # ------------------------------------------------------------------------

    games_notebook = (
        get_onenote_notebook(
            connector,
            GAMES_NOTEBOOK,
        )
    )

    add_notebook(
        connector=connector,
        notebook=games_notebook,
        raw_objects=raw_objects,
        sections=sections,
        section_ids=section_ids,
        section_group_ids=(
            section_group_ids
        ),
        only_section_name=(
            GAMES_SECTION
        ),
    )

    # ------------------------------------------------------------------------
    # Mimic's Tavern -> Homebrew
    # ------------------------------------------------------------------------

    mimics_notebook = (
        get_onenote_notebook(
            connector,
            MIMICS_TAVERN_NOTEBOOK,
        )
    )

    add_notebook(
        connector=connector,
        notebook=mimics_notebook,
        raw_objects=raw_objects,
        sections=sections,
        section_ids=section_ids,
        section_group_ids=(
            section_group_ids
        ),
        only_section_name=(
            MIMICS_TAVERN_SECTION
        ),
    )

    # ------------------------------------------------------------------------
    # Retrieve pages using production hierarchy logic
    # ------------------------------------------------------------------------

    for section_context in sections:

        connector._enumerate_onenote_section_pages(
            section_context=(
                section_context
            ),
            raw_objects=(
                raw_objects
            ),
        )

    return build_connector_section(
        "onenote",
        raw_objects,
    )


# ============================================================================
# General Pipeline Validation
# ============================================================================

def validate_pipeline(
    source_name,
    connector_section,
):
    """
    Translate every Connector object and compare canonical values against
    the raw source data and Connector-derived hierarchy.
    """

    translator = GraphTranslator()

    translator_section = (
        translator.run(
            connector_section
        )
    )

    failures = []

    translated_by_id = {
        record.source_object_id:
            record
        for record
        in translator_section.translated_records
    }

    # ------------------------------------------------------------------------
    # Record accounting
    # ------------------------------------------------------------------------

    if (
        len(
            translator_section.translated_records
        )
        + len(
            translator_section.record_errors
        )
        != len(
            connector_section.raw_objects
        )
    ):

        failures.append(
            {
                "object":
                    source_name,

                "field":
                    "record_accounting",

                "expected":
                    len(
                        connector_section.raw_objects
                    ),

                "actual":
                    (
                        len(
                            translator_section
                            .translated_records
                        )
                        + len(
                            translator_section
                            .record_errors
                        )
                    ),
            }
        )

    # ------------------------------------------------------------------------
    # Validate every object
    # ------------------------------------------------------------------------

    for connector_object in (
        connector_section.raw_objects
    ):

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

        object_id = raw_object.get(
            "id"
        )

        name = expected_name(
            source_object_type,
            raw_object,
        )

        record = (
            translated_by_id.get(
                object_id
            )
        )

        if record is None:

            failures.append(
                {
                    "object":
                        name,

                    "field":
                        "translated_record",

                    "expected":
                        "present",

                    "actual":
                        "missing",
                }
            )

            continue

        comparisons = {
            "name":
                (
                    name,
                    record.name,
                ),

            "object_type":
                (
                    expected_type(
                        source_object_type,
                        raw_object,
                    ),
                    record.object_type,
                ),

            "source_object_id":
                (
                    object_id,
                    record.source_object_id,
                ),

            "source_created_at":
                (
                    raw_object.get(
                        "createdDateTime"
                    ),
                    record.source_created_at,
                ),

            "source_modified_at":
                (
                    raw_object.get(
                        "lastModifiedDateTime"
                    ),
                    record.source_modified_at,
                ),
        }

        if (
            "source_parent_object_id"
            in connector_metadata
        ):

            comparisons[
                "source_parent_object_id"
            ] = (
                connector_metadata.get(
                    "source_parent_object_id"
                ),
                record.source_parent_object_id,
            )

        elif source_name == "onedrive":

            parent_reference = (
                raw_object.get(
                    "parentReference"
                )
                or {}
            )

            comparisons[
                "source_parent_object_id"
            ] = (
                parent_reference.get(
                    "id"
                ),
                record.source_parent_object_id,
            )

        if (
            "source_path"
            in connector_metadata
        ):

            comparisons[
                "source_path"
            ] = (
                connector_metadata.get(
                    "source_path"
                ),
                record.source_path,
            )

        for (
            field_name,
            values,
        ) in comparisons.items():

            expected_value = (
                values[0]
            )

            actual_value = (
                values[1]
            )

            if (
                expected_value
                != actual_value
            ):

                failures.append(
                    {
                        "object":
                            name,

                        "object_id":
                            object_id,

                        "field":
                            field_name,

                        "expected":
                            expected_value,

                        "actual":
                            actual_value,
                    }
                )

    return (
        translator_section,
        failures,
    )


# ============================================================================
# Known OneNote Regression Validation
# ============================================================================

def get_unique_record(
    translator_section,
    name,
):
    """
    Return exactly one translated record having the requested name.

    Used only for known deterministic regression objects whose names are
    unique within the selected sample.
    """

    matches = [
        record
        for record
        in translator_section.translated_records
        if record.name == name
    ]

    if len(matches) != 1:

        return (
            None,
            {
                "object":
                    name,

                "field":
                    "baseline_lookup",

                "expected":
                    "exactly one translated record",

                "actual":
                    len(matches),
            },
        )

    return (
        matches[0],
        None,
    )


def validate_games_hierarchy(
    translator_section,
):
    """
    Validate the known Games -> Minecraft hierarchy.

    This proves the normal contiguous level 0 -> level 1 case.
    """

    failures = []

    parent_page, error = (
        get_unique_record(
            translator_section,
            "My World Realms - Hoesing and Park",
        )
    )

    if error:

        failures.append(
            error
        )

        return failures

    expected_children = (
        "Blueprints",
        "Storage Build",
        "Coordinates",
        "Super GreenHouse Tower",
    )

    expected_path = (
        "Games/Minecraft/"
        "My World Realms - Hoesing and Park"
    )

    for child_name in expected_children:

        child, error = (
            get_unique_record(
                translator_section,
                child_name,
            )
        )

        if error:

            failures.append(
                error
            )

            continue

        if (
            child.source_parent_object_id
            != parent_page.source_object_id
        ):

            failures.append(
                {
                    "object":
                        child_name,

                    "field":
                        "source_parent_object_id",

                    "expected":
                        parent_page.source_object_id,

                    "actual":
                        child.source_parent_object_id,
                }
            )

        if (
            child.source_path
            != expected_path
        ):

            failures.append(
                {
                    "object":
                        child_name,

                    "field":
                        "source_path",

                    "expected":
                        expected_path,

                    "actual":
                        child.source_path,
                }
            )

    return failures


def validate_non_contiguous_hierarchy(
    translator_section,
):
    """
    Validate the known Mimic's Tavern hierarchy:

        Homebrew
            Selune Armor       level 0
                Armor          level 2

    This is the regression case that exposed the original hierarchy bug.

    The old hierarchy algorithm required level - 1 to exist and therefore
    could not resolve Armor.

    The corrected algorithm must identify Selune Armor as Armor's parent
    because it is the nearest preceding page at a lower hierarchy level.
    """

    failures = []

    parent_page, error = (
        get_unique_record(
            translator_section,
            "Selune Armor",
        )
    )

    if error:

        failures.append(
            error
        )

        return failures

    child_page, error = (
        get_unique_record(
            translator_section,
            "Armor",
        )
    )

    if error:

        failures.append(
            error
        )

        return failures

    # ------------------------------------------------------------------------
    # Parent relationship
    # ------------------------------------------------------------------------

    if (
        child_page.source_parent_object_id
        != parent_page.source_object_id
    ):

        failures.append(
            {
                "object":
                    "Armor",

                "field":
                    "source_parent_object_id",

                "expected":
                    parent_page.source_object_id,

                "actual":
                    child_page.source_parent_object_id,
            }
        )

    # ------------------------------------------------------------------------
    # Source path
    # ------------------------------------------------------------------------

    expected_path = (
        "Mimic's Tavern/"
        "Homebrew/"
        "Selune Armor"
    )

    if (
        child_page.source_path
        != expected_path
    ):

        failures.append(
            {
                "object":
                    "Armor",

                "field":
                    "source_path",

                "expected":
                    expected_path,

                "actual":
                    child_page.source_path,
            }
        )

    # ------------------------------------------------------------------------
    # Verify the exact Graph hierarchy levels that make this a meaningful
    # regression test.
    # ------------------------------------------------------------------------

    parent_hierarchy = (
        parent_page.metadata.get(
            "connector_hierarchy",
            {},
        )
    )

    child_hierarchy = (
        child_page.metadata.get(
            "connector_hierarchy",
            {},
        )
    )

    parent_level = (
        parent_hierarchy.get(
            "page_level"
        )
    )

    child_level = (
        child_hierarchy.get(
            "page_level"
        )
    )

    if parent_level != 0:

        failures.append(
            {
                "object":
                    "Selune Armor",

                "field":
                    "page_level",

                "expected":
                    0,

                "actual":
                    parent_level,
            }
        )

    if child_level != 2:

        failures.append(
            {
                "object":
                    "Armor",

                "field":
                    "page_level",

                "expected":
                    2,

                "actual":
                    child_level,
            }
        )

    # ------------------------------------------------------------------------
    # Verify source ordering.
    # ------------------------------------------------------------------------

    parent_order = (
        parent_hierarchy.get(
            "page_order"
        )
    )

    child_order = (
        child_hierarchy.get(
            "page_order"
        )
    )

    if (
        isinstance(
            parent_order,
            int,
        )
        and isinstance(
            child_order,
            int,
        )
    ):

        if child_order <= parent_order:

            failures.append(
                {
                    "object":
                        "Armor",

                    "field":
                        "page_order",

                    "expected":
                        (
                            "greater than Selune "
                            "Armor page order"
                        ),

                    "actual":
                        child_order,
                }
            )

    else:

        failures.append(
            {
                "object":
                    "Armor",

                "field":
                    "page_order",

                "expected":
                    "integer ordering values",

                "actual":
                    {
                        "Selune Armor":
                            parent_order,

                        "Armor":
                            child_order,
                    },
            }
        )

    return failures


def validate_untitled_pages(
    translator_section,
):
    """
    Verify that the Games sample still contains valid Untitled pages and
    that they were normalized correctly.
    """

    failures = []

    untitled_records = [
        record
        for record
        in translator_section.translated_records
        if record.name == "Untitled"
    ]

    if len(untitled_records) < 1:

        failures.append(
            {
                "object":
                    "Untitled",

                "field":
                    "blank_title_normalization",

                "expected":
                    "at least one Untitled page",

                "actual":
                    len(untitled_records),
            }
        )

    return failures


# ============================================================================
# Reporting
# ============================================================================

def print_inventory(
    label,
    connector_section,
):
    """
    Print concise Connector inventory.
    """

    print()
    print("=" * 78)
    print(
        f"{label} CONNECTOR INVENTORY"
    )
    print("=" * 78)

    counts = Counter()

    for connector_object in (
        connector_section.raw_objects
    ):

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

        counts[
            source_object_type
        ] += 1

        print(
            f"{source_object_type:<12} | "
            f"{str(expected_name(source_object_type, raw_object))}"
        )

    print()

    print(
        f"Total objects: "
        f"{len(connector_section.raw_objects)}"
    )

    print(
        f"Types: {dict(counts)}"
    )


def print_translator_output(
    label,
    translator_section,
):
    """
    Print canonical Translator fields needed for inspection.
    """

    print()
    print("=" * 78)
    print(
        f"{label} TRANSLATOR OUTPUT"
    )
    print("=" * 78)

    for record in (
        translator_section.translated_records
    ):

        pprint(
            {
                "name":
                    record.name,

                "object_type":
                    record.object_type,

                "source_name":
                    record.source_name,

                "source_object_id":
                    record.source_object_id,

                "source_parent_object_id":
                    record.source_parent_object_id,

                "source_created_at":
                    record.source_created_at,

                "source_modified_at":
                    record.source_modified_at,

                "source_path":
                    record.source_path,

                "source_url":
                    record.source_url,
            },
            sort_dicts=False,
        )

        print(
            "-" * 78
        )


def print_result(
    label,
    failures,
):
    """
    Print exact validation outcome.
    """

    print()
    print("=" * 78)
    print(
        f"{label} VALIDATION"
    )
    print("=" * 78)

    if not failures:

        print(
            f"{label}: PASS"
        )

        return True

    print(
        f"{label}: FAIL"
    )

    print(
        f"Failures: {len(failures)}"
    )

    for failure in failures:

        print(
            "-" * 78
        )

        pprint(
            failure,
            sort_dicts=False,
        )

    return False


# ============================================================================
# Main
# ============================================================================

def main():

    connector = GraphConnector()

    print()
    print("=" * 78)
    print(
        "Microsoft Graph Connector -> Translator "
        "Deterministic Regression Validation"
    )
    print("=" * 78)

    onedrive_pass = False
    onenote_pass = False

    # ========================================================================
    # OneDrive
    # ========================================================================

    try:

        onedrive_section = (
            get_onedrive_sample(
                connector
            )
        )

        print_inventory(
            "ONEDRIVE WRITINGS",
            onedrive_section,
        )

        (
            onedrive_translator,
            onedrive_failures,
        ) = validate_pipeline(
            "onedrive",
            onedrive_section,
        )

        print_translator_output(
            "ONEDRIVE WRITINGS",
            onedrive_translator,
        )

        onedrive_pass = print_result(
            "ONEDRIVE WRITINGS",
            onedrive_failures,
        )

    except Exception as error:

        print()
        print(
            "ONEDRIVE WRITINGS: FAIL"
        )

        print(
            f"{error.__class__.__name__}: "
            f"{error}"
        )

    # ========================================================================
    # OneNote
    # ========================================================================

    try:

        onenote_section = (
            get_onenote_sample(
                connector
            )
        )

        print_inventory(
            "ONENOTE REGRESSION SAMPLE",
            onenote_section,
        )

        (
            onenote_translator,
            onenote_failures,
        ) = validate_pipeline(
            "onenote",
            onenote_section,
        )

        # --------------------------------------------------------------------
        # Known hierarchy regression cases
        # --------------------------------------------------------------------

        onenote_failures.extend(
            validate_games_hierarchy(
                onenote_translator
            )
        )

        onenote_failures.extend(
            validate_non_contiguous_hierarchy(
                onenote_translator
            )
        )

        onenote_failures.extend(
            validate_untitled_pages(
                onenote_translator
            )
        )

        print_translator_output(
            "ONENOTE REGRESSION SAMPLE",
            onenote_translator,
        )

        onenote_pass = print_result(
            "ONENOTE REGRESSION SAMPLE",
            onenote_failures,
        )

    except Exception as error:

        print()
        print(
            "ONENOTE REGRESSION SAMPLE: FAIL"
        )

        print(
            f"{error.__class__.__name__}: "
            f"{error}"
        )

    # ========================================================================
    # Final Result
    # ========================================================================

    print()
    print("=" * 78)
    print("FINAL RESULT")
    print("=" * 78)

    print(
        f"OneDrive Writings : "
        f"{'PASS' if onedrive_pass else 'FAIL'}"
    )

    print(
        f"OneNote Regression: "
        f"{'PASS' if onenote_pass else 'FAIL'}"
    )

    if (
        onedrive_pass
        and onenote_pass
    ):

        print()
        print(
            "Connector -> Translator "
            "deterministic regression validation: PASS"
        )

    else:

        print()
        print(
            "Connector -> Translator "
            "deterministic regression validation: FAIL"
        )


if __name__ == "__main__":

    main()