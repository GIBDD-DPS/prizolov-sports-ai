#!/usr/bin/env python3
"""Example: Playwright worker posts Pari events to storefront ingest API."""

import json
import os
import sys
import urllib.request

API_BASE = os.getenv("PRIZOLOV_API_BASE", "https://prizolov-sports-dmandreyanov.amvera.io")
INGEST_SECRET = os.getenv("BOOKMAKER_INGEST_SECRET", "")


def post_events(events):
    if not INGEST_SECRET:
        raise SystemExit("Set BOOKMAKER_INGEST_SECRET")
    body = json.dumps({"events": events}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE.rstrip('/')}/api/ingest/bookmaker-events",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Bookmaker-Ingest-Secret": INGEST_SECRET,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


if __name__ == "__main__":
    # TODO: use Playwright to open https://pari.ru/sports/football and extract teams + odds.
    sample = [
        {"home": "Team A", "away": "Team B", "sport": "football", "league": "Pari", "is_live": False},
    ]
    print(post_events(sample))
