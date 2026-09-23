"""
AI Observability & Reliability Operations Center for Cadence Enterprise Platform.
"""

import json
import streamlit as st
from utils.database import get_db
from utils.db_models import ActivityEventDB, AIEventDB, ProposalDB


def render_observability_page() -> None:
    """Render the high-end enterprise AI Observability & Telemetry Center."""
    # Top Header
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div>
                <div style="font-size: 11px; font-weight: 700; color: #6366F1; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 2px;">
                    AI TELEMETRY & RELIABILITY OPERATIONS
                </div>
                <h1 style="font-size: 26px; font-weight: 800; color: #0F172A; margin: 0; letter-spacing: -0.02em;">
                    AI Observability Center
                </h1>
                <div style="font-size: 13px; color: #64748B; margin-top: 4px;">
                    Real-time execution metrics, LLM latency, confidence signals, human-in-the-loop approvals, and structured JSON logs.
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Fetch real telemetry from database
    with get_db() as session:
        ai_events = session.query(AIEventDB).order_by(AIEventDB.created_at.desc()).all()
        activities = session.query(ActivityEventDB).all()
        proposals = session.query(ProposalDB).all()

    total_events = len(ai_events)
    successful = sum(1 for e in ai_events if e.confidence and e.confidence >= 0.6)
    success_rate = (successful / total_events * 100) if total_events > 0 else 100.0

    latencies = [e.latency_ms for e in ai_events if e.latency_ms]
    avg_latency = round(sum(latencies) / len(latencies), 0) if latencies else 0

    confidences = [e.confidence for e in ai_events if e.confidence is not None]
    avg_conf = round((sum(confidences) / len(confidences)) * 100, 1) if confidences else 90.0

    approvals = sum(1 for a in activities if a.event_type == "MILESTONE_STATUS_CHANGE" and "Human approved" in (a.description or ""))
    rejections = sum(1 for a in activities if a.event_type == "AI_PROPOSAL_REJECTED")

    # 1. Top Metrics Bar (4 Required Metrics Cards)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("AI EVENTS", total_events)
    m2.metric("SUCCESS RATE", f"{success_rate:.1f}%")
    m3.metric("AVG LATENCY", f"{avg_latency:.0f} ms")
    m4.metric("AVG CONFIDENCE SIGNAL", f"{avg_conf:.1f}%")

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 2. LLM Task Breakdown
    st.markdown("<div style='font-size:14px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:12px;'>📊 LLM Task Type Breakdown</div>", unsafe_allow_html=True)
    task_counts = {}
    for e in ai_events:
        task_counts[e.event_type] = task_counts.get(e.event_type, 0) + 1

    if not task_counts:
        task_counts = {"STATUS_PARSING": 0, "RISK_EXTRACTION": 0, "CUSTOMER_EMAIL_DRAFT": 0}

    t_cols = st.columns(len(task_counts))
    for idx, (t_name, count) in enumerate(task_counts.items()):
        with t_cols[idx % len(t_cols)]:
            st.markdown(f"""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:14px 16px; text-align:center; box-shadow:0 1px 2px rgba(0,0,0,0.02);">
                <div style="font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase;">{t_name}</div>
                <div style="font-size:24px; font-weight:800; color:#4F46E5; margin-top:4px;">{count}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)

    # 3. Recent AI Execution Telemetry Table & Inspection
    st.markdown("<div style='font-size:14px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:12px;'>🔍 Recent AI Execution Logs & Structured JSON Telemetry</div>", unsafe_allow_html=True)

    if not ai_events:
        st.markdown("<div class='cadence-empty-state'>No AI telemetry events recorded yet. Log an AI update to populate live execution logs.</div>", unsafe_allow_html=True)
        return

    for event in ai_events[:15]:
        conf_pct = (event.confidence or 0.85) * 100
        conf_bg = "#F0FDF4" if conf_pct >= 85 else ("#FFFBEB" if conf_pct >= 60 else "#FEF2F2")
        conf_fg = "#15803D" if conf_pct >= 85 else ("#B45309" if conf_pct >= 60 else "#B91C1C")
        ts_date = str(event.created_at)[:19].replace("T", " ") if event.created_at else "Recent"

        header_str = f"⚡ {ts_date} | Task: {event.event_type} | Model: {event.model or 'llama-3.3-70b-versatile'} | Latency: {event.latency_ms:.0f}ms | Confidence: {conf_pct:.0f}%"

        with st.expander(header_str):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**Event ID:** `{event.id}`")
                st.markdown(f"**Project Target:** `{event.project_id}`")
                st.markdown(f"**Input Summary:** {event.input_summary or 'Raw update analysis request'}")
            with c2:
                st.markdown(f"""
                <span style="background:{conf_bg}; color:{conf_fg}; padding:4px 12px; border-radius:999px; font-size:12px; font-weight:700;">
                    ● Confidence: {conf_pct:.0f}%
                </span>
                """, unsafe_allow_html=True)

            st.markdown("**Structured Output JSON Payload:**")
            try:
                st.json(json.loads(event.structured_output))
            except Exception:
                st.code(event.structured_output or "{}")

