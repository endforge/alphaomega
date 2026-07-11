from msal import PublicClientApplication
import requests

CLIENT_ID = "1ec08875-5201-4c26-8b61-97c0916e0885"

FOLDER_ID = "70EE5AA1D6A4DA1F!72650"

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

response = requests.get(
	f"https://graph.microsoft.com/v1.0/me/drive/items/{FOLDER_ID}/children",
	headers=headers
)

data = response.json()

for item in data.get("value", []):
	item_type = "Folder" if "folder" in item else "File"
	print(f"{item_type}: {item['name']}")
	print(f"ID: {item['id']}")
print()