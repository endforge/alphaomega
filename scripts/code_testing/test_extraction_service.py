"""
File: test_extraction_service.py

Purpose:
    Verify ExtractionService behavior without making live
    source-system requests.

Tests:
    - OneDrive extraction flow.
    - OneNote extraction flow.
    - Record-level failure isolation.
    - Invalid record input handling.
    - Stage-level failure handling.
    - ExtractionSection locking.
"""

from types import SimpleNamespace
from unittest.mock import Mock

from scripts.extraction.extraction_service import (
    ExtractionService,
)
from scripts.sync.sync_exceptions import (
    ExtractionError,
)


def build_input(
    source_name,
    source_object_id,
    object_type,
    name,
):
    """
    Build a simple orchestration-supplied Extraction input.
    """

    return SimpleNamespace(
        source_name=source_name,
        source_object_id=source_object_id,
        object_type=object_type,
        name=name,
    )


def test_onedrive_extraction():
    """
    Verify OneDrive content is retrieved, extracted, hashed,
    and returned as an ExtractionRecord.
    """

    onedrive_retriever = Mock()
    onedrive_retriever.retrieve.return_value = (
        b"AlphaOmega OneDrive content"
    )

    router = Mock()
    router.get_retriever.return_value = (
        onedrive_retriever
    )

    service = ExtractionService(
        retriever_router=router,
    )

    extraction_input = build_input(
        source_name="OneDrive",
        source_object_id="drive-123",
        object_type="CONTENT",
        name="notes.txt",
    )

    section = service.run(
        [extraction_input]
    )

    assert section.extraction_succeeded is True
    assert section.is_locked is True
    assert len(section.extraction_records) == 1
    assert len(section.record_errors) == 0

    record = section.extraction_records[0]

    assert (
        record.canonical_content
        == "AlphaOmega OneDrive content"
    )

    assert len(record.content_hash) == 64

    assert (
        record.extractor_name
        == "text_extractor"
    )

    assert (
        record.canonical_metadata[
            "content_length"
        ]
        == len(
            "AlphaOmega OneDrive content"
        )
    )

    assert record.extraction_timestamp is not None

    router.get_retriever.assert_called_once_with(
        "OneDrive"
    )

    onedrive_retriever.retrieve.assert_called_once_with(
        "drive-123"
    )

    print(
        "PASS: OneDrive ExtractionService flow correct."
    )


def test_onenote_extraction():
    """
    Verify OneNote HTML retrieval is routed through
    the HTML extractor.
    """

    onenote_retriever = Mock()
    onenote_retriever.retrieve.return_value = (
        b"<html><body><p>OneNote content</p></body></html>"
    )

    router = Mock()
    router.get_retriever.return_value = (
        onenote_retriever
    )

    service = ExtractionService(
        retriever_router=router,
    )

    extraction_input = build_input(
        source_name="OneNote",
        source_object_id="page-456",
        object_type="page",
        name="Bogmire Notes",
    )

    section = service.run(
        [extraction_input]
    )

    assert section.extraction_succeeded is True
    assert section.is_locked is True
    assert len(section.extraction_records) == 1
    assert len(section.record_errors) == 0

    record = section.extraction_records[0]

    assert (
        "OneNote content"
        in record.canonical_content
    )

    assert len(record.content_hash) == 64

    onenote_retriever.retrieve.assert_called_once_with(
        source_object_id="page-456",
        object_type="page",
    )

    print(
        "PASS: OneNote ExtractionService flow correct."
    )


def test_record_failure_continues_batch():
    """
    Verify one source-object failure becomes an
    ExtractionRecordError and does not stop the batch.
    """

    good_retriever = Mock()
    good_retriever.retrieve.return_value = (
        b"Good content"
    )

    bad_retriever = Mock()
    bad_retriever.retrieve.side_effect = (
        RuntimeError(
            "Synthetic retrieval failure."
        )
    )

    router = Mock()

    router.get_retriever.side_effect = [
        good_retriever,
        bad_retriever,
        good_retriever,
    ]

    service = ExtractionService(
        retriever_router=router,
    )

    inputs = [
        build_input(
            "OneDrive",
            "object-a",
            "CONTENT",
            "a.txt",
        ),
        build_input(
            "OneDrive",
            "object-b",
            "CONTENT",
            "b.txt",
        ),
        build_input(
            "OneDrive",
            "object-c",
            "CONTENT",
            "c.txt",
        ),
    ]

    section = service.run(
        inputs
    )

    assert section.extraction_succeeded is True
    assert len(section.extraction_records) == 2
    assert len(section.record_errors) == 1

    error = section.record_errors[0]

    assert (
        error["source_object_id"]
        == "object-b"
    )

    assert (
        error["error_type"]
        == "ExtractionRecordError"
    )

    assert (
        "Synthetic retrieval failure."
        in error["message"]
    )

    print(
        "PASS: ExtractionRecordError isolated "
        "and batch continued."
    )


def test_missing_required_record_input():
    """
    Verify invalid input for one source object becomes
    an ExtractionRecordError rather than terminating
    the entire stage.
    """

    service = ExtractionService()

    extraction_input = build_input(
        source_name="OneDrive",
        source_object_id=None,
        object_type="CONTENT",
        name="bad.txt",
    )

    section = service.run(
        [extraction_input]
    )

    assert section.extraction_succeeded is True
    assert len(section.extraction_records) == 0
    assert len(section.record_errors) == 1

    error = section.record_errors[0]

    assert (
        error["source_object_id"]
        is None
    )

    assert (
        error["error_type"]
        == "ExtractionRecordError"
    )

    assert (
        "source_object_id"
        in error["message"]
    )

    print(
        "PASS: Invalid source-object input captured "
        "as ExtractionRecordError."
    )


def test_missing_batch_is_stage_failure():
    """
    Verify missing Extraction batch is a stage-level
    ExtractionError.
    """

    service = ExtractionService()

    try:
        service.run(None)

        raise AssertionError(
            "Missing Extraction batch did not "
            "raise ExtractionError."
        )

    except ExtractionError as error:
        assert (
            str(error)
            == "Extraction input batch is required."
        )

    print(
        "PASS: Missing batch raised ExtractionError."
    )


def test_unexpected_stage_failure():
    """
    Verify an unexpected failure in batch iteration becomes
    a stage-level ExtractionError.
    """

    class BrokenBatch:
        """
        Iterable that fails at the stage/batch level.
        """

        def __iter__(self):
            raise RuntimeError(
                "Synthetic batch failure."
            )

    service = ExtractionService()

    try:
        service.run(
            BrokenBatch()
        )

        raise AssertionError(
            "Unexpected stage failure did not "
            "raise ExtractionError."
        )

    except ExtractionError as error:
        assert (
            str(error)
            == "Extraction stage failed."
        )

        assert isinstance(
            error.__cause__,
            RuntimeError,
        )

        assert (
            str(error.__cause__)
            == "Synthetic batch failure."
        )

    print(
        "PASS: Unexpected stage failure converted "
        "to ExtractionError."
    )


def test_section_locking():
    """
    Verify ExtractionSection remains immutable
    after successful stage completion.
    """

    retriever = Mock()
    retriever.retrieve.return_value = (
        b"Lock test"
    )

    router = Mock()
    router.get_retriever.return_value = (
        retriever
    )

    service = ExtractionService(
        retriever_router=router,
    )

    section = service.run(
        [
            build_input(
                "OneDrive",
                "lock-123",
                "CONTENT",
                "lock.txt",
            )
        ]
    )

    assert section.is_locked is True

    assert isinstance(
        section.extraction_records,
        tuple,
    )

    assert isinstance(
        section.record_errors,
        tuple,
    )

    print(
        "PASS: ExtractionSection locked after completion."
    )


def main():
    """
    Run ExtractionService tests.
    """

    print(
        "\nRunning ExtractionService exception tests...\n"
    )

    test_onedrive_extraction()
    test_onenote_extraction()
    test_record_failure_continues_batch()
    test_missing_required_record_input()
    test_missing_batch_is_stage_failure()
    test_unexpected_stage_failure()
    test_section_locking()

    print(
        "\nExtractionService exception tests PASSED.\n"
    )


if __name__ == "__main__":
    main()