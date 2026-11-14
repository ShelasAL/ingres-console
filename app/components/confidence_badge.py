"""
Confidence badge component for Streamlit.
Renders visually distinct color-coded badges for confidence and response states.
"""
import streamlit as st


def render_confidence_badge(confidence: str, state: str):
    """Render confidence and response state badges."""
    colors = {
        "HIGH": ("#198754", "#d1e7dd", "🟢 HIGH CONFIDENCE"),
        "MEDIUM": ("#ffc107", "#fff3cd", "🟡 MEDIUM CONFIDENCE"),
        "LOW": ("#dc3545", "#f8d7da", "🔴 LOW CONFIDENCE"),
        "NONE": ("#6c757d", "#e2e3e5", "⚫ NO CONFIDENCE")
    }
    state_colors = {
        "GROUNDED": ("#0f5132", "#d1e7dd", "✅ Fully Supported"),
        "PARTIAL": ("#664d03", "#fff3cd", "⚠️ Partially Supported"),
        "INFERRED": ("#495057", "#e9ecef", "🔶 Inferred"),
        "INSUFFICIENT": ("#842029", "#f8d7da", "❌ Insufficient Data"),
        "OUT_OF_SCOPE": ("#2b2f32", "#ced4da", "🚫 Out of Scope"),
        "HUMAN_REVIEW": ("#432874", "#e2d9f3", "👤 Human Review Required")
    }

    c_fg, c_bg, c_txt = colors.get(confidence.upper(), ("#6c757d", "#e2e3e5", confidence))
    s_fg, s_bg, s_txt = state_colors.get(state.upper(), ("#6c757d", "#e2e3e5", state))

    html = f"""
    <div style="display: flex; gap: 8px; margin-bottom: 12px; align-items: center;">
        <span style="background-color: {s_bg}; color: {s_fg}; padding: 4px 10px; border-radius: 12px; font-size: 0.82rem; font-weight: 600; border: 1px solid {s_fg}40;">
            {s_txt}
        </span>
        <span style="background-color: {c_bg}; color: {c_fg}; padding: 4px 10px; border-radius: 12px; font-size: 0.82rem; font-weight: 600; border: 1px solid {c_fg}40;">
            {c_txt}
        </span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

