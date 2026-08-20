"""
AlphaOmega Knowledge Object Repository

Provides database access to canonical Knowledge Objects.

The repository owns storage-specific operations against the
knowledge_objects table. It does not make synchronization decisions.
"""

from typing import Any, Mapping, Optional

from supabase import Client


class KnowledgeObjectRepository:
    """
    Provide repository access to AlphaOmega Knowledge Objects.
    """

    TABLE_NAME = "knowledge_objects"

    DISCOVERY_FIELDS = (
        "id,"
        "title,"
        "source_parent_object_id,"
        "source_modified_at,"
        "content_hash"
    )

    def __init__(self, client: Client):
        """
        Initialize the Knowledge Object repository.

        Args:
            client:
                Authenticated Supabase client constrained by RLS.
        """

        if client is None:
            raise ValueError(
                "Authenticated Supabase client is required."
            )

        self._client = client

    def find_by_source_identity(
        self,
        source_id: str,
        source_object_id: str,
    ) -> Optional[Mapping[str, Any]]:
        """
        Locate a Knowledge Object using its stable source identity.

        Args:
            source_id:
                AlphaOmega identifier for the Source of Truth.

            source_object_id:
                Unique identifier assigned by the Source of Truth.

        Returns:
            Mapping:
                Stored Knowledge Object facts required by Discovery.

            None:
                No Knowledge Object exists for the supplied source identity.

        Raises:
            ValueError:
                If required source identity is missing.

            RuntimeError:
                If the repository lookup cannot be completed.
        """

        if source_id is None or not str(source_id).strip():
            raise ValueError(
                "source_id is required."
            )

        if source_object_id is None or not str(source_object_id).strip():
            raise ValueError(
                "source_object_id is required."
            )

        try:
            response = (
                self._client
                .table(self.TABLE_NAME)
                .select(self.DISCOVERY_FIELDS)
                .eq("source_id", source_id)
                .eq("source_object_id", source_object_id)
                .limit(2)
                .execute()
            )
        except Exception as error:
            raise RuntimeError(
                "Knowledge Object repository lookup failed."
            ) from error

        records = response.data

        if records is None:
            raise RuntimeError(
                "Knowledge Object repository returned no result data."
            )

        if len(records) == 0:
            return None

        if len(records) > 1:
            raise RuntimeError(
                "Multiple Knowledge Objects were found for the same "
                "source identity."
            )

        return records[0]