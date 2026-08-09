"""
File: test_graph_translator.py

Purpose:
    Tests the Microsoft Graph Translator stage.
"""

from pprint import pprint

from scripts.connectors.ms_graph.graph_connector import GraphConnector
from scripts.translator.graph_translator import GraphTranslator


# SOURCE = "onenote"
SOURCE = "onedrive"


def print_record(record):
    """
    Pretty-print a TranslatorRecord.
    """

    print("-" * 80)

    pprint(vars(record))


def print_error(error):
    """
    Pretty-print a Translator record error.
    """

    print("-" * 80)

    pprint(error)


def main():

    print("\nTesting Graph Translator...\n")

    #
    # Connector Stage
    #
    print("Running Connector...")

    connector = GraphConnector()

    connector_section = connector.run(SOURCE)

    print(type(connector_section.raw_objects))
    print(connector_section.raw_objects)

    print("Connector completed successfully.\n")

    #
    # Translator Stage
    #
    print("Running Translator...")

    translator = GraphTranslator()

    translator_section = translator.run(
        connector_section
    )

    print("Translator completed successfully.\n")

    print("=" * 80)
    print("TRANSLATED RECORDS")
    print("=" * 80)

    if translator_section.translated_records:

        for record in translator_section.translated_records:
            print_record(record)

    else:

        print("No translated records.")

    print()

    print("=" * 80)
    print("RECORD ERRORS")
    print("=" * 80)

    if translator_section.record_errors:

        for error in translator_section.record_errors:
            print_error(error)

    else:

        print("No record errors.")

    print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(
        f"Translation Successful : "
        f"{translator_section.translation_succeeded}"
    )

    print(
        f"Translated Records     : "
        f"{len(translator_section.translated_records)}"
    )

    print(
        f"Record Errors          : "
        f"{len(translator_section.record_errors)}"
    )

    print()


if __name__ == "__main__":
    main()