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
    grade = str(health.get("grade", "C")).strip()
    reasoning = health.get("reasoning", "")
    flags = health.get("flags", [])

    # Dynamic Theme configuration based on Score & Grade
    if score >= 85 or grade in ("A", "Healthy", "On Track"):
        color = "#10B981"
        bg = "linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%)"
        border = "#86EFAC"
        badge_bg = "#15803D"
        display_grade = "Grade A (Healthy)" if grade == "A" else grade
    elif score >= 65 or grade in ("B", "C", "At Risk"):
        color = "#F59E0B"
        bg = "linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%)"
        border = "#FDE68A"
        badge_bg = "#B45309"
        display_grade = f"Grade {grade} (At Risk)" if grade in ("B", "C") else grade
    else:  # Critical / Delayed
        color = "#EF4444"
        bg = "linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%)"
        border = "#FECACA"
        badge_bg = "#B91C1C"
        display_grade = f"Grade {grade} (Critical)" if grade in ("D", "F") else grade

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
                        {display_grade}
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

    # Flags Pills
    if flags:
        flag_pills = []
        for flag in flags:
            if "DELIVERABLES" in flag or "COMPLETED" in flag or "DONE" in flag:
                pill = f'<div style="background:#F0FDF4; border:1px solid #86EFAC; color:#15803D; font-size:12px; font-weight:600; padding:6px 12px; border-radius:8px; display:inline-flex; align-items:center; gap:6px; margin-right:8px; margin-bottom:8px;">✅ {flag}</div>'
            else:
                pill = f'<div style="background:#FFFBEB; border:1px solid #FDE68A; color:#92400E; font-size:12px; font-weight:600; padding:6px 12px; border-radius:8px; display:inline-flex; align-items:center; gap:6px; margin-right:8px; margin-bottom:8px;">⚠️ {flag}</div>'
            flag_pills.append(pill)
        st.markdown(f'<div style="margin-bottom:16px;">{"".join(flag_pills)}</div>', unsafe_allow_html=True)