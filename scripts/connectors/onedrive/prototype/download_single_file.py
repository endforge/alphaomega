from msal import PublicClientApplication
import requests
import json

CLIENT_ID = "1ec08875-5201-4c26-8b61-97c0916e0885"

app = PublicClientApplication(
    CLIENT_ID,
    authority="https://login.microsoftonline.com/common"
)

result = app.acquire_token_interactive(
    scopes=["User.Read", "Files.Read"]
)

token = result["access_token"]

headers = {
    "Authorization": f"Bearer {token}"
}

with open("data/manifest/supported_files.json", "r", encoding="utf-8") as file:
    manifest = json.load(file)

first_file = manifest[0]

print(f"Downloading: {first_file['name']}")

response = requests.get(
    f"https://graph.microsoft.com/v1.0/me/drive/items/{first_file['id']}/content",
    headers=headers
)

with open(
    f"artifacts/test_downloads/{first_file['name']}",
    "wb"
) as file:
    file.write(response.content)

print("Download complete")