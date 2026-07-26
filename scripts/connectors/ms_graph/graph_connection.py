"""
Microsoft Graph connection for AlphaOmega.

Responsibilities:
    - Authenticate with Microsoft Graph.
    - Maintain an authenticated session.
    - Execute HTTP GET requests.
    - Return the raw HTTP response.

This module does NOT:
    - Know about OneNote notebooks.
    - Know about sections.
    - Know about pages.
    - Parse JSON.
    - Extract HTML.
    - Save data.
"""

import requests

from msal import PublicClientApplication

from config.settings import GRAPH_CLIENT_ID


# ============================================================================
# Configuration - Uses SCOPES for both OneNote and OneDrive
# ============================================================================

AUTHORITY = "https://login.microsoftonline.com/common"

SCOPES = [
    "User.Read",
    "Notes.Read",
    "Files.Read",
]

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


# ============================================================================
# Private State
# ============================================================================

_app = None
_access_token = None


# ============================================================================
# Private Functions
# ============================================================================

def _get_msal_application():
    """
    Create the MSAL application the first time it is needed.

    The application object is reused for the lifetime of the program.
    """

    global _app

    if _app is None:
        _app = PublicClientApplication(
            client_id=GRAPH_CLIENT_ID,
            authority=AUTHORITY,
        )

    return _app


def _get_access_token():
    """
    Return a valid Microsoft Graph access token.

    If a token has already been obtained during this execution,
    reuse it.

    Otherwise authenticate the user and obtain one.
    """

    global _access_token

    if _access_token is not None:
        return _access_token

    app = _get_msal_application()

    result = app.acquire_token_interactive(
        scopes=SCOPES
    )

    if "access_token" not in result:
        raise RuntimeError(
            f"Authentication failed:\n{result}"
        )

    _access_token = result["access_token"]

    return _access_token


def _build_headers():
    """
    Build the Authorization header for Microsoft Graph.
    """

    token = _get_access_token()

    return {
        "Authorization": f"Bearer {token}"
    }


def _graph_request(method, endpoint):
    """
    Execute an HTTP request against Microsoft Graph.

    Parameters
    ----------
    method : str
        HTTP method (GET, POST, PATCH, DELETE)

    endpoint : str
        Microsoft Graph endpoint beginning with "/"

    Returns
    -------
    requests.Response
    """

    url = f"{GRAPH_BASE_URL}{endpoint}"

    headers = _build_headers()

    response = requests.request(
        method=method,
        url=url,
        headers=headers,
    )

    response.raise_for_status()

    return response


# ============================================================================
# Public Functions
# ============================================================================

def graph_get(endpoint):
    """
    Execute an HTTP GET request against Microsoft Graph.
    """

    return _graph_request("GET", endpoint)

