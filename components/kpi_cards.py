"""KPI metric cards component for Cadence enterprise portfolio overview."""

import streamlit as st


def render_kpi_cards(total: int, on_track: int, at_risk: int, delayed: int) -> None:
    """Render 4 compact, high-end B2B SaaS KPI cards."""
    col1, col2, col3, col4 = st.columns(4)

    cards_data = [
        ("TOTAL PROJECTS", total, "Active client delivery programs", "#0F172A", "#F8FAFC", "#E2E8F0"),
        ("ON TRACK", on_track, f"{(on_track/total*100):.0f}% of portfolio on schedule" if total > 0 else "Normal", "#15803D", "#F0FDF4", "#BBF7D0"),
        ("AT RISK", at_risk, "Requires proactive attention" if at_risk > 0 else "None", "#B45309", "#FFFBEB", "#FDE68A"),
        ("DELAYED", delayed, "Schedule slipping / critical block" if delayed > 0 else "None", "#B91C1C", "#FEF2F2", "#FECACA"),
    ]

    cols = [col1, col2, col3, col4]

    for idx, (label, val, note, text_color, bg_color, border_color) in enumerate(cards_data):
        with cols[idx]:
            st.markdown(f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 3px solid {text_color}; border-radius: 12px; padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px;">
                    {label}
                </div>
                <div style="font-size: 32px; font-weight: 800; color: {text_color}; line-height: 1.1; letter-spacing: -0.02em;">
                    {val}
                </div>
                <div style="font-size: 12px; color: #64748B; font-weight: 500; margin-top: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    {note}
                </div>
            </div>
            """, unsafe_allow_html=True)
