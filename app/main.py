"""
INGRES — National Groundwater Intelligence Platform
Executive Command Center & Operational Overview.
"""
import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path

from app.components.provider_settings import render_provider_settings

st.set_page_config(
    page_title="INGRES — National Groundwater Intelligence Platform",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar
st.sidebar.title("💧 INGRES Enterprise")
st.sidebar.caption("National Groundwater Intelligence Platform")
st.sidebar.markdown("---")

# Render multi-provider settings
llm_client = render_provider_settings()

st.sidebar.markdown("""
### Quick Navigation
- **01 Groundwater Copilot**: Natural language query assistant
- **02 Station Dossier**: Individual well telemetry & profile
- **03 Hydro Explorer**: Geospatial data catalog & filters
- **04 Performance Report**: System SLA & reliability metrics
""")

# Main Executive Header
st.title("💧 National Groundwater Intelligence Platform")
st.markdown("##### Real-Time Aquifer Monitoring, Verified Evidence Retrieval & Resource Sustainability Analytics")

# Load metrics from DB
db_path = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "ingres.duckdb"
con = duckdb.connect(str(db_path), read_only=True)

well_count = con.execute("SELECT COUNT(*) FROM wells").fetchone()[0]
level_count = con.execute("SELECT COUNT(*) FROM gw_levels").fetchone()[0]
quality_count = con.execute("SELECT COUNT(*) FROM gw_quality").fetchone()[0]
unit_count = con.execute("SELECT COUNT(*) FROM assessment_units").fetchone()[0]
over_exp_count = con.execute("SELECT COUNT(*) FROM assessment_units WHERE category='over_exploited'").fetchone()[0]
potable_rate = con.execute("SELECT (COUNT(CASE WHEN potability='potable' THEN 1 END) * 100.0 / COUNT(*)) FROM gw_quality").fetchone()[0]

con.close()

# Executive KPI Cards
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
with kpi1:
    st.metric("Monitoring Stations", f"{well_count:,}", "Active Sensors")
with kpi2:
    st.metric("Water Table Observations", f"{level_count:,}", "Quarterly Telemetry")
with kpi3:
    st.metric("Quality Tests Indexed", f"{quality_count:,}", "BIS 10500 Compliant")
with kpi4:
    st.metric("Drinking Water Potability", f"{potable_rate:.1f}%", "-2.4% vs 2021")
with kpi5:
    st.metric("Over-Exploited Basins", f"{over_exp_count}", "Priority Intervention", delta_color="inverse")

st.markdown("---")

# Main Dashboard Panels
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("🗺️ National Aquifer Extraction Intensity")
    st.caption("Distribution of groundwater extraction stages across key monitored states.")
    
    con = duckdb.connect(str(db_path), read_only=True)
    state_au = con.execute("""
        SELECT state, 
               ROUND(AVG(stage_of_extraction_pct), 1) as avg_extraction_stage,
               ROUND(SUM(annual_gw_recharge_mcm), 1) as total_recharge_mcm,
               ROUND(SUM(total_extraction_mcm), 1) as total_extraction_mcm,
               COUNT(*) as total_units
        FROM assessment_units
        GROUP BY state
        ORDER BY avg_extraction_stage DESC
    """).df()
    con.close()

    fig_state = px.bar(
        state_au,
        x="state",
        y="avg_extraction_stage",
        color="avg_extraction_stage",
        color_continuous_scale="Reds",
        labels={"avg_extraction_stage": "Extraction Stage (%)", "state": "State"},
        text="avg_extraction_stage"
    )
    fig_state.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="100% Critical Threshold")
    st.plotly_chart(fig_state, use_container_width=True)

with col_right:
    st.subheader("⚠️ Water Quality Vulnerability Watch")
    st.caption("Contamination risk analysis evaluated against BIS 10500:2012 maximum limits.")

    con = duckdb.connect(str(db_path), read_only=True)
    violations = con.execute("""
        SELECT 
            SUM(CASE WHEN fluoride_mg_l > 1.5 THEN 1 ELSE 0 END) as high_fluoride,
            SUM(CASE WHEN tds_mg_l > 500 THEN 1 ELSE 0 END) as high_tds,
            SUM(CASE WHEN nitrate_mg_l > 45 THEN 1 ELSE 0 END) as high_nitrate,
            SUM(CASE WHEN arsenic_ug_l > 10 THEN 1 ELSE 0 END) as high_arsenic
        FROM gw_quality
    """).df()
    con.close()

    v_data = [
        {"Contaminant": "High TDS (>500 mg/L)", "Exceedances": int(violations["high_tds"].iloc[0]), "Severity": "High"},
        {"Contaminant": "Fluoride (>1.5 mg/L)", "Exceedances": int(violations["high_fluoride"].iloc[0]), "Severity": "Critical"},
        {"Contaminant": "Nitrate (>45 mg/L)", "Exceedances": int(violations["high_nitrate"].iloc[0]), "Severity": "Moderate"},
        {"Contaminant": "Arsenic (>10 µg/L)", "Exceedances": int(violations["high_arsenic"].iloc[0]), "Severity": "Critical"},
    ]
    v_df = pd.DataFrame(v_data)

    fig_v = px.pie(v_df, names="Contaminant", values="Exceedances", color="Severity",
                   color_discrete_map={"Critical": "#dc3545", "High": "#fd7e14", "Moderate": "#ffc107"},
                   hole=0.45)
    st.plotly_chart(fig_v, use_container_width=True)

st.markdown("---")

# Platform Workflows & Entry points
st.subheader("🚀 Platform Modules")
m1, m2, m3 = st.columns(3)

with m1:
    st.markdown("""
    #### 💬 [Groundwater AI Copilot](01_Groundwater_Copilot)
    Natural-language scientific query engine with zero hallucinations, verified station citations, and automatic coverage detection.
    """)
with m2:
    st.markdown("""
    #### 🔍 [Station & Well Dossier](02_Station_Dossier)
    Detailed profile and sensor health for all 200 monitoring stations: historical hydrographs, water quality radar, and borehole specs.
    """)
with m3:
    st.markdown("""
    #### 📊 [System Performance & Audit](04_Performance_Report)
    SLAs, query execution reliability, latency benchmarks, and verified provenance audit reports.
    """)
