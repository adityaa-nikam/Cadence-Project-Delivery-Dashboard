"""
Project Detail & Delivery Workspace for Cadence Enterprise Platform.
"""

from datetime import datetime
import streamlit as st

from ai_helper import draft_customer_email
from components.health_score import render_health_score
from components.issue_badge import render_issue
from components.milestone_card import render_milestone
from components.risk_card import render_risk_card
from components.status_badge import get_status_badge_html
from components.timeline import render_project_timeline
from components.update_feed import customer_safe_updates, render_update_entry
from utils import risk_engine, services
from utils.demo_mode import get_demo_scenarios_for_project
from utils.state import (
    get_issues,
    get_milestones,
    get_or_compute_health,
    get_project,
    get_updates,
)


def _render_back_button():
    """Render top level navigation bar."""
    col1, _ = st.columns([2, 8])
    with col1:
        if st.button("← Back to Portfolio", key="back_all_projects", type="secondary"):
            st.session_state["selected_project_id"] = None
            st.rerun()


def render_detail() -> None:
    """Render the selected project's enterprise delivery workspace."""
    _render_back_button()

    project_id = st.session_state.get("selected_project_id")
    project = get_project(project_id)
    if project is None:
        st.session_state["selected_project_id"] = None
        st.rerun()

    # 1. Project Title & Delivery Status Header
    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px 24px; margin-top: 8px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem;">
            <div>
                <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px;">PROJECT DELIVERY WORKSPACE</div>
                <h1 style="font-size: 26px; font-weight: 800; color: #0F172A; margin: 0; letter-spacing: -0.02em;">{project.name}</h1>
                <div style="font-size: 13px; color: #64748B; margin-top: 4px;">
                    Lead Owner: <strong style="color:#334155;">{', '.join(project.owners)}</strong>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:12px;">
                {get_status_badge_html(project.overall_status)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Fetch project data models
    milestones = get_milestones(project_id)
    issues = get_issues(project_id)
    updates = get_updates(project_id)
    activities = services.get_activity_history(project_id)
    health = get_or_compute_health(project_id, project, milestones, issues, updates)

    # 2. Delivery Health Card
    render_health_score(health, project.overall_status)

    # 3. Project Snapshot KPI Mini-Cards
    total_ms = len(milestones)
    done_ms = sum(1 for m in milestones if m.status == "Done")
    blocked_ms = sum(1 for m in milestones if m.status == "Blocked")
    high_issues = sum(1 for i in issues if getattr(i, "severity", "").upper() == "HIGH")
    pct = (done_ms / total_ms) if total_ms > 0 else 0
    last_upd_str = project.last_update[:10] if getattr(project, "last_update", "") else "Recent"

    sn1, sn2, sn3, sn4 = st.columns(4)
    sn1.metric("Milestone Completion", f"{done_ms} / {total_ms}", f"{pct*100:.0f}% Done")
    sn2.metric("Blocked Tasks", blocked_ms, delta=f"-{blocked_ms}" if blocked_ms > 0 else None, delta_color="inverse")
    sn3.metric("High Severity Issues", high_issues, delta=f"-{high_issues}" if high_issues > 0 else None, delta_color="inverse")
    sn4.metric("Last Activity Log", last_upd_str)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 4. View Perspective Switch (Internal vs Customer Portal)
    v_col1, v_col2 = st.columns([3, 2])
    with v_col1:
        st.markdown("<div style='font-size:14px; font-weight:700; color:#0F172A; margin-top:4px;'>Dashboard View Perspective</div>", unsafe_allow_html=True)
    with v_col2:
        current_mode = st.session_state.get("view_mode", "internal")
        view_choice = st.radio(
            "Dashboard View Mode",
            ["🔒 Internal View", "👤 Customer View"],
            index=0 if current_mode == "internal" else 1,
            horizontal=True,
            key="detail_view_mode",
            label_visibility="collapsed",
        )
    show_internal = view_choice == "🔒 Internal View"
    st.session_state["view_mode"] = "internal" if show_internal else "customer"

    if show_internal:
        with st.expander("🔒 Internal Team Engineering Context & Notes", expanded=True):
            st.markdown(f"<div style='font-size:0.9rem; color:#334155; line-height:1.5;'>{project.internal_notes}</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%); color: white; padding: 16px 20px; border-radius: 12px; margin-bottom: 1rem; box-shadow: 0 4px 6px -1px rgba(79,70,229,0.2);">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.9;">Verified Client Portal</div>
            <h3 style="margin: 2px 0 0; color: white; font-weight: 800; font-size: 1.15rem;">Customer Delivery Status Report</h3>
            <p style="margin: 4px 0 0; opacity: 0.9; font-size: 0.85rem;">Verified project delivery timeline and progress updates. Internal notes and AI raw prompts are strictly hidden.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 5. Visual Project Delivery Timeline
    render_project_timeline(project, milestones, updates, activities)

    visible_milestone_titles = {milestone.title for milestone in milestones if not milestone.internal_only}

    # 6. Milestones & Deliverables
    st.markdown("<div style='font-size:15px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.04em; margin-top:20px; margin-bottom:12px;'>📋 Milestones & Deliverables</div>", unsafe_allow_html=True)
    if not show_internal:
        st.caption("Showing customer-visible milestones only")
    for milestone in milestones:
        render_milestone(milestone, show_internal)

    # 7. AI Customer Status Draft Workspace (Internal View Only)
    if show_internal:
        st.markdown("<hr style='border-color:#E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px 20px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
                <div>
                    <div style="font-size: 15px; font-weight: 800; color: #0F172A;">📧 AI Customer Status Draft Workspace</div>
                    <div style="color: #64748B; font-size: 13px; margin-top: 2px;">Generate an executive-ready customer update grounded in database milestones. (Requires human review before sending)</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        d_col1, d_col2 = st.columns([3, 1])
        with d_col1:
            st.markdown("<div style='font-size:12px; color:#475569; margin-top:6px;'>AI evaluates recent milestones, open blockages, and progress to calibrate tone (Positive, Cautious, or Urgent).</div>", unsafe_allow_html=True)
        with d_col2:
            generate_btn = st.button(
                "✨ Draft Customer Email", 
                key=f"draft_email_{project_id}",
                type="primary",
                use_container_width=True
            )

        email_cache_key = f"email_draft_{project_id}"
        if generate_btn:
            with st.spinner("✍️ Drafting executive customer update..."):
                result = draft_customer_email(project, milestones, issues, updates)
                st.session_state[email_cache_key] = result

        if email_cache_key in st.session_state:
            draft = st.session_state[email_cache_key]
            if draft.get("error") and not draft.get("body"):
                st.error(f"Could not generate email: {draft['error']}")
            else:
                tone = draft.get("tone", "cautious")
                tone_bg = "#ECFDF5" if tone == "positive" else ("#FFFBEB" if tone == "cautious" else "#FEF2F2")
                tone_fg = "#047857" if tone == "positive" else ("#B45309" if tone == "cautious" else "#B91C1C")

                st.markdown(f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:16px; margin-top:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span style="font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase;">Email Preview (Human Review Mandatory)</span>
                        <span style="background:{tone_bg}; color:{tone_fg}; padding:2px 10px; border-radius:999px; font-size:11px; font-weight:700;">
                            ● {tone.capitalize()} Tone Calibrated
                        </span>
                    </div>
                    <div style="font-size:14px; font-weight:700; color:#0F172A; margin-bottom:8px;">Subject: {draft['subject']}</div>
                </div>
                """, unsafe_allow_html=True)

                st.text_area(
                    "Email Body (editable before sending):",
                    value=draft["body"].replace("\\n", "\n"),
                    height=200,
                    key=f"email_body_edit_{project_id}"
                )
                st.warning("⚠️ Human review required before sending. Verify all details against customer terms.")

    # 8. Active Project Risks (Internal View Only)
    project_risks = risk_engine.get_project_risks(project.id)
    if show_internal:
        st.markdown("<hr style='border-color:#E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:15px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:12px;'>⚠️ Active Project Risks & Actionable Recommendations</div>", unsafe_allow_html=True)

        if not project_risks:
            st.info("No active risks currently flagged for this project.")
        else:
            r_col1, r_col2 = st.columns(2)
            for r_idx, risk in enumerate(project_risks):
                with (r_col1 if r_idx % 2 == 0 else r_col2):
                    render_risk_card(risk)

    # 9. AI Update Processing Pipeline & Proposal Review
    st.markdown("<hr style='border-color:#E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:15px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:12px;'>🤖 AI Update Processing Pipeline</div>", unsafe_allow_html=True)

    applied_summary_key = f"last_applied_summary_{project.id}"
    if applied_summary_key in st.session_state:
        last_summary = st.session_state.pop(applied_summary_key)
        applied_html = (
            f'<div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:10px; padding:16px; margin-bottom:16px;">'
            f'<div style="font-size:11px; font-weight:700; color:#166534; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px;">✅ AI UPDATE APPLIED & AUDITED</div>'
            f'<div style="font-size:13px; color:#14532D; line-height:1.5;">'
            f'<strong>Summary:</strong> {last_summary.get("summary")}<br/>'
            f'{"<br/>".join(["✓ Applied: " + c for c in last_summary.get("applied_changes", [])])}'
            f'{("<br/>" + "<br/>".join(["✗ Rejected: " + r for r in last_summary.get("rejected_changes", [])])) if last_summary.get("rejected_changes") else ""}'
            f'</div>'
            f'</div>'
        )
        st.markdown(applied_html, unsafe_allow_html=True)

    proposal_state_key = f"pending_proposal_{project.id}"

    if show_internal:
        # Step 1: Demo Scenarios & Natural Language Input
        demo_scenarios = get_demo_scenarios_for_project(project.id)
        if demo_scenarios:
            st.markdown("<div style='font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase; margin-bottom:6px;'>⚡ Demo Scenarios:</div>", unsafe_allow_html=True)
            scen_cols = st.columns(len(demo_scenarios))
            for s_idx, scen in enumerate(demo_scenarios):
                with scen_cols[s_idx]:
                    if st.button(f"⚡ {scen['title'][:25]}...", key=f"demo_scen_{project.id}_{s_idx}", type="secondary", use_container_width=True):
                        scen_text = scen.get("raw_text") or scen.get("text", "")
                        st.session_state[f"update_input_field_{project.id}"] = scen_text
                        try:
                            res = services.create_ai_proposal_service(project.id, scen_text.strip())
                            st.session_state[proposal_state_key] = res
                        except Exception as ex:
                            st.error(f"Failed to analyze demo scenario: {str(ex)}")
                        st.rerun()

        with st.form(f"update_form_{project.id}"):
            st.markdown("<div style='font-size:13px; font-weight:600; color:#334155; margin-bottom:4px;'>Step 1: Paste natural-language update (Email, Slack note, or Call summary)</div>", unsafe_allow_html=True)
            current_input_val = st.session_state.get(f"update_input_field_{project.id}", "")
            raw_text = st.text_area(
                "Raw update content",
                value=current_input_val,
                height=100,
                placeholder="e.g., Firewall approval is complete and integration testing is now unblocked.",
                key=f"update_input_field_{project.id}",
                label_visibility="collapsed"
            )
            submit = st.form_submit_button("✨ Step 2: Analyze Update with AI", type="primary")
            if submit and raw_text.strip():
                try:
                    res = services.create_ai_proposal_service(project.id, raw_text.strip())
                    st.session_state[proposal_state_key] = res
                    st.rerun()
                except Exception as ex:
                    st.error(f"Failed to analyze update: {str(ex)}")

        # Step 3: Review Proposed Changes (AI Proposal Review Card)
        if proposal_state_key in st.session_state:
            prop_data = st.session_state[proposal_state_key]
            analysis = prop_data.get("analysis", {})
            status_changes = analysis.get("status_changes", [])
            source_update_text = prop_data.get("raw_text", raw_text.strip() if 'raw_text' in locals() else "")

            if prop_data.get("is_duplicate"):
                st.warning("⚠️ Duplicate update hash detected. Displaying cached proposal.")

            if not status_changes:
                # No state-changing proposal detected
                st.info("✓ AI analysis completed — no project-state changes detected.")
                if analysis.get("summary"):
                    st.caption(f"Summary: {analysis.get('summary')}")
                if st.button("Dismiss", key=f"btn_dismiss_no_change_{project.id}", type="secondary"):
                    del st.session_state[proposal_state_key]
                    st.rerun()
            else:
                # State-changing proposal detected — Prominent AI PROPOSAL REVIEW card
                overall_conf = analysis.get("overall_confidence", 0.90) * 100
                prop_header_html = (
                    f'<div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border: 2px solid #6366F1; border-radius: 12px; padding: 18px 20px; margin-top: 12px; margin-bottom: 16px; color: white;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;">'
                    f'<span style="font-size: 14px; font-weight: 800; letter-spacing: 0.04em; color: #EEF2FF;">🤖 AI PROPOSAL REVIEW</span>'
                    f'<span style="background: #4F46E5; color: white; padding: 3px 12px; border-radius: 999px; font-size: 11px; font-weight: 700;">'
                    f'Model Confidence Signal: {overall_conf:.0f}%'
                    f'</span>'
                    f'</div>'
                    f'<div style="font-size: 13px; color: #C7D2FE; margin-bottom: 6px;">'
                    f'<strong>Source Update:</strong> "{source_update_text}"'
                    f'</div>'
                    f'<div style="font-size: 13px; color: #E0E7FF; margin-bottom: 4px;">'
                    f'<strong>AI Reason:</strong> {analysis.get("summary", "")}'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(prop_header_html, unsafe_allow_html=True)

                st.markdown("<div style='font-size:13px; font-weight:700; color:#0F172A; margin-bottom:8px;'>Proposed Milestone Transitions:</div>", unsafe_allow_html=True)

                for idx, change in enumerate(status_changes):
                    conf_pct = change.get("confidence", 0.85) * 100
                    conf_lvl = change.get("confidence_level", "HIGH")
                    conf_bg = "#F0FDF4" if conf_lvl == "HIGH" else ("#FFFBEB" if conf_lvl == "MEDIUM" else "#FEF2F2")
                    conf_fg = "#15803D" if conf_lvl == "HIGH" else ("#B45309" if conf_lvl == "MEDIUM" else "#B91C1C")

                    change_card_html = (
                        f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:14px 16px; margin-bottom:8px; box-shadow:0 1px 2px rgba(0,0,0,0.02);">'
                        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">'
                        f'<span style="font-weight:700; font-size:14px; color:#0F172A;">{change.get("entity_name")}</span>'
                        f'<span style="background:{conf_bg}; color:{conf_fg}; padding:2px 8px; border-radius:6px; font-size:11px; font-weight:700;">'
                        f'{conf_lvl} ({conf_pct:.0f}%)'
                        f'</span>'
                        f'</div>'
                        f'<div style="display:flex; align-items:center; gap:8px; font-size:13px; margin-bottom:6px;">'
                        f'<span style="background:#F1F5F9; color:#475569; padding:2px 8px; border-radius:4px; font-weight:600;">Current: {change.get("previous_status", "Open")}</span>'
                        f'<span style="font-weight:800; color:#6366F1;">➔</span>'
                        f'<span style="background:#F0FDF4; color:#15803D; padding:2px 8px; border-radius:4px; font-weight:700;">Proposed: {change.get("proposed_status")}</span>'
                        f'</div>'
                        f'<div style="font-size:12px; color:#64748B;">'
                        f'<strong>Reason:</strong> {change.get("reason", "")}'
                        f'</div>'
                        f'</div>'
                    )
                    st.markdown(change_card_html, unsafe_allow_html=True)

                btn_col1, btn_col2, _ = st.columns([2, 2, 4])
                with btn_col1:
                    if st.button("✅ Approve", type="primary", key=f"btn_approve_prop_{project.id}", use_container_width=True):
                        all_indices = list(range(len(status_changes)))
                        res = services.apply_proposal_decision_service(
                            prop_data["proposal_id"], all_indices, []
                        )
                        st.session_state[applied_summary_key] = res
                        del st.session_state[proposal_state_key]
                        st.rerun()

                with btn_col2:
                    if st.button("❌ Reject", type="secondary", key=f"btn_reject_prop_{project.id}", use_container_width=True):
                        all_indices = list(range(len(status_changes)))
                        res = services.apply_proposal_decision_service(
                            prop_data["proposal_id"], [], all_indices
                        )
                        st.session_state[applied_summary_key] = res
                        del st.session_state[proposal_state_key]
                        st.rerun()

    visible_updates = updates if show_internal else customer_safe_updates(updates, visible_milestone_titles)
    if not visible_updates:
        st.info("No activity updates logged yet.")
    else:
        for update in visible_updates:
            render_update_entry(update, show_internal)

    # 10. Structured Activity Audit Log ("What Changed?")
    if show_internal and activities:
        st.markdown("<hr style='border-color:#E2E8F0; margin: 24px 0;'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:15px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px;'>📜 Activity Audit Log (\"What Changed?\")</div>", unsafe_allow_html=True)
        st.caption("Immutable audit record of state transitions, AI extractions, and human approvals.")

        for act in activities[:10]:
            ts_display = act.timestamp[:16].replace("T", " ") if getattr(act, "timestamp", "") else "N/A"
            source_badge = f'<span style="background:#EEF2FF; color:#3730A3; padding:2px 8px; border-radius:6px; font-size:11px; font-weight:700;">{act.source}</span>'
            actor_name = "User (Human Approval)" if "Human" in act.source else "Cadence System"
            before_txt = act.before_state
            after_txt = act.after_state
            has_state_transition = bool(before_txt and before_txt != "None") or bool(after_txt and after_txt != "None")

            if has_state_transition:
                type_badge = '<span style="background:#F0FDF4; color:#15803D; padding:2px 8px; border-radius:6px; font-size:11px; font-weight:700;">⚡ STATE TRANSITION</span>'
                details_grid = (
                    f'<div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:8px; font-size:12px; background:#F8FAFC; padding:6px 10px; border-radius:6px; margin-bottom:6px;">'
                    f'<div><strong>BEFORE:</strong> <span style="color:#B91C1C; font-weight:600;">{before_txt or "N/A"}</span></div>'
                    f'<div><strong>AFTER:</strong> <span style="color:#15803D; font-weight:700;">{after_txt or "N/A"}</span></div>'
                    f'<div><strong>ACTOR:</strong> <span style="color:#334155;">{actor_name}</span></div>'
                    f'</div>'
                )
            else:
                type_badge = '<span style="background:#F1F5F9; color:#475569; padding:2px 8px; border-radius:6px; font-size:11px; font-weight:700;">ℹ️ LOG ENTRY</span>'
                details_grid = (
                    f'<div style="font-size:12px; background:#F8FAFC; padding:6px 10px; border-radius:6px; margin-bottom:6px; color:#475569;">'
                    f'<strong>ACTOR:</strong> {actor_name} &nbsp;•&nbsp; <strong>EVENT TYPE:</strong> {act.event_type}'
                    f'</div>'
                )

            act_card_html = (
                f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:12px 16px; margin-bottom:8px; box-shadow:0 1px 2px rgba(0,0,0,0.02);">'
                f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">'
                f'<div style="font-weight:700; font-size:13px; color:#0F172A;">'
                f'⏱️ <span style="font-family:monospace; color:#475569;">{ts_display}</span> • <span style="color:#4F46E5;">{act.event_type}</span>'
                f'</div>'
                f'<div style="display:flex; gap:6px; align-items:center;">'
                f'{type_badge}'
                f'{source_badge}'
                f'</div>'
                f'</div>'
                f'{details_grid}'
                f'<div style="font-size:12px; color:#475569;"><strong>Reason:</strong> {act.description}</div>'
                f'</div>'
            )
            st.markdown(act_card_html, unsafe_allow_html=True)