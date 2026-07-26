import os
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE = Path(__file__).parent / ".env"

load_dotenv(ENV_FILE)


def get_required_setting(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Required configuration setting '{name}' was not found."
        )

    return value


GRAPH_CLIENT_ID = get_required_setting("ALPHAOMEGA_CLIENT_ID")