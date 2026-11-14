"""
Page 1: Groundwater AI Copilot.
Natural-language scientific query engine with zero hallucinations, verified citations,
and sorted interactive hydrographs.
"""
import sys
import time
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

# Setup path
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from ingres.schema.db_setup import get_connection
from ingres.retrieval.query_router import route_query
from ingres.retrieval.text_to_sql import execute_query
from ingres.retrieval.coverage_detector import check_coverage
from ingres.retrieval.vector_search import semantic_search
from ingres.retrieval.geo_filter import get_well_coordinates
from ingres.generation.context_assembler import assemble_context
from ingres.generation.response_generator import generate_response

from app.components.confidence_badge import render_confidence_badge
from app.components.provenance_card import render_provenance_card
from app.components.chat_interface import init_chat_session, display_chat_history
from app.components.provider_settings import render_provider_settings

st.set_page_config(page_title="Groundwater Copilot — INGRES Enterprise", page_icon="💬", layout="wide")

# Sidebar provider settings
llm_client = render_provider_settings()

init_chat_session()

st.title("💬 Groundwater AI Copilot")
st.caption("Ask natural-language scientific questions about water tables, chemical potability, and aquifer sustainability.")

# Query suggestion buttons
st.markdown("**Sample Hydrogeological Inquiries:**")
q_col1, q_col2, q_col3, q_col4 = st.columns(4)

suggested_query = None
if q_col1.button("📉 Jaipur water table trend"):
    suggested_query = "Show me the water level trend in Jaipur from 2015 to 2023"
if q_col2.button("🧪 Nalgonda fluoride status"):
    suggested_query = "What is the fluoride level in Nalgonda wells?"
if q_col3.button("⚠️ Rajasthan over-exploited units"):
    suggested_query = "Which districts in Rajasthan are over-exploited?"
if q_col4.button("📖 What is a monitoring well?"):
    suggested_query = "What is a well and piezometer in groundwater monitoring?"

# Render history
display_chat_history(render_confidence_badge, render_provenance_card)

# Input box
user_input = st.chat_input("Enter your groundwater inquiry (e.g. 'What is the water level in Bikaner in 2022?')...")
active_query = user_input or suggested_query

if active_query:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": active_query, "response_obj": None})
    with st.chat_message("user"):
        st.markdown(active_query)

    # Process query
    with st.chat_message("assistant"):
        with st.spinner("Analyzing inquiry, evaluating data coverage & retrieving evidence..."):
            con = get_connection()

            # 1. Router
            route_res = route_query(active_query, llm_client=llm_client)

            # 2. Coverage Detector
            coverage_res = check_coverage(active_query, route_res.entities, con)

            # 3. Text-to-SQL
            sql_res = execute_query(
                query=active_query,
                entities=route_res.entities,
                intent=route_res.intent,
                con=con,
                llm_client=llm_client
            )

            # 4. Semantic Search
            semantic_chunks = []
            if route_res.intent in ["SEMANTIC_CONCEPTUAL", "UNSUPPORTED"] or not sql_res.success or sql_res.row_count == 0:
                semantic_chunks = semantic_search(active_query, n_results=2)

            # 5. Geospatial coordinates
            locs = route_res.entities.get("locations", [])
            coords = get_well_coordinates(locs, con) if locs else []

            # 6. Context Assembly
            ctx = assemble_context(
                sql_result=sql_res,
                semantic_chunks=semantic_chunks,
                coverage=coverage_res,
                intent=route_res.intent,
                well_coordinates=coords
            )

            # 7. Generation
            resp = generate_response(active_query, ctx, llm_client)

            # Display response
            render_confidence_badge(resp.confidence, resp.state)
            st.markdown(resp.answer_text)

            # Visualizations if data is available
            df = sql_res.to_dataframe()
            if not df.empty:
                v_tabs = st.tabs(["📊 Interactive Hydrograph", "🗺️ Station Map", "📋 Raw Data Records"])

                with v_tabs[0]:
                    if "measurement_date" in df.columns and "depth_to_water_mbgl" in df.columns:
                        # CRITICAL FIX: Sort chronologically to prevent tangled zig-zags
                        clean_df = df.dropna(subset=["depth_to_water_mbgl"]).copy()
                        clean_df["measurement_date"] = pd.to_datetime(clean_df["measurement_date"])
                        clean_df = clean_df.sort_values(by="measurement_date")

                        fig = px.line(
                            clean_df,
                            x="measurement_date",
                            y="depth_to_water_mbgl",
                            color="well_id" if "well_id" in clean_df.columns else None,
                            markers=True,
                            title="Water Table Depth Hydrograph (mbgl) — Lower is Deeper",
                            labels={"depth_to_water_mbgl": "Depth (mbgl)", "measurement_date": "Observation Date"}
                        )
                        fig.update_yaxes(autorange="reversed") # Depth is measured downwards
                        st.plotly_chart(fig, use_container_width=True)

                    elif "sample_date" in df.columns and any(col in df.columns for col in ["fluoride_mg_l", "tds_mg_l", "ph"]):
                        val_cols = [c for c in ["fluoride_mg_l", "tds_mg_l", "ph", "nitrate_mg_l", "arsenic_ug_l"] if c in df.columns]
                        clean_q_df = df.copy()
                        clean_q_df["sample_date"] = pd.to_datetime(clean_q_df["sample_date"])
                        clean_q_df = clean_q_df.sort_values(by="sample_date")

                        fig = px.bar(
                            clean_q_df,
                            x="sample_date",
                            y=val_cols[0],
                            color="potability" if "potability" in clean_q_df.columns else None,
                            title=f"Water Quality Observation: {val_cols[0].replace('_', ' ').upper()}",
                            barmode="group"
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    elif "stage_of_extraction_pct" in df.columns:
                        fig = px.bar(
                            df,
                            x="district" if "district" in df.columns else "unit_id",
                            y="stage_of_extraction_pct",
                            color="category" if "category" in df.columns else None,
                            title="Groundwater Extraction Stage (%)",
                            color_discrete_map={
                                "safe": "green", "semi_critical": "orange",
                                "critical": "red", "over_exploited": "darkred", "saline": "purple"
                            }
                        )
                        fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="100% Critical Threshold")
                        st.plotly_chart(fig, use_container_width=True)

                with v_tabs[1]:
                    if coords:
                        map_df = pd.DataFrame(coords)
                        st.map(map_df, latitude="latitude", longitude="longitude")
                        st.caption(f"Showing {len(map_df)} monitoring stations for queried region.")
                    else:
                        st.info("No spatial coordinates mapped for this specific query.")

                with v_tabs[2]:
                    st.dataframe(df, use_container_width=True)

            render_provenance_card(resp)

            # Save assistant message to session state
            st.session_state.messages.append({
                "role": "assistant",
                "content": resp.answer_text,
                "response_obj": resp
            })

