"""
File: graph_translator_mappings.py

Purpose:
    Defines Microsoft Graph-specific mappings used by GraphTranslator.

This module contains knowledge of Microsoft Graph's object structure.
It translates Microsoft-specific representations into AlphaOmega's
canonical synchronization concepts.
"""

from common.object_types import CONTAINER, CONTENT


# ============================================================================
# Microsoft Graph Source Object Types
# ============================================================================

GRAPH_NOTEBOOK = "notebook"
GRAPH_ONENOTE_SECTION = "section"
GRAPH_ONENOTE_PAGE = "page"
GRAPH_DRIVE_ROOT = "driveRoot"
GRAPH_DRIVE_ITEM = "driveItem"


# ============================================================================
# Microsoft Graph Object Type Mappings
# ============================================================================

GRAPH_OBJECT_TYPE_MAPPING = {
    GRAPH_NOTEBOOK: CONTAINER,
    GRAPH_ONENOTE_SECTION: CONTAINER,
    GRAPH_ONENOTE_PAGE: CONTENT,

    GRAPH_DRIVE_ROOT: CONTAINER,
    GRAPH_DRIVE_ITEM: CONTENT,
}


# ============================================================================
# Canonical Field Mappings
# ============================================================================

GRAPH_FIELD_MAPPING = {
    "id": "source_object_id",
    "displayName": "name",
    "name": "name",
    "createdDateTime": "source_created_at",
    "lastModifiedDateTime": "source_modified_at",
    "webUrl": "source_url",
    "parentReference.id": "source_parent_object_id",
    "parentReference.path": "source_path",
}


# ============================================================================
# Reserved Microsoft Graph Fields
# ============================================================================

RESERVED_GRAPH_FIELDS = {
    "id",
    "@odata.type",
    "displayName",
    "name",
    "createdDateTime",
    "lastModifiedDateTime",
    "webUrl",
    "parentReference",
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_canonical_object_type(source_object_type):
    """
    Determine the AlphaOmega canonical object type for a
    Microsoft Graph source object.

    Returns None if the object type is unsupported.
    """

    return GRAPH_OBJECT_TYPE_MAPPING.get(source_object_type)


from collections.abc import Mapping


def get_nested_value(raw_object, field_path):
    """
    Retrieve a value from a Microsoft Graph object using dot notation.

    Example:
        parentReference.id
    """

    value = raw_object

    for field_name in field_path.split("."):

        if not isinstance(value, Mapping):
            return None

        value = value.get(field_name)

        if value is None:
            return None

    return value