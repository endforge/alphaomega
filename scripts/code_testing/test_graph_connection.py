"""
Manual test for the Microsoft Graph connection.

This verifies that AlphaOmega can:
1. Load Microsoft Graph configuration.
2. Authenticate through MSAL.
3. Receive an access token.
4. Send an authenticated request.
5. Receive a valid HTTP response.
6. Parse returned JSON.
"""

from scripts.connectors.ms_graph.graph_connection import graph_get


def test_graph_connection():
    """
    Request the signed-in user's basic Microsoft Graph profile.
    """

    endpoint = "/me"

    print("Testing Microsoft Graph connection...")

    response = graph_get(endpoint)

    data = response.json()

    print("Microsoft Graph connection succeeded.")
    print(f"Display name: {data.get('displayName')}")
    print(f"User ID: {data.get('id')}")
    print(f"Email: {data.get('mail')}")


if __name__ == "__main__":
    test_graph_connection()