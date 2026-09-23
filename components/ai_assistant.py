"""Enterprise AI Delivery Assistant component for Cadence dashboard."""

import streamlit as st
from ai_helper import query_projects


def _on_chip_click(q_text: str) -> None:
    """Callback triggered when a suggested query chip is clicked."""
    st.session_state["nl_query_field"] = q_text
    st.session_state["pending_query_run"] = q_text


def _on_ask_click() -> None:
    """Callback triggered when the Ask AI Assistant button is clicked."""
    user_q = st.session_state.get("nl_query_field", "").strip()
    if user_q:
        st.session_state["pending_query_run"] = user_q


def render_ai_delivery_assistant(projects: list, milestones: list, issues: list, updates: list) -> None:
    """Render the enterprise AI Delivery Assistant utility panel."""
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
            <div style="background:#EEF2FF; color:#4F46E5; width:28px; height:28px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:14px;">
                ✨
            </div>
            <div style="font-size: 15px; font-weight: 800; color: #0F172A;">AI Delivery Assistant</div>
        </div>
        <div style="font-size: 12px; color: #64748B; margin-bottom: 12px;">
            Ask natural-language questions about project risks, blockers, owners, and status.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Suggested Query Chips
    st.markdown("<div style='font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px;'>Suggested Queries:</div>", unsafe_allow_html=True)

    queries = [
        "Which projects are blocked?",
        "What's at risk?",
        "Who owns Orion Logistics?",
        "Which projects have open bugs?"
    ]

    q_cols = st.columns(2)
    for idx, q_text in enumerate(queries):
        with q_cols[idx % 2]:
            st.button(
                f"🔍 {q_text}",
                key=f"chip_q_{idx}",
                type="secondary",
                use_container_width=True,
                on_click=_on_chip_click,
                args=(q_text,)
            )

    if "nl_query_field" not in st.session_state:
        st.session_state["nl_query_field"] = ""

    st.text_input(
        "Ask about portfolio status",
        placeholder="e.g. Which projects are blocked by firewall rules?",
        key="nl_query_field",
        label_visibility="collapsed"
    )

    st.button(
        "✨ Ask AI Assistant",
        key="btn_ask_ai_nl",
        type="primary",
        use_container_width=True,
        on_click=_on_ask_click
    )

    query_to_run = st.session_state.pop("pending_query_run", None)

    if query_to_run:
        with st.spinner("🔍 Querying portfolio database..."):
            answer = query_projects(query_to_run, projects, milestones, issues, updates)
            st.session_state["nl_query_answer"] = {
                "query": query_to_run,
                "answer": answer
            }

    if "nl_query_answer" in st.session_state:
        ans_data = st.session_state["nl_query_answer"]
        st.markdown(f"""
<div style="background: #F8FAFC; border: 1px solid #C7D2FE; border-radius: 10px; padding: 14px 16px; margin-top: 12px;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <span style="background:#EEF2FF; color:#3730A3; border:1px solid #C7D2FE; padding:2px 8px; border-radius:6px; font-size:10px; font-weight:700; text-transform:uppercase;">
            FACTUAL DATABASE RESULT
        </span>
        <span style="font-size:11px; color:#64748B;">Query: "{ans_data['query']}"</span>
    </div>
    <div style="font-size: 13px; color: #1E1B4B; line-height: 1.5; font-weight: 500;">
        {ans_data['answer']}
    </div>
</div>
""", unsafe_allow_html=True)

