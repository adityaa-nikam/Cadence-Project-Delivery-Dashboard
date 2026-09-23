"""
Filterable Project Overview & Portfolio Dashboard for Cadence Enterprise Platform.
"""

from datetime import datetime
import streamlit as st

from components.ai_assistant import render_ai_delivery_assistant
from components.header import render_page_header
from components.kpi_cards import render_kpi_cards
from components.project_card import render_project_card
from components.status_badge import get_status_badge_html
from utils import services
from utils.state import get_or_compute_health


def is_project_stale(project_id, updates, days_threshold=7):
    """Check if a project has no updates within the threshold days."""
    project_updates = [u for u in updates if u.project_id == project_id]
    if not project_updates:
        return True
    latest = max(project_updates, key=lambda u: u.timestamp)
    try:
        latest_dt = datetime.fromisoformat(latest.timestamp)
        return (datetime.now() - latest_dt).days > days_threshold
    except Exception:
        return False


def render_overview() -> None:
    """Render the high-end enterprise portfolio dashboard."""
    # 1. Top Header Banner
    export_clicked = render_page_header(
        eyebrow="GLOBAL DELIVERY PORTFOLIO",
        title="Project Delivery Dashboard",
        subtitle="Unified visibility across active client delivery programs.",
        action_label="📥 Export Report (Demo)"
    )
    if export_clicked:
        st.toast("📥 Executive Portfolio Report exported successfully (Demo Mode)", icon="✅")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 2. Portfolio Datasets & Stats
    all_projects = services.get_projects()
    all_milestones = []
    all_updates = []
    all_issues = []
    for p in all_projects:
        all_milestones.extend(services.get_project_milestones(p.id))
        all_updates.extend(services.get_project_updates(p.id))
        all_issues.extend(services.get_project_issues(p.id))

    total = len(all_projects)
    on_track = sum(1 for p in all_projects if p.overall_status == "On Track")
    at_risk = sum(1 for p in all_projects if p.overall_status == "At Risk")
    delayed = sum(1 for p in all_projects if p.overall_status == "Delayed")

    # 3. KPI Metrics Row (4 Compact KPI Cards)
    render_kpi_cards(total=total, on_track=on_track, at_risk=at_risk, delayed=delayed)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # 4. Main Two-Column Layout (Left ~65%, Right ~35%)
    left_col, right_col = st.columns([1.85, 1])

    # ----------------------------------------------------
    # LEFT COLUMN — ACTIVE DELIVERY PORTFOLIO
    # ----------------------------------------------------
    with left_col:
        # Header & Filter Bar
        f_head_col, f_select_col = st.columns([2, 1])
        with f_head_col:
            st.markdown("""
            <div style="margin-bottom: 8px;">
                <div style="font-size: 16px; font-weight: 800; color: #0F172A; letter-spacing: -0.01em;">ACTIVE DELIVERY PORTFOLIO</div>
                <div style="font-size: 13px; color: #64748B;">Current delivery status across client projects.</div>
            </div>
            """, unsafe_allow_html=True)

        with f_select_col:
            selected_filter = st.selectbox(
                "Filter portfolio status",
                ["All Projects", "On Track", "At Risk", "Delayed"],
                label_visibility="collapsed",
                key="portfolio_status_filter"
            )

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        # Filter Projects via Database Query
        filtered_projects = services.get_projects(selected_filter)

        if not filtered_projects:
            st.markdown("""
            <div class="cadence-empty-state">
                No active projects match the selected status filter.
            </div>
            """, unsafe_allow_html=True)
        else:
            for project in filtered_projects:
                p_milestones = services.get_project_milestones(project.id)
                p_issues = services.get_project_issues(project.id)
                p_updates = services.get_project_updates(project.id)
                p_health = get_or_compute_health(project.id, project, p_milestones, p_issues, p_updates)

                # Render dense B2B SaaS project card
                clicked = render_project_card(project, p_milestones, p_issues, p_updates, p_health)
                if clicked:
                    st.session_state["selected_project_id"] = project.id
                    st.rerun()

    # ----------------------------------------------------
    # RIGHT COLUMN — DELIVERY ATTENTION & AI UTILITIES
    # ----------------------------------------------------
    with right_col:
        # Delivery Attention Section
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size: 14px; font-weight: 800; color: #0F172A; letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 12px; display:flex; align-items:center; justify-content:space-between;">
                <span>🎯 DELIVERY ATTENTION</span>
                <span style="font-size: 11px; background: #FEF2F2; color: #B91C1C; padding: 2px 8px; border-radius: 6px; font-weight: 700;">Action Required</span>
            </div>
        """, unsafe_allow_html=True)

        # 1. High Priority Blocked Milestones / High Severity Issues
        high_priority_items = []
        for p in all_projects:
            p_issues = services.get_project_issues(p.id)
            p_ms = services.get_project_milestones(p.id)
            blocked = [m for m in p_ms if m.status == "Blocked"]
            high_iss = [i for i in p_issues if getattr(i, "severity", "").upper() == "HIGH"]
            if blocked or high_iss:
                high_priority_items.append((p, blocked, high_iss))

        if high_priority_items:
            st.markdown("<div style='font-size:11px; font-weight:700; color:#B91C1C; text-transform:uppercase; margin-bottom:6px;'>⚠️ HIGH PRIORITY BLOCKERS</div>", unsafe_allow_html=True)
            for p, blocked, high_iss in high_priority_items[:2]:
                desc = []
                if blocked:
                    desc.append(f"{len(blocked)} blocked milestone(s)")
                if high_iss:
                    desc.append(f"{len(high_iss)} high-severity issue(s)")

                st.markdown(f"""
                <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:8px; padding:10px 12px; margin-bottom:8px; font-size:12px;">
                    <div style="font-weight:700; color:#0F172A;">{p.name}</div>
                    <div style="color:#B91C1C; margin-top:2px;">{", ".join(desc)}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"View {p.name} →", key=f"att_btn_{p.id}", type="secondary", use_container_width=True):
                    st.session_state["selected_project_id"] = p.id
                    st.rerun()

        # 2. Upcoming Milestones
        upcoming_ms = [m for m in all_milestones if m.status != "Done" and m.due_date]
        upcoming_ms.sort(key=lambda x: x.due_date)
        if upcoming_ms:
            st.markdown("<div style='font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase; margin-top:12px; margin-bottom:6px;'>📅 UPCOMING MILESTONES</div>", unsafe_allow_html=True)
            for m in upcoming_ms[:2]:
                st.markdown(f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:8px 12px; margin-bottom:6px; font-size:12px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:700; color:#0F172A;">{m.title}</div>
                        <div style="color:#64748B; font-size:11px;">Due {m.due_date}</div>
                    </div>
                    <div>{get_status_badge_html(m.status, compact=True)}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # AI Delivery Assistant Utility Panel
        render_ai_delivery_assistant(all_projects, all_milestones, all_issues, all_updates)

        # Staleness Intelligence Alert Panel
        stale_items = []
        for p in all_projects:
            p_upds = services.get_project_updates(p.id)
            if is_project_stale(p.id, p_upds, days_threshold=7):
                p_ms = services.get_project_milestones(p.id)
                open_count = sum(1 for m in p_ms if m.status != "Done")
                stale_items.append((p, open_count))

        if stale_items:
            st.markdown("""
            <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 12px; padding: 16px; margin-top: 16px;">
                <div style="font-size: 11px; font-weight: 700; color: #B45309; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px;">
                    ⏱️ STALENESS INTELLIGENCE
                </div>
            """, unsafe_allow_html=True)

            for sp, affected_count in stale_items:
                st.markdown(f"""
                <div style="margin-bottom: 10px; border-bottom: 1px dashed #FDE68A; padding-bottom: 8px;">
                    <div style="font-size: 13px; font-weight: 700; color: #0F172A;">{sp.name}</div>
                    <div style="font-size: 12px; color: #475569; margin-top: 2px;">
                        No update for >7 days • Owner: <strong>{", ".join(sp.owners)}</strong><br/>
                        Affected Milestones: <strong>{affected_count} open</strong>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Draft Reminder for {sp.name} (Demo)", key=f"stale_rem_{sp.id}", type="secondary", use_container_width=True):
                    st.toast(f"Status update reminder drafted for {sp.name} lead ({', '.join(sp.owners)})!", icon="📩")

            st.markdown("</div>", unsafe_allow_html=True)