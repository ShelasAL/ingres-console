"""
Page 5: Live NWIC Data Synchronization.
Direct, in-app ingestion of official CGWB groundwater datasets from nwdp.nwic.gov.in.
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import requests

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from ingres.schema.db_setup import get_connection
from ingres.data.nwic_loader import NWIC_RESOURCES, ingest_state_data
from app.components.provider_settings import render_provider_settings

st.set_page_config(page_title="NWIC Live Sync — INGRES Enterprise", page_icon="📡", layout="wide")

# Sidebar
render_provider_settings()

st.title("📡 Official NWIC / CGWB Live Data Synchronizer")
st.caption("Direct programmatic ingestion from National Water Data Portal (`nwdp.nwic.gov.in`).")

# Server connectivity check
nwic_status = False
try:
    check = requests.get("https://nwdp.nwic.gov.in/api/3/action/package_search?q=organization:cgwb", timeout=5, verify=False)
    nwic_status = (check.status_code == 200)
except Exception:
    pass

c_stat1, c_stat2 = st.columns([2, 1])
with c_stat1:
    if nwic_status:
        st.success("🟢 **National Water Data Portal (NWIC) API:** Online & Accessible (`nwdp.nwic.gov.in`)")
    else:
        st.warning("🟡 **NWIC Portal Status:** Connecting / Limited access. Direct cached streaming enabled.")
with c_stat2:
    con = get_connection()
    live_count = con.execute("SELECT COUNT(*) FROM wells WHERE data_source='CGWB-NWIC-Live'").fetchone()[0]
    st.metric("Live CGWB Stations Ingested", f"{live_count:,}")
    con.close()

st.markdown("---")

# State Selection Panel
st.subheader("📥 Ingest State Groundwater Datasets")
st.markdown("Select one or more states to stream official quarterly water level telemetry and laboratory chemical quality tests.")

available_states = list(NWIC_RESOURCES.keys())
state_labels = {k: v["state_name"] for k, v in NWIC_RESOURCES.items()}

col_cfg1, col_cfg2 = st.columns([2, 1])
with col_cfg1:
    selected_states = st.multiselect(
        "Select States for Live Ingestion:",
        options=available_states,
        default=["rajasthan", "punjab", "andhra", "delhi", "kerala", "tamil nadu", "uttar pradesh"],
        format_func=lambda x: state_labels.get(x, x)
    )

with col_cfg2:
    max_records = st.select_slider(
        "Max Records per State:",
        options=[500, 1000, 2500, 5000, 10000],
        value=1000,
        help="Higher counts download larger datasets from government servers."
    )

if st.button("🚀 Ingest Selected States Data Now", key="sync_nwic_btn", type="primary"):
    if not selected_states:
        st.warning("Please select at least one state to ingest.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []

        con = get_connection()
        for idx, state_key in enumerate(selected_states):
            state_label = state_labels.get(state_key, state_key)
            status_text.text(f"⏳ Downloading & ingesting {state_label} datasets from NWIC...")
            try:
                stats = ingest_state_data(state_key, con, max_rows=max_records)
                results.append(stats)
            except Exception as e:
                results.append({"state": state_label, "stations": 0, "levels": 0, "quality": 0, "error": str(e)})

            progress_bar.progress((idx + 1) / len(selected_states))

        con.close()
        status_text.text("✅ Data ingestion batch finished!")
        st.success(f"Successfully processed {len(selected_states)} states from official CGWB sources.")

        # Results summary table
        st.subheader("📊 Ingestion Summary")
        res_df = pd.DataFrame(results)
        st.dataframe(res_df, use_container_width=True)

st.markdown("---")

# Inspection of ingested live data
st.subheader("🗺️ Ingested Live CGWB Stations")
con = get_connection()
live_wells_df = con.execute("""
    SELECT well_id, state, district, block, latitude, longitude, well_type, data_source
    FROM wells
    WHERE data_source='CGWB-NWIC-Live'
    LIMIT 2000
""").df()
con.close()

if not live_wells_df.empty:
    m_col1, m_col2 = st.columns([1, 1])
    with m_col1:
        st.dataframe(live_wells_df, use_container_width=True)
    with m_col2:
        st.map(live_wells_df, latitude="latitude", longitude="longitude")
        st.caption(f"Showing {len(live_wells_df)} live CGWB monitoring stations plotted geographically.")
else:
    st.info("No live CGWB stations imported yet. Select states above and click 'Ingest Selected States Data Now'.")

