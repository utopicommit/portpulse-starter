"""IMF PortWatch historical port-call data and a first Port Busyness Index.

This module is independent of the live AIS code in vessel_data.py.
Source: https://portwatch.imf.org/ (IMF and UN Global Platform).
"""

import pandas as pd
import requests

BASE_URL = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services"
PORTS_URL = f"{BASE_URL}/PortWatch_ports_database/FeatureServer/0/query"
HISTORY_URL = f"{BASE_URL}/Daily_Ports_Data/FeatureServer/0/query"

# "Dubai" maps to Jebel Ali, not every harbour in the Dubai metropolitan area.
# "Oslofjord" maps to Oslo port, not the entire fjord.
HISTORICAL_PORTS = {
    "Rotterdam": ("Rotterdam", "NLD"),
    "Hamburg": ("Hamburg", "DEU"),
    "Karachi": ("Karachi", "PAK"),
    "Dubai (Jebel Ali)": ("Jebel Ali", "ARE"),
    "Oslo (not all Oslofjord)": ("Oslo", "NOR"),
}


def _get_rows(url: str, params: dict) -> list[dict]:
    """Send a limited ArcGIS query and extract the attributes of each result."""
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise ValueError(f"PortWatch API error: {payload['error'].get('message', 'Unknown error')}")
    if not isinstance(payload.get("features"), list):
        raise ValueError("Unexpected response from the PortWatch API")
    return [item["attributes"] for item in payload["features"] if "attributes" in item]


def find_port_id(port_name: str) -> str:
    """Look up the PortWatch-specific ID, rather than guessing from port names."""
    if port_name not in HISTORICAL_PORTS:
        raise ValueError(f"Unknown historical port: {port_name}")

    search_name, country_code = HISTORICAL_PORTS[port_name]
    rows = _get_rows(
        PORTS_URL,
        {
            "where": f"portname LIKE '%{search_name}%' AND ISO3 = '{country_code}'",
            "outFields": "portid,portname,ISO3",
            "returnGeometry": "false",
            "resultRecordCount": 20,
            "f": "json",
        },
    )
    exact = [r for r in rows if str(r.get("portname", "")).casefold() == search_name.casefold()]
    if len(exact) != 1 or not exact[0].get("portid"):
        names = ", ".join(str(r.get("portname", "?")) for r in rows)
        raise ValueError(
            f"Could not uniquely match {search_name} ({country_code}) in PortWatch. "
            f"Found: {names or 'no matching ports'}"
        )
    return str(exact[0]["portid"])


def fetch_port_calls(port_name: str, days: int = 365) -> pd.DataFrame:
    """Fetch the most recent N published daily rows for one port.

    PortWatch is delayed, usually refreshed on a weekly schedule; it is NOT live AIS.
    Results are capped to one API page (<=1000 observations) for a small prototype.
    """
    if not 35 <= days <= 1000:
        raise ValueError("days must be between 35 and 1000")
    port_id = find_port_id(port_name)
    rows = _get_rows(
        HISTORY_URL,
        {
            "where": f"portid = '{port_id}'",
            "outFields": "date,portid,portname,portcalls,portcalls_cargo,portcalls_tanker",
            "orderByFields": "date DESC",
            "returnGeometry": "false",
            "resultRecordCount": days,
            "f": "json",
        },
    )
    if not rows:
        raise ValueError(f"No historical port calls were returned for {port_name}")
    frame = pd.DataFrame(rows)
    if not {"date", "portcalls"}.issubset(frame.columns):
        raise ValueError("PortWatch did not return the expected date/portcalls fields")
    # ArcGIS layers have used date strings and numeric epoch-millisecond timestamps.
    if pd.api.types.is_numeric_dtype(frame["date"]):
        dates = pd.to_datetime(frame["date"], unit="ms", errors="coerce", utc=True)
    else:
        dates = pd.to_datetime(frame["date"], errors="coerce", utc=True)
    frame["date"] = dates.dt.tz_localize(None).dt.normalize()
    frame["portcalls"] = pd.to_numeric(frame["portcalls"], errors="coerce")
    frame = frame.dropna(subset=["date", "portcalls"])
    frame = frame.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    if frame.empty:
        raise ValueError(f"No usable historical observations for {port_name}")
    return frame.reset_index(drop=True)


def calculate_pbi(frame: pd.DataFrame) -> pd.DataFrame:
    """PBI = 100 x last-7-day calls / expected 7-day calls.

    Expected calls = mean daily calls in the 28 days BEFORE that 7-day window x 7.
    Missing dates are left missing (never silently treated as zero).
    This is a rolling *short-term* baseline, not a seasonal or congestion index.
    """
    result = frame[["date", "portcalls"]].copy()
    result["date"] = pd.to_datetime(result["date"])
    result = result.drop_duplicates("date").sort_values("date").set_index("date")
    result = result.asfreq("D")
    result["calls_last_7_days"] = result["portcalls"].rolling(7, min_periods=7).sum()
    expected = result["portcalls"].shift(7).rolling(28, min_periods=28).mean() * 7
    result["expected_7_day_calls"] = expected
    result["pbi"] = 100 * result["calls_last_7_days"] / expected.where(expected > 0)
    return result.reset_index()
