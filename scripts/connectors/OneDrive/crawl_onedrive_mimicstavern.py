from msal import PublicClientApplication
import requests
import os

CLIENT_ID = "1ec08875-5201-4c26-8b61-97c0916e0885"
ROOT_FOLDER_ID = "70EE5AA1D6A4DA1F!72650"

extension_counts = {}
folder_count = 0
file_count = 0

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


def scan_folder(folder_id):
    global folder_count
    global file_count

    response = requests.get(
        f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children",
        headers=headers
    )

    data = response.json()

    for item in data.get("value", []):
        if "folder" in item:
            folder_count += 1
            scan_folder(item["id"])
        else:
            file_count += 1
            file_name = item["name"]
            extension = os.path.splitext(file_name)[1].lower()

            if extension == "":
                extension = "[no extension]"

            extension_counts[extension] = extension_counts.get(extension, 0) + 1


scan_folder(ROOT_FOLDER_ID)

print("Scan complete")
print(f"Folders found: {folder_count}")
print(f"Files found: {file_count}")
print()
print("File types found:")

for extension, count in sorted(extension_counts.items(), key=lambda item: item[1], reverse=True):
    print(f"{extension}: {count}")