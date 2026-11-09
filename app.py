"""PortPulse v0.1: an automatically refreshing maritime traffic dashboard."""

from datetime import datetime, timezone

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

from vessel_data import REGIONS, fetch_snapshot, normalize_vessels

st.set_page_config(page_title="PortPulse | Maritime Traffic", page_icon="🚢", layout="wide")
st.title("🚢 PortPulse")
st.caption("Live maritime traffic intelligence · Open Waters AIS · v0.1")

region_name = st.sidebar.selectbox("Monitoring area", list(REGIONS))
auto_refresh = st.sidebar.toggle("Auto-refresh every 60 seconds", value=True)
st.sidebar.markdown("**Legend**")
st.sidebar.markdown("🟢 Moving (≥ 1 knot)  \n🟠 Nearly stationary (< 1 knot)  \n⚪ Speed unknown")
st.sidebar.info("AIS snapshots are not official counts of port arrivals, berth delays, or congestion.")

region = REGIONS[region_name]
st.subheader(f"Vessel activity · {region_name}")


@st.cache_data(ttl=45, show_spinner=False)
def cached_snapshot(bbox: str) -> dict:
    # If multiple users load the app at once, the short cache reduces API calls.
    return fetch_snapshot(bbox)


@st.fragment(run_every="60s" if auto_refresh else None)
def live_dashboard() -> None:
    try:
        with st.spinner("Fetching vessel positions …"):
            payload = cached_snapshot(region["bbox"])
    except (requests.RequestException, ValueError) as error:
        st.error(f"Cannot fetch AIS data right now: {error}")
        st.info("Check your internet connection, try another region, or refresh the page later.")
        return

    vessels = normalize_vessels(payload["features"])
    frame = pd.DataFrame(vessels)
    moving = sum(v["status"] == "Moving" for v in vessels)
    stationary = sum(v["status"] == "Nearly stationary" for v in vessels)
    unknown = len(vessels) - moving - stationary

    a, b, c, d = st.columns(4)
    a.metric("Reported vessels", len(vessels))
    b.metric("Moving", moving)
    c.metric("Nearly stationary", stationary)
    d.metric("Speed unknown", unknown)

    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    st.caption(f"Dashboard checked: {checked_at} · Source observations can be up to 30 minutes old.")

    if not vessels:
        st.warning("No matching vessel positions were returned. Try another area or check again soon.")
    else:
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=frame,
            get_position="[lon, lat]",
            get_fill_color="color",
            get_radius=200,
            radius_min_pixels=4,
            radius_max_pixels=9,
            pickable=True,
            auto_highlight=True,
        )
        deck = pdk.Deck(
            map_style=None,
            initial_view_state=pdk.ViewState(
                latitude=region["center"][0],
                longitude=region["center"][1],
                zoom=region["zoom"],
                pitch=0,
            ),
            layers=[layer],
            tooltip={
                "html": "<b>{name}</b><br/>MMSI: {mmsi}<br/>Speed: {speed_label} kn<br/>Status: {status}<br/>Last report: {last_seen_utc}",
                "style": {"backgroundColor": "#102437", "color": "white"},
            },
        )
        st.pydeck_chart(deck, height=450)

        st.subheader("Vessel details")
        fields = ["name", "mmsi", "status", "speed_kn", "age_minutes", "lat", "lon", "source"]
        st.dataframe(
            frame[fields].rename(
                columns={
                    "name": "Vessel",
                    "mmsi": "MMSI",
                    "status": "Movement",
                    "speed_kn": "Speed (kn)",
                    "age_minutes": "Report age (min)",
                    "lat": "Latitude",
                    "lon": "Longitude",
                    "source": "AIS source",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    if len(payload["features"]) >= 1000:
        st.warning("API result reached its 1,000-position limit. The displayed count may be incomplete.")

    with st.expander("Data origin, attribution and limitations"):
        st.write(
            "Position snapshots: Open Waters AIS (https://openwaters.io/ais/). "
            "Actual coverage and freshness depend on receiving stations and data sources. "
            "A vessel under 1 knot is labeled nearly stationary, not necessarily anchored. "
            "This version does not estimate berth waiting times or port congestion."
        )
        st.write("The API identifies original AIS data sources; retain their license attribution for public use.")
        if payload.get("attribution"):
            st.json(payload["attribution"])
        else:
            st.write("No additional attribution object was returned in this response.")


live_dashboard()
