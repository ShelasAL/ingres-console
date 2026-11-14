"""
Provider Settings Sidebar Component.
Allows configuring OpenRouter, Gemini, OpenAI, or Custom Base URLs (Ollama / Local LLM)
with automatic fallback to the Deterministic Hydro Synthesizer.
"""
import os
import streamlit as st
from ingres.generation.llm_client import get_llm_client, DEFAULT_OPENROUTER_URL, DEFAULT_OPENROUTER_MODEL


def render_provider_settings():
    """Renders LLM provider configuration in the Streamlit sidebar."""
    st.sidebar.markdown("### ⚙️ AI Engine Settings")

    if "provider" not in st.session_state:
        st.session_state.provider = os.getenv("LLM_PROVIDER", "OpenRouter")
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    if "base_url" not in st.session_state:
        st.session_state.base_url = os.getenv("LLM_BASE_URL", DEFAULT_OPENROUTER_URL)
    if "model_name" not in st.session_state:
        st.session_state.model_name = os.getenv("LLM_MODEL", DEFAULT_OPENROUTER_MODEL)

    with st.sidebar.expander("🔌 Model & Provider Config", expanded=False):
        provider_choice = st.selectbox(
            "Primary Provider:",
            ["OpenRouter", "Google Gemini", "OpenAI", "Custom Base URL (Local / Ollama)"],
            index=["OpenRouter", "Google Gemini", "OpenAI", "Custom Base URL (Local / Ollama)"].index(
                st.session_state.provider if st.session_state.provider in ["OpenRouter", "Google Gemini", "OpenAI"] else "Custom Base URL (Local / Ollama)"
            )
        )

        st.session_state.provider = provider_choice

        if provider_choice == "OpenRouter":
            st.caption("Standard OpenRouter API integration.")
            st.session_state.base_url = DEFAULT_OPENROUTER_URL
            st.session_state.api_key = st.text_input("OpenRouter API Key:", value=st.session_state.api_key, type="password", placeholder="sk-or-v1-...")
            st.session_state.model_name = st.text_input("Model Name:", value=st.session_state.model_name or DEFAULT_OPENROUTER_MODEL)

        elif provider_choice == "Google Gemini":
            st.caption("Google AI Studio Gemini API integration.")
            st.session_state.api_key = st.text_input("Gemini API Key:", value=st.session_state.api_key, type="password", placeholder="AIzaSy...")
            st.session_state.model_name = st.text_input("Model Name:", value="gemini-1.5-flash")

        elif provider_choice == "OpenAI":
            st.caption("OpenAI REST endpoint.")
            st.session_state.base_url = "https://api.openai.com/v1"
            st.session_state.api_key = st.text_input("OpenAI API Key:", value=st.session_state.api_key, type="password", placeholder="sk-...")
            st.session_state.model_name = st.text_input("Model Name:", value="gpt-4o-mini")

        elif provider_choice == "Custom Base URL (Local / Ollama)":
            st.caption("Compatible with Ollama, LMStudio, vLLM, or private proxy.")
            st.session_state.base_url = st.text_input("Base URL:", value=st.session_state.base_url or "http://localhost:11434/v1")
            st.session_state.api_key = st.text_input("API Key (Optional):", value=st.session_state.api_key, type="password", placeholder="Bearer token if required")
            st.session_state.model_name = st.text_input("Model Name:", value=st.session_state.model_name or "llama3")

    # Update active singleton client
    prov_key = "openrouter" if provider_choice == "OpenRouter" else ("gemini" if provider_choice == "Google Gemini" else ("openai" if provider_choice == "OpenAI" else "custom"))
    client = get_llm_client(
        provider=prov_key,
        api_key=st.session_state.api_key,
        base_url=st.session_state.base_url,
        model=st.session_state.model_name,
    )

    # Status badge
    if client.is_online:
        st.sidebar.success(f"🟢 **Online:** {provider_choice} ({st.session_state.model_name.split('/')[-1]})")
    else:
        st.sidebar.info("⚡ **Offline Fallback:** Dynamic Hydro Synthesizer active (Zero-key)")

    st.sidebar.markdown("---")
    return client

