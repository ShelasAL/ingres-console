"""
Station & Well Dossier: In-depth telemetry, historical hydrographs,
sensor health, and chemical profiling for every monitoring station.
"""
import sys
from pathlib import Path
import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from ingres.schema.db_setup import get_connection
from app.components.provider_settings import render_provider_settings

st.set_page_config(page_title="Station Dossier — INGRES Enterprise", page_icon="🔍", layout="wide")

# Sidebar
render_provider_settings()

st.title("🔍 Station & Well Dossier")
st.caption("Deep-dive inspection: sensor telemetry, borehole specifications, historical hydrographs, and chemical potability.")

con = get_connection()

# Selector filters
c_sel1, c_sel2, c_sel3 = st.columns(3)

states = [r[0] for r in con.execute("SELECT DISTINCT state FROM wells ORDER BY state").fetchall()]
with c_sel1:
    selected_state = st.selectbox("Select State:", states, index=0)

districts = [r[0] for r in con.execute("SELECT DISTINCT district FROM wells WHERE state=? ORDER BY district", [selected_state]).fetchall()]
with c_sel2:
    selected_district = st.selectbox("Select District:", districts, index=0)

wells = [r[0] for r in con.execute("SELECT well_id FROM wells WHERE district=? ORDER BY well_id", [selected_district]).fetchall()]
with c_sel3:
    selected_well = st.selectbox("Select Station ID:", wells, index=0)

# Fetch Well Metadata
well_meta = con.execute("SELECT * FROM wells WHERE well_id=?", [selected_well]).df().iloc[0]

st.markdown("---")

# Header & Profile Card
col_info, col_map = st.columns([2, 1])

with col_info:
    st.subheader(f"Station Profile: `{selected_well}`")
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.markdown("**Location:**")
        st.write(f"{well_meta['district']}, {well_meta['state']}")
        st.caption(f"Block: {well_meta['block'] or 'Unspecified'}")
    with p2:
        st.markdown("**Aquifer Classification:**")
        st.write(f"{(well_meta['aquifer_type'] or 'Unconfined').title()} Aquifer")
        st.caption(f"Station Type: {well_meta['well_type'].replace('_', ' ').title()}")
    with p3:
        st.markdown("**Borehole Depth:**")
        st.write(f"{well_meta['depth_mbgl'] or 'N/A'} mbgl")
        st.caption(f"Installed: {well_meta['installation_year'] or 'Unknown'}")
    with p4:
        st.markdown("**Telemetry Source:**")
        st.write(f"{well_meta['data_source']}")
        st.caption(f"Coords: {well_meta['latitude']:.3f}°N, {well_meta['longitude']:.3f}°E")

with col_map:
    loc_df = pd.DataFrame([{"lat": well_meta["latitude"], "lon": well_meta["longitude"]}])
    st.map(loc_df, latitude="lat", longitude="lon", zoom=8)

st.markdown("---")

# Telemetry Health & Historical Level Records
levels_df = con.execute("""
    SELECT measurement_date, season, depth_to_water_mbgl, measurement_method, data_quality_flag, remarks
    FROM gw_levels
    WHERE well_id=?
    ORDER BY measurement_date ASC
""", [selected_well]).df()

# Quality Records
quality_df = con.execute("""
    SELECT sample_date, ph, tds_mg_l, fluoride_mg_l, arsenic_ug_l, nitrate_mg_l, hardness_mg_l, iron_mg_l, potability
    FROM gw_quality
    WHERE well_id=?
    ORDER BY sample_date DESC
""", [selected_well]).df()

# Assessment Record for District
assess_df = con.execute("""
    SELECT stage_of_extraction_pct, category, annual_gw_recharge_mcm, total_extraction_mcm, assessment_year
    FROM assessment_units
    WHERE LOWER(district)=LOWER(?)
    ORDER BY assessment_year DESC
    LIMIT 1
""", [selected_district]).df()

# Sensor & Telemetry Health Metrics
h1, h2, h3, h4 = st.columns(4)

total_readings = len(levels_df)
good_readings = (levels_df["data_quality_flag"] == "good").sum() if total_readings > 0 else 0
health_pct = (good_readings / total_readings * 100) if total_readings > 0 else 0
last_date = levels_df["measurement_date"].max() if total_readings > 0 else "N/A"
latest_depth = levels_df["depth_to_water_mbgl"].dropna().iloc[-1] if not levels_df["depth_to_water_mbgl"].dropna().empty else "N/A"

with h1:
    st.metric("Total Historical Readings", f"{total_readings}", help="Total seasonal observation logs")
with h2:
    st.metric("Latest Water Table", f"{latest_depth} mbgl" if latest_depth != "N/A" else "N/A", help="Most recent depth to water")
with h3:
    st.metric("Telemetry Health Score", f"{health_pct:.1f}%", help="Percentage of validated readings with 'good' quality flag")
with h4:
    st.metric("Latest Observation Date", f"{last_date}")

st.markdown("---")

# Tabs for Hydrograph, Water Quality, and Raw Telemetry Logs
t1, t2, t3 = st.tabs(["📉 Historical Hydrograph", "🧪 Water Quality & Potability Radar", "📋 Telemetry Logs"])

with t1:
    if not levels_df.empty and "depth_to_water_mbgl" in levels_df.columns:
        fig_hyd = px.line(
            levels_df.dropna(subset=["depth_to_water_mbgl"]),
            x="measurement_date",
            y="depth_to_water_mbgl",
            markers=True,
            color="season",
            title=f"Water Table Depth Hydrograph — Station {selected_well}",
            labels={"measurement_date": "Observation Date", "depth_to_water_mbgl": "Depth to Water (mbgl)"}
        )
        # Reversed axis: depth is downward
        fig_hyd.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_hyd, use_container_width=True)
    else:
        st.info("No level readings recorded for this station.")

with t2:
    if not quality_df.empty:
        latest_q = quality_df.iloc[0]
        st.markdown(f"#### Latest Sample Test: `{latest_q['sample_date']}` • Potability: **{str(latest_q['potability']).upper()}**")

        q_cols = st.columns(5)
        with q_cols[0]:
            fl_val = latest_q['fluoride_mg_l']
            st.metric("Fluoride", f"{fl_val} mg/L" if pd.notna(fl_val) else "N/A", "Limit: 1.5 mg/L", delta_color="inverse" if pd.notna(fl_val) and fl_val > 1.5 else "normal")
        with q_cols[1]:
            tds_val = latest_q['tds_mg_l']
            st.metric("TDS", f"{tds_val} mg/L" if pd.notna(tds_val) else "N/A", "Limit: 500 mg/L", delta_color="inverse" if pd.notna(tds_val) and tds_val > 500 else "normal")
        with q_cols[2]:
            ph_val = latest_q['ph']
            st.metric("pH Level", f"{ph_val}" if pd.notna(ph_val) else "N/A", "Limit: 6.5 - 8.5")
        with q_cols[3]:
            ars_val = latest_q['arsenic_ug_l']
            st.metric("Arsenic", f"{ars_val} µg/L" if pd.notna(ars_val) else "N/A", "Limit: 10 µg/L", delta_color="inverse" if pd.notna(ars_val) and ars_val > 10 else "normal")
        with q_cols[4]:
            nit_val = latest_q['nitrate_mg_l']
            st.metric("Nitrate", f"{nit_val} mg/L" if pd.notna(nit_val) else "N/A", "Limit: 45 mg/L", delta_color="inverse" if pd.notna(nit_val) and nit_val > 45 else "normal")

        # Historical Quality Table
        st.markdown("##### Historical Quality Records for Station")
        st.dataframe(quality_df, use_container_width=True)
    else:
        st.info("No chemical water quality samples on record for this station.")

with t3:
    st.dataframe(levels_df, use_container_width=True)

con.close()

