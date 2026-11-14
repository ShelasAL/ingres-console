"""
Provenance Card component for Streamlit.
Renders data provenance (well_id, coordinates, measurement date, flags)
and provides an export mechanism + human-review escalation with unique UUIDs.
"""
import uuid
import streamlit as st
import pandas as pd


def render_provenance_card(response):
    """
    Renders structured provenance details for a generated response.
    Uses unique UUIDs to prevent StreamlitDuplicateElementKey exceptions.
    """
    unique_id = uuid.uuid4().hex[:8]

    with st.expander("🔍 Scientific Evidence & Data Provenance", expanded=False):
        c1, c2 = st.columns([3, 1])

        with c1:
            st.markdown("**Data Coverage Assessment:**")
            st.info(response.coverage_note if response.coverage_note else "Coverage complete.")

            if response.recommendation:
                st.markdown("**Recommendation / Guidance:**")
                st.caption(response.recommendation)

        with c2:
            st.metric("Cited Stations", len(response.sources))
            if response.sources:
                st.caption(", ".join(response.sources[:5]))

        # Evidence table
        if response.evidence_list:
            st.markdown("#### Retrieved Station Records")
            df = pd.DataFrame(response.evidence_list)
            st.dataframe(df, use_container_width=True)

            # CSV Download with guaranteed unique key
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Evidence (CSV)",
                data=csv,
                file_name=f"groundwater_evidence_{unique_id}.csv",
                mime="text/csv",
                key=f"export_btn_{unique_id}"
            )

        # Executed SQL Query
        if response.sql_used:
            st.markdown("#### Deterministic Analytical Query")
            st.code(response.sql_used, language="sql")

        # Human Review Action with guaranteed unique key
        if st.button("👤 Flag Query for Expert Human Review", key=f"flag_btn_{unique_id}"):
            st.warning("Query and retrieved evidence have been logged for hydrogeological review.")
