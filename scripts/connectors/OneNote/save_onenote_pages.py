from msal import PublicClientApplication
import requests
from bs4 import BeautifulSoup
from pathlib import Path

CLIENT_ID = "1ec08875-5201-4c26-8b61-97c0916e0885"

PAGE_ID = "0-01f665c544630c39171529ee7179198c!1-70EE5AA1D6A4DA1F!770044"

app = PublicClientApplication(
    CLIENT_ID,
    authority="https://login.microsoftonline.com/common"
)

result = app.acquire_token_interactive(
    scopes=["User.Read", "Notes.Read"]
)

token = result["access_token"]s

headers = {
    "Authorization": f"Bearer {token}"
}

response = requests.get(
    f"https://graph.microsoft.com/v1.0/me/onenote/pages/{PAGE_ID}/content",
    headers=headers
)

html = response.text

soup = BeautifulSoup(html, "html.parser")

title = soup.title.string if soup.title else "Untitled"
text = soup.get_text(separator="\n", strip=True)

print(f"TITLE: {title}")
print()


OUTPUT_DIR = Path("data/extracted_text")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

output_path = OUTPUT_DIR / "page.txt"

with open(output_path, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Saved {output_path}")