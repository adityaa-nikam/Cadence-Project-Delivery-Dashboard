"""Visual project delivery timeline component with bottom-to-top execution progress bar."""

from datetime import datetime
import streamlit as st


def render_project_timeline(project, milestones: list, updates: list, activities: list) -> None:
    """Render a clean, visual milestone execution timeline with bottom-to-top vertical progress line."""
    # Compute milestone completion percentage
    total_ms = len(milestones)
    done_ms = sum(1 for m in milestones if m.status == "Done")
    pct = int((done_ms / total_ms) * 100) if total_ms > 0 else 0

    st.markdown("<h3 style='font-size:1.25rem; font-weight:700; color:#0F172A; margin-top:1.5rem; margin-bottom:0.5rem;'>🗓️ Visual Project Delivery Timeline</h3>", unsafe_allow_html=True)

    # Header bar showing execution progress percentage
    progress_header_html = (
        f'<div style="display:flex; justify-content:space-between; align-items:center; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:12px 16px; margin-bottom:16px; box-shadow:0 1px 2px rgba(0,0,0,0.02);">'
        f'<div>'
        f'<div style="font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.04em;">Timeline Execution Flow</div>'
        f'<div style="font-size:14px; font-weight:800; color:#0F172A;">Bottom-to-Top Vertical Progress Line</div>'
        f'</div>'
        f'<div style="display:flex; align-items:center; gap:12px;">'
        f'<span style="font-size:13px; font-weight:800; color:#10B981;">{pct}% Completed ({done_ms}/{total_ms} Milestones)</span>'
        f'<div style="width:130px; height:8px; background:#E2E8F0; border-radius:999px; overflow:hidden;">'
        f'<div style="width:{pct}%; height:100%; background:linear-gradient(90deg, #4F46E5, #10B981); border-radius:999px;"></div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(progress_header_html, unsafe_allow_html=True)

    events = []

    # 1. Project Kickoff / Creation Event (Origin at Bottom)
    events.append({
        "date": "2026-07-01",
        "title": "🚀 Project Kickoff & Workspace Created",
        "type": "Kickoff",
        "is_completed": True,
        "dot_color": "#4F46E5",
        "dot_shadow": "0 0 0 3px rgba(79,70,229,0.25)",
        "badge_bg": "#EEF2FF",
        "badge_fg": "#3730A3",
        "detail": f"Lead Owner: {', '.join(project.owners)}",
    })

    # 2. Milestones
    for m in milestones:
        if m.status == "Done":
            events.append({
                "date": m.due_date or "2026-08-01",
                "title": f"✅ Milestone Completed: {m.title}",
                "type": "Milestone",
                "is_completed": True,
                "dot_color": "#10B981",
                "dot_shadow": "0 0 0 3px rgba(16,185,129,0.25)",
                "badge_bg": "#ECFDF5",
                "badge_fg": "#047857",
                "detail": f"Status: {m.status} • Due {m.due_date}",
            })
        elif m.status == "Blocked":
            events.append({
                "date": m.due_date or "2026-08-15",
                "title": f"🚧 Milestone Blocked: {m.title}",
                "type": "Blocker",
                "is_completed": False,
                "dot_color": "#EF4444",
                "dot_shadow": "0 0 0 3px rgba(239,68,68,0.25)",
                "badge_bg": "#FEF2F2",
                "badge_fg": "#B91C1C",
                "detail": f"Status: {m.status} • Due {m.due_date}",
            })
        else:
            events.append({
                "date": m.due_date or "2026-09-01",
                "title": f"📋 Target Milestone: {m.title}",
                "type": "Target",
                "is_completed": False,
                "dot_color": "#94A3B8",
                "dot_shadow": "0 0 0 2px #F1F5F9",
                "badge_bg": "#FFFBEB",
                "badge_fg": "#B45309",
                "detail": f"Status: {m.status} • Due {m.due_date}",
            })

    # 3. Recent Activity Logs
    for act in activities[:5]:
        ts_date = act.timestamp[:10] if getattr(act, "timestamp", "") else "2026-09-01"
        events.append({
            "date": ts_date,
            "title": f"⚡ Activity: {act.event_type}",
            "type": "Activity",
            "is_completed": True,
            "dot_color": "#6366F1",
            "dot_shadow": "0 0 0 2px rgba(99,102,241,0.2)",
            "badge_bg": "#F1F5F9",
            "badge_fg": "#334155",
            "detail": f"{act.description} ({act.source})",
        })

    # Sort events by date reverse (newest at top, oldest/kickoff at bottom)
    try:
        sorted_events = sorted(events, key=lambda e: e["date"], reverse=True)
    except Exception:
        sorted_events = events

    # Render CSS Timeline with Dead-Center Aligned 4px Vertical Progress Bar
    st.markdown("""
<style>
.timeline-wrapper {
    position: relative;
    padding: 16px 20px;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}
.timeline-container {
    position: relative;
    padding-left: 36px;
    margin-top: 12px;
    margin-bottom: 8px;
}
/* Static background track line on left vertical axis */
.timeline-track-bg {
    position: absolute;
    left: 11px;
    top: 18px;
    bottom: 22px;
    width: 4px;
    background: #E2E8F0;
    border-radius: 999px;
    z-index: 1;
}
/* Active vertical progress bar filling UPWARDS from bottom to top */
.timeline-progress-fill {
    position: absolute;
    left: 11px;
    bottom: 22px;
    width: 4px;
    background: linear-gradient(0deg, #4F46E5 0%, #10B981 100%);
    border-radius: 999px;
    z-index: 2;
    transition: height 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 0 6px rgba(16, 185, 129, 0.35);
}
.timeline-item {
    position: relative;
    margin-bottom: 18px;
}
.timeline-item:last-child {
    margin-bottom: 4px;
}
/* Dots positioned DEAD CENTER on the 4px vertical progress line (Center = 13px) */
.timeline-dot {
    position: absolute;
    left: -30px;
    top: 12px;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid #FFFFFF;
    z-index: 3;
    transition: all 0.2s ease;
}
</style>
""", unsafe_allow_html=True)

    timeline_html_items = []
    for ev in sorted_events:
        item = (
            f'<div class="timeline-item">'
            f'<div class="timeline-dot" style="background:{ev["dot_color"]}; box-shadow:{ev["dot_shadow"]};"></div>'
            f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:10px 14px; box-shadow:0 1px 2px rgba(0,0,0,0.02);">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">'
            f'<span style="font-weight:700; font-size:0.9rem; color:#0F172A;">{ev["title"]}</span>'
            f'<span style="background:{ev["badge_bg"]}; color:{ev["badge_fg"]}; padding:2px 8px; border-radius:6px; font-size:11px; font-weight:700;">{ev["date"]}</span>'
            f'</div>'
            f'<div style="font-size:0.8125rem; color:#64748B;">{ev["detail"]}</div>'
            f'</div>'
            f'</div>'
        )
        timeline_html_items.append(item)

    # Calculate vertical progress fill height percentage from bottom (Kickoff) up to current completion stage
    fill_height = max(12, min(100, pct))

    container_html = (
        f'<div class="timeline-wrapper">'
        f'<div class="timeline-container">'
        f'<div class="timeline-track-bg"></div>'
        f'<div class="timeline-progress-fill" style="height: {fill_height}%;"></div>'
        f'{"".join(timeline_html_items)}'
        f'</div>'
        f'</div>'
    )
    st.markdown(container_html, unsafe_allow_html=True)


