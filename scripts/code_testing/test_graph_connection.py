"""
Manual test for the Microsoft Graph connection.

This verifies that AlphaOmega can:
1. Load the Microsoft Graph client configuration.
2. Authenticate through MSAL.
3. Receive an access token.
4. Send an authenticated request to Microsoft Graph.
5. Receive and parse a valid response.
"""

from scripts.connectors.ms_graph.graph_connection import graph_get


def test_graph_connection() -> None:
    """Request the signed-in user's basic Microsoft Graph profile."""

    endpoint = "/me"

    print("Testing Microsoft Graph connection...")

    graph_response = graph_get(endpoint)

    print("Microsoft Graph connection succeeded.")
    print(f"Display name: {graph_response.get('displayName')}")
    print(f"User ID: {graph_response.get('id')}")
    print(f"Email: {graph_response.get('mail')}")


if __name__ == "__main__":
    test_graph_connection()