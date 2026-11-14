"""
Page 3: Groundwater Data Explorer.
Interactive filtering, inspection, and visualization of the underlying structured datasets.
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from ingres.schema.db_setup import get_connection
from app.components.provider_settings import render_provider_settings

st.set_page_config(page_title="Data Explorer — INGRES Enterprise", page_icon="📊", layout="wide")

# Sidebar
render_provider_settings()

st.title("📊 National Groundwater Data Catalog")
st.caption("Inspect and filter raw hydrogeological datasets (CGWB / NWIC / GEC-2015 standard).")

con = get_connection()

tab_names = ["Monitoring Stations", "Water Level Time-Series", "Water Quality Samples", "GEC-2015 Assessment Units"]
tabs = st.tabs(tab_names)

# Tab 1: Wells
with tabs[0]:
    st.subheader("Monitoring Stations (`wells`)")
    states = [r[0] for r in con.execute("SELECT DISTINCT state FROM wells ORDER BY state").fetchall()]
    selected_state = st.selectbox("Filter by State:", ["All"] + states, key="wells_state")

    query = "SELECT * FROM wells"
    if selected_state != "All":
        query += f" WHERE state = '{selected_state}'"
    wells_df = con.execute(query).df()

    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(wells_df, use_container_width=True)
    with col2:
        st.map(wells_df, latitude="latitude", longitude="longitude")

# Tab 2: Levels
with tabs[1]:
    st.subheader("Seasonal Water Levels (`gw_levels`)")
    seasons = [r[0] for r in con.execute("SELECT DISTINCT season FROM gw_levels WHERE season IS NOT NULL").fetchall()]
    c1, c2 = st.columns(2)
    with c1:
        sel_season = st.selectbox("Season:", ["All"] + seasons, key="lvl_season")
    with c2:
        sel_flag = st.selectbox("Quality Flag:", ["All", "good", "suspect", "missing", "estimated"], key="lvl_flag")

    lvl_query = """
    SELECT l.record_id, w.district, w.state, l.measurement_date, l.season,
           l.depth_to_water_mbgl, l.data_quality_flag, l.measurement_method
    FROM gw_levels l JOIN wells w ON l.well_id = w.well_id
    WHERE 1=1
    """
    if sel_season != "All":
        lvl_query += f" AND l.season = '{sel_season}'"
    if sel_flag != "All":
        lvl_query += f" AND l.data_quality_flag = '{sel_flag}'"
    lvl_query += " LIMIT 1000"

    lvl_df = con.execute(lvl_query).df()
    st.dataframe(lvl_df, use_container_width=True)

    if not lvl_df.empty and "depth_to_water_mbgl" in lvl_df.columns:
        fig = px.histogram(
            lvl_df.dropna(subset=["depth_to_water_mbgl"]),
            x="depth_to_water_mbgl",
            color="data_quality_flag",
            nbins=30,
            title="Distribution of Depth-to-Water Levels (mbgl)"
        )
        st.plotly_chart(fig, use_container_width=True)

# Tab 3: Quality
with tabs[2]:
    st.subheader("Chemical Quality Samples (`gw_quality`)")
    pot_opts = ["All", "potable", "non_potable", "unknown"]
    sel_pot = st.selectbox("Potability (BIS 10500:2012):", pot_opts, key="qual_pot")

    q_query = """
    SELECT q.record_id, w.district, w.state, q.sample_date,
           q.ph, q.tds_mg_l, q.fluoride_mg_l, q.arsenic_ug_l, q.nitrate_mg_l, q.potability
    FROM gw_quality q JOIN wells w ON q.well_id = w.well_id
    """
    if sel_pot != "All":
        q_query += f" WHERE q.potability = '{sel_pot}'"
    q_query += " LIMIT 1000"

    qual_df = con.execute(q_query).df()
    st.dataframe(qual_df, use_container_width=True)

    if not qual_df.empty:
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            fig_fl = px.box(qual_df, x="potability", y="fluoride_mg_l", points="all", title="Fluoride by Potability (BIS Limit: 1.5 mg/L)")
            fig_fl.add_hline(y=1.5, line_dash="dash", line_color="red")
            st.plotly_chart(fig_fl, use_container_width=True)
        with c_p2:
            fig_tds = px.box(qual_df, x="potability", y="tds_mg_l", points="all", title="TDS by Potability (BIS Limit: 500 mg/L)")
            fig_tds.add_hline(y=500, line_dash="dash", line_color="red")
            st.plotly_chart(fig_tds, use_container_width=True)

# Tab 4: Assessments
with tabs[3]:
    st.subheader("Groundwater Resource Estimation Units (`assessment_units`)")
    cat_opts = ["All", "safe", "semi_critical", "critical", "over_exploited", "saline"]
    sel_cat = st.selectbox("GEC Category:", cat_opts, key="au_cat")

    au_query = "SELECT * FROM assessment_units"
    if sel_cat != "All":
        au_query += f" WHERE category = '{sel_cat}'"
    au_query += " ORDER BY stage_of_extraction_pct DESC"

    au_df = con.execute(au_query).df()
    st.dataframe(au_df, use_container_width=True)

    if not au_df.empty:
        fig_cat = px.pie(au_df, names="category", title="GEC-2015 Category Breakdown", hole=0.4)
        st.plotly_chart(fig_cat, use_container_width=True)

con.close()

