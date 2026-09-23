"""High-density B2B SaaS Project Card component."""

import streamlit as st
from components.status_badge import get_status_badge_html


def render_project_card(project, milestones: list, issues: list, updates: list, health: dict) -> bool:
    """
    Render a compact, high-density project card for the portfolio grid.
    Returns True if 'View Details ->' button is clicked.
    """
    total_ms = len(milestones)
    done_ms = sum(1 for m in milestones if m.status == "Done")
    blocked_ms = sum(1 for m in milestones if m.status == "Blocked")
    pct = (done_ms / total_ms) if total_ms > 0 else 0

    high_issues = sum(1 for i in issues if getattr(i, "severity", "").upper() == "HIGH")
    last_upd = project.last_update[:10] if getattr(project, "last_update", "") else "Recent"
    score = health.get("score", 100)
    grade = health.get("grade", "Healthy")

    badge_html = get_status_badge_html(project.overall_status, compact=True)

    issue_flag = ""
    if high_issues > 0:
        issue_flag = f'<span style="background:#FEF2F2; color:#B91C1C; border:1px solid #FECACA; font-size:11px; font-weight:700; padding:2px 8px; border-radius:6px; display:inline-flex; align-items:center; gap:4px;">⚠️ {high_issues} High Issue</span>'
    elif blocked_ms > 0:
        issue_flag = f'<span style="background:#FEF2F2; color:#B91C1C; border:1px solid #FECACA; font-size:11px; font-weight:700; padding:2px 8px; border-radius:6px; display:inline-flex; align-items:center; gap:4px;">🚧 {blocked_ms} Blocked</span>'

    score_color = "#15803D" if score >= 80 else ("#B45309" if score >= 50 else "#B91C1C")

    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px 20px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.03); transition: all 0.2s ease;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <div>
                <div style="font-size: 16px; font-weight: 800; color: #0F172A; letter-spacing: -0.01em;">{project.name}</div>
                <div style="font-size: 12px; color: #64748B; margin-top: 2px;">Lead: <strong style="color:#334155;">{', '.join(project.owners)}</strong></div>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                {issue_flag}
                {badge_html}
            </div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #475569; margin-top: 12px; margin-bottom: 6px;">
            <span>Milestones: <strong>{done_ms}/{total_ms} ({pct*100:.0f}%)</strong></span>
            <span>Health: <strong style="color:{score_color}; font-weight:800;">{score}/100</strong> ({grade})</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Streamlit native progress bar & View details button
    p_col1, p_col2 = st.columns([4, 1])
    with p_col1:
        st.progress(pct)
    with p_col2:
        clicked = st.button("View Details →", key=f"btn_pcard_{project.id}", type="secondary", use_container_width=True)

    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
    return clicked
