"""Compact, modern enterprise page header component."""

import streamlit as st


def render_page_header(eyebrow: str, title: str, subtitle: str, action_label: str = "📥 Export Report (Demo)") -> bool:
    """
    Render compact header with eyebrow, title, subtitle, and right action button.
    Returns True if action button is clicked.
    """
    h_col1, h_col2 = st.columns([4, 1])

    action_clicked = False
    with h_col1:
        st.markdown(f"""
        <div style="margin-bottom: 12px;">
            <div style="font-size: 11px; font-weight: 700; color: #6366F1; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 2px;">
                {eyebrow}
            </div>
            <h1 style="font-size: 26px; font-weight: 800; color: #0F172A; margin: 0; letter-spacing: -0.02em; line-height: 1.2;">
                {title}
            </h1>
            <div style="font-size: 13px; color: #64748B; font-weight: 500; margin-top: 4px;">
                {subtitle}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with h_col2:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.button(action_label, key=f"hdr_btn_{title.lower().replace(' ', '_')}", type="secondary", use_container_width=True):
            action_clicked = True

    return action_clicked
