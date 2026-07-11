from msal import PublicClientApplication
import requests
import os
import json

CLIENT_ID = "1ec08875-5201-4c26-8b61-97c0916e0885"
ROOT_FOLDER_ID = "70EE5AA1D6A4DA1F!72650"

SUPPORTED_EXTENSIONS = [
    ".pdf",
    ".txt",
    ".docx",
    ".doc",
    ".xlsx",
    ".csv",
    ".md",
    ".rtf",
    ".html",
    ".pptx"
]

supported_files = []

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


def scan_folder(folder_id, current_path="Mimics Tavern"):
    response = requests.get(
        f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children",
        headers=headers
    )

    data = response.json()

    for item in data.get("value", []):

        if "folder" in item:

            next_path = f"{current_path}/{item['name']}"
            scan_folder(item["id"], next_path)

        else:
            file_name = item["name"]
            extension = os.path.splitext(file_name)[1].lower()

            if extension in SUPPORTED_EXTENSIONS:

                supported_files.append({
                    "name": file_name,
                    "id": item["id"],
                    "extension": extension,
                    "path": f"{current_path}/{file_name}",
                    "size": item.get("size", 0),
                    "last_modified": item.get("lastModifiedDateTime", "")
                })

scan_folder(ROOT_FOLDER_ID)

with open("data/manifest/supported_files.json", "w", encoding="utf-8") as file:
    json.dump(supported_files, file, indent=4)

print(f"Manifest created.")
print(f"Supported files found: {len(supported_files)}")