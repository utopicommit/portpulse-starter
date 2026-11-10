"""The historical analytics tab; import show_history_tab() into app.py."""

import pandas as pd
import requests
import streamlit as st

from port_history import HISTORICAL_PORTS, calculate_pbi, fetch_port_calls


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def cached_port_calls(port_name: str) -> pd.DataFrame:
    # Reuse results for six hours rather than calling IMF on every dashboard rerun.
    return fetch_port_calls(port_name, days=365)


def show_history_tab() -> None:
    st.subheader("Historical port traffic and activity index")
    st.caption("Source: IMF PortWatch / UN Global Platform; daily historical estimates, not a live vessel feed.")
    port = st.selectbox("Historical port", list(HISTORICAL_PORTS), key="history_port")

    try:
        with st.spinner("Loading historical port calls ..."):
            history = cached_port_calls(port)
    except (requests.RequestException, ValueError, KeyError) as exc:
        st.error(f"Historical data could not be loaded: {exc}")
        st.info("Try Rotterdam or Hamburg first, then retry if the IMF service is temporarily unavailable.")
        return

    activity = calculate_pbi(history)
    valid = activity.dropna(subset=["pbi"])
    latest_data_date = history["date"].max().strftime("%Y-%m-%d")

    a, b, c = st.columns(3)
    a.metric("Latest published day", latest_data_date)
    b.metric("Latest daily port calls", f"{history.iloc[-1]['portcalls']:,.0f}")
    if valid.empty:
        c.metric("Port Busyness Index", "N/A")
        st.info("Not enough consecutive daily observations yet to calculate the index.")
    else:
        latest_index = valid.iloc[-1]
        c.metric("Port Busyness Index", f"{latest_index['pbi']:.0f}")
        st.caption(
            f"PBI as of {latest_index['date']:%Y-%m-%d}: "
            "100 means the most recent 7-day call total matches the previous 28-day baseline. "
            "Above 100 means busier than that baseline; it does not imply congestion."
        )

    days_shown = st.selectbox("Chart period", [90, 180, 365], index=1)
    cutoff = history["date"].max() - pd.Timedelta(days=days_shown - 1)
    history_view = history.loc[history["date"] >= cutoff]
    activity_view = activity.loc[activity["date"] >= cutoff]
    st.markdown("#### Daily vessel arrivals (port calls)")
    st.line_chart(history_view.set_index("date")["portcalls"])
    st.markdown("#### Port Busyness Index (PBI)")
    st.line_chart(activity_view.set_index("date")["pbi"])
    st.caption(
        "PBI = 100 × (calls during previous 7 days) / "
        "(7 × mean daily calls during the 28 days before those 7 days). "
        "Missing days are excluded, not counted as zero."
    )
    st.markdown("#### Latest daily observations")
    st.dataframe(
        history_view[["date", "portcalls", "portcalls_cargo", "portcalls_tanker"]]
        .sort_values("date", ascending=False)
        .head(20),
        hide_index=True,
        use_container_width=True,
    )
    st.caption("Attribution: IMF PortWatch (International Monetary Fund), with UN Global Platform AIS data. ")
    st.link_button("Open IMF PortWatch data and methodology", "https://portwatch.imf.org/pages/data-and-methodology")
    st.warning(
        "Caution: this is a short-term activity indicator, not an official congestion score. "
        "Historical port boundaries and AIS coverage may differ from your live-map bounding boxes."
    )
