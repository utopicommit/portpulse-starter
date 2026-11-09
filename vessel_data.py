"""Fetch and normalize live AIS vessel snapshots from Open Waters.

This module does not depend on Streamlit. Keeping data handling separate makes
it easy to test and eventually reuse with a database or API service.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

API_URL = "https://ais.openwaters.io/v1/vessels"

# Boxes are minLat,minLon,maxLat,maxLon, as documented by Open Waters.
REGIONS = {
    "Rotterdam": {
        "bbox": "51.75,3.70,52.07,4.68",
        "center": (51.91, 4.25),
        "zoom": 9,
    },
    "Hamburg": {
        "bbox": "53.40,9.60,53.75,10.20",
        "center": (53.55, 9.93),
        "zoom": 10,
    },
    "Oslofjord": {
        "bbox": "59.00,10.00,60.00,11.00",
        "center": (59.55, 10.50),
        "zoom": 8,
    },
    "Singapore": {
    "bbox": "1.15,103.55,1.50,104.15",
    "center": (1.30, 103.85),
    "zoom": 10,
    },
    "Karachi": {
    "bbox": "24.65,66.70,25.15,67.35",
    "center": (24.82, 66.99),
    "zoom": 10,
    },
    "Dubai": {
        "bbox": "24.85,54.85,25.50,55.55",
        "center": (25.15, 55.15),
        "zoom": 9,
    },
}


def fetch_snapshot(bbox: str) -> dict[str, Any]:
    """Download last known vessel positions reported in the past 30 minutes.

    A snapshot is NOT a perfect census: coverage, reporting frequency, and
    provider limits affect which vessels are visible.
    """
    response = requests.get(
        API_URL,
        params={"bbox": bbox, "max_age": "30m", "limit": 1000},
        timeout=20,
        headers={"User-Agent": "PortPulse-learning-project/0.1"},
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise ValueError("Unexpected response: not a GeoJSON FeatureCollection")
    if not isinstance(payload.get("features"), list):
        raise ValueError("Unexpected response: missing features list")
    return payload


def _report_age_minutes(seen: Any, now: datetime) -> float | None:
    if not isinstance(seen, str):
        return None
    try:
        observed = datetime.fromisoformat(seen.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            return None
        return round(max((now - observed).total_seconds() / 60, 0), 1)
    except ValueError:
        return None


def normalize_vessels(features: list[dict[str, Any]], now: datetime | None = None) -> list[dict[str, Any]]:
    """Return map/table-friendly rows for valid *vessel* point features.

    Speed < 1 kn means 'nearly stationary', NOT 'anchored'. A slow ship may be
    maneuvering. Records lacking speed remain 'Unknown'.
    """
    now = now or datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    seen_mmsis: set[str] = set()

    for feature in features:
        if not isinstance(feature, dict):
            continue
        geometry = feature.get("geometry") or {}
        props = feature.get("properties") or {}
        if geometry.get("type") != "Point" or props.get("kind", "vessel") != "vessel":
            continue
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            continue
        try:
            lon = float(coordinates[0])
            lat = float(coordinates[1])
        except (ValueError, TypeError):
            continue
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            continue

        identifier = props.get("mmsi", feature.get("id"))
        if identifier is None:
            continue
        mmsi = str(identifier)
        if mmsi in seen_mmsis:
            continue
        seen_mmsis.add(mmsi)

        try:
            speed = float(props["sog"]) if props.get("sog") is not None else None
            if speed is not None and not (0 <= speed <= 102.2):
                speed = None
        except (TypeError, ValueError):
            speed = None

        status = "Unknown speed" if speed is None else ("Nearly stationary" if speed < 1 else "Moving")
        colors = {
            "Moving": [34, 197, 94, 210],
            "Nearly stationary": [245, 158, 11, 220],
            "Unknown speed": [148, 163, 184, 210],
        }
        name = str(props.get("name") or "Unnamed vessel").strip()
        rows.append(
            {
                "name": name,
                "mmsi": mmsi,
                "lat": lat,
                "lon": lon,
                "speed_kn": speed,
                "speed_label": f"{speed:.1f}" if speed is not None else "N/A",
                "status": status,
                "last_seen_utc": props.get("seen") or "Unknown",
                "age_minutes": _report_age_minutes(props.get("seen"), now),
                "source": str(props.get("source") or "Unknown"),
                "color": colors[status],
            }
        )
    return rows
