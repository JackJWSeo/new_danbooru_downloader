import requests
from config import TAG_URL, HEADERS

def resolve_artist(name: str) -> str | None:
    try:
        r = requests.get(
            TAG_URL,
            params={
                "search[name_matches]": f"*{name}*",
                "search[category]": 1,
                "limit": 5
            },
            headers=HEADERS,
            timeout=10
        )
        if r.status_code != 200:
            return None

        tags = r.json()
        if not tags:
            return None

        tags.sort(key=lambda t: t.get("post_count", 0), reverse=True)
        return tags[0]["name"]

    except Exception:
        return None
