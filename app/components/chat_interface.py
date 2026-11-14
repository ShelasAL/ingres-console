"""
Chat Interface component for Streamlit.
Handles message history and presentation.
"""
import streamlit as st


def init_chat_session():
    """Ensure chat history state exists."""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "👋 Welcome to **INGRES Groundwater Assistant**!\n\n"
                    "I can help you query groundwater levels, water quality parameters (Fluoride, Arsenic, TDS, pH), "
                    "aquifer categorizations, and extraction stages across Indian states based on CGWB and GEC-2015 methodologies.\n\n"
                    "**Example queries you can try:**\n"
                    "- *What is the pre-monsoon water level in Jaipur for 2022?*\n"
                    "- *Which districts in Rajasthan are over-exploited?*\n"
                    "- *What is the fluoride level in Nalgonda wells?*\n"
                    "- *Show me the water level trend in Pune from 2015 to 2023*\n"
                    "- *Is Surat groundwater potable?*\n"
                ),
                "response_obj": None
            }
        ]


def display_chat_history(render_badge_fn, render_provenance_fn):
    """Render conversation history."""
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("response_obj") is not None:
                resp = msg["response_obj"]
                render_badge_fn(resp.confidence, resp.state)
                st.markdown(resp.answer_text)
                render_provenance_fn(resp)
            else:
                st.markdown(msg["content"])

