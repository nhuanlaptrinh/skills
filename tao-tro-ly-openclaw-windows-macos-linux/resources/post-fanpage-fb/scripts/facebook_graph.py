import os
import re

import requests


GRAPH_API_VERSION = os.getenv("FB_GRAPH_API_VERSION", "v25.0").strip()
if not re.fullmatch(r"v\d+\.\d+", GRAPH_API_VERSION):
    raise ValueError("FB_GRAPH_API_VERSION phải có dạng v25.0")

GRAPH_API_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def graph_url(path: str) -> str:
    return f"{GRAPH_API_BASE_URL}/{path.lstrip('/')}"


def response_error(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"

    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict) and error.get("message"):
        return f"HTTP {response.status_code}: {error['message']}"
    return f"HTTP {response.status_code}"


def resolve_page_id(page_access_token: str) -> str:
    response = requests.get(
        graph_url("me"),
        params={"fields": "id,name", "access_token": page_access_token},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Không tự lấy được Page ID: {response_error(response)}")

    payload = response.json()
    page_id = str(payload.get("id", "")).strip()
    if not page_id:
        raise RuntimeError("Token hợp lệ nhưng API không trả Page ID")
    return page_id
