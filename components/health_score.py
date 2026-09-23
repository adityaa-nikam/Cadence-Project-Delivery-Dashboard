"""Visual health score widget for project delivery dashboard."""

import streamlit as st


def render_health_score(health: dict, project_status: str | None = None) -> None:
    """
    Display a modern visual health score widget using HTML + Streamlit.
    
    Args:
        health: Dict with keys: score, grade, reasoning, flags, error
        project_status: Optional overall project delivery status string
    """
    if not health:
        return
    
    score = health.get("score", 0)
    grade = health.get("grade", "Critical")
    reasoning = health.get("reasoning", "")
    flags = health.get("flags", [])
    
    # Theme configuration based on grade
    if grade == "Healthy":
        color = "#10B981"
        bg = "linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%)"
        border = "#A7F3D0"
        badge_bg = "#047857"
    elif grade == "At Risk":
        color = "#F59E0B"
        bg = "linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%)"
        border = "#FDE68A"
        badge_bg = "#B45309"
    else:  # Critical
        color = "#EF4444"
        bg = "linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%)"
        border = "#FECACA"
        badge_bg = "#B91C1C"
    
    status_context = f"Target Delivery Status: <strong>{project_status}</strong> &nbsp;•&nbsp; " if project_status else ""

    # Main health score card
    st.markdown(f"""
    <div style="background:{bg}; border:1px solid {border}; border-radius:16px; padding:20px 24px; margin-bottom:16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
        <div style="display:flex; align-items:center; gap:24px; flex-wrap:wrap;">
            <div style="text-align:center; min-width:90px; background: #FFFFFF; padding: 12px 16px; border-radius: 14px; border: 1px solid {border}; box-shadow: 0 2px 4px rgba(0,0,0,0.04);">
                <div style="font-size:42px; font-weight:800; color:{color}; line-height:1; font-family:'Plus Jakarta Sans', sans-serif;">
                    {score}
                </div>
                <div style="font-size:10px; color:#64748B; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; margin-top:4px;">Engine Score</div>
            </div>
            <div style="flex:1;">
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
                    <span style="background:{badge_bg}; color:#FFFFFF; font-size:12px; font-weight:700; padding:3px 12px; border-radius:999px; text-transform:uppercase; letter-spacing:0.05em;">
                        {grade}
                    </span>
                    <span style="font-size:13px; color:#475569; font-weight:600;">{status_context}Deterministic AI Engine Assessment</span>
                </div>
                <div style="font-size:14px; color:#334155; line-height:1.5; font-weight:500;">{reasoning}</div>
                <div style="font-size:11px; color:#64748B; font-style:italic; margin-top:6px;">
                    💡 <em>Note: Project Target Status reflects manual delivery tracking, whereas Health Score is deterministically derived from active blockages, issue severity, and update recency.</em>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Warning flags
    if flags:
        flag_html = "".join([
            f'<div style="background:#FFFBEB; border:1px solid #FDE68A; color:#92400E; font-size:12px; font-weight:600; padding:6px 12px; border-radius:8px; display:inline-flex; align-items:center; gap:6px; margin-right:8px; margin-bottom:8px;">⚠️ {flag}</div>'
            for flag in flags
        ])
        st.markdown(f'<div style="margin-bottom:16px;">{flag_html}</div>', unsafe_allow_html=True)