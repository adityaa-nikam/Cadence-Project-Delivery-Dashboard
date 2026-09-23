"""Actionable Risk Card component for Cadence enterprise UI."""

import streamlit as st


def render_risk_card(risk, compact: bool = False) -> None:
    """Render a clean, modern B2B SaaS risk card."""
    sev = getattr(risk, "severity", "MEDIUM").upper()

    if sev == "HIGH":
        sev_bg = "#FEF2F2"
        sev_fg = "#B91C1C"
        sev_border = "#FECACA"
        card_border = "#FCA5A5"
    elif sev == "MEDIUM":
        sev_bg = "#FFFBEB"
        sev_fg = "#B45309"
        sev_border = "#FDE68A"
        card_border = "#FCD34D"
    else:  # LOW
        sev_bg = "#F8FAFC"
        sev_fg = "#475569"
        sev_border = "#E2E8F0"
        card_border = "#CBD5E1"

    title = getattr(risk, "title", "Project Delivery Risk")
    impact = getattr(risk, "impact", "Potential delivery impact")
    action = getattr(risk, "recommended_action", "Review with lead owner")
    milestone = getattr(risk, "affected_milestone", "")

    milestone_html = f'<div style="font-size:11px; color:#64748B; margin-top:4px;">📋 Milestone: <strong>{milestone}</strong></div>' if milestone else ""

    st.markdown(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid {card_border}; border-radius:10px; padding:14px 16px; margin-bottom:10px; box-shadow:0 1px 2px rgba(0,0,0,0.02);">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
            <div style="font-weight:700; font-size:0.925rem; color:#0F172A;">⚠️ {title}</div>
            <span style="background:{sev_bg}; color:{sev_fg}; border:1px solid {sev_border}; padding:2px 8px; border-radius:6px; font-size:11px; font-weight:700;">
                {sev} SEVERITY
            </span>
        </div>
        <div style="font-size:0.825rem; color:#334155; margin-bottom:4px;">
            <strong>Impact:</strong> {impact}
        </div>
        <div style="font-size:0.825rem; color:#15803D; background:#F0FDF4; border:1px solid #BBF7D0; padding:6px 10px; border-radius:6px; margin-top:6px;">
            <strong>Recommended Action:</strong> {action}
        </div>
        {milestone_html}
    </div>
    """, unsafe_allow_html=True)
