"""Daily live smoke for iskur_mcp — one fixed probe of the İŞKUR
job portal (health + announcements + cities). Fast GETs only; the
slow search postback is NOT used here.

Run: python tests/smoke_live.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from iskur_mcp import http as H
from iskur_mcp import iskur as I


def main() -> int:
    health = H.health_check()
    print("health:", health)
    assert health["status"] == "ok", health
    items = I.parse_announcements(H.fetch_announcements())
    print(f"announcements: {len(items)}, first={items[0]['title']!r}")
    assert len(items) >= 1
    cities = I.parse_cities(H.fetch_search_page())
    print(f"cities: {len(cities)}")
    assert len(cities) == 81, cities
    print("smoke live: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
