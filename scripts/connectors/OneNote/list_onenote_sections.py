from msal import PublicClientApplication
import requests

CLIENT_ID = "1ec08875-5201-4c26-8b61-97c0916e0885"

app = PublicClientApplication(
    CLIENT_ID,
    authority="https://login.microsoftonline.com/common"
)

result = app.acquire_token_interactive(
    scopes=["User.Read", "Notes.Read"]
)

token = result["access_token"]

headers = {
    "Authorization": f"Bearer {token}"
}

response = requests.get(
    "https://graph.microsoft.com/v1.0/me/onenote/sections",
    headers=headers
)

data = response.json()

for section in data.get("value", []):
    print(f"Section: {section['displayName']}")
    print(f"ID: {section['id']}")
    print()