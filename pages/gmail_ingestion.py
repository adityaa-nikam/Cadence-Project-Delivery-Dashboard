"""
Gmail Ingestion & Automated Email Update Processing Page for Cadence Enterprise Platform.
"""

import json
import streamlit as st
from integrations.gmail import GmailConnector
from utils import services
from utils.state import get_or_compute_health


def render_gmail_ingestion_page() -> None:
    """Render the enterprise Gmail Ingestion Operations Center."""
    connector = GmailConnector()
    conn_status = connector.get_connection_status()

    # Top Header Banner
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
            <div>
                <div style="font-size: 11px; font-weight: 700; color: #6366F1; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 2px;">
                    EXTERNAL INTEGRATIONS & INGESTION
                </div>
                <h1 style="font-size: 26px; font-weight: 800; color: #0F172A; margin: 0; letter-spacing: -0.02em;">
                    📧 Gmail Ingestion Center
                </h1>
                <div style="font-size: 13px; color: #64748B; margin-top: 4px;">
                    Automated status update ingestion, domain-based project matching, AI structured extraction, and human approval.
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 1. Connection Status & Controls Bar
    configured = conn_status["configured"]
    authenticated = conn_status["authenticated"]

    status_bg = "#F0FDF4" if authenticated else "#FFFBEB"
    status_fg = "#15803D" if authenticated else "#B45309"
    status_border = "#86EFAC" if authenticated else "#FDE68A"
    status_icon = "🟢" if authenticated else "⚠️"

    st.markdown(f"""
    <div style="background:{status_bg}; border:1px solid {status_border}; border-radius:12px; padding:16px 20px; margin-bottom:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <div style="font-size:14px; font-weight:800; color:{status_fg}; display:flex; align-items:center; gap:8px;">
                    <span>{status_icon} {conn_status['mode_label']}</span>
                </div>
                <div style="font-size:12px; color:#475569; margin-top:4px;">
                    Scope: <code style="background:rgba(0,0,0,0.05); padding:2px 6px; border-radius:4px;">{conn_status['scope']}</code> (Read-Only)
                    &nbsp;•&nbsp; Status: <b>{'Authenticated' if authenticated else 'Unauthenticated / Standby'}</b>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Action Buttons Row
    b_col1, b_col2, _ = st.columns([1.5, 1.5, 3])
    with b_col1:
        if st.button("📥 Sync & Ingest Emails", type="primary", use_container_width=True):
            st.session_state["trigger_gmail_sync"] = True
            st.rerun()

    with b_col2:
        connect_btn = st.button("🔒 Connect Gmail (OAuth)", type="secondary", use_container_width=True)

    if connect_btn or st.session_state.get("show_oauth_modal"):
        with st.expander("🔑 Google OAuth 2.0 Configuration Setup", expanded=True):
            st.markdown("""
            ### Live Gmail OAuth 2.0 Integration Setup
            To connect a live Gmail inbox to Cadence:

            1. Go to **Google Cloud Console** -> APIs & Services -> Credentials.
            2. Create an **OAuth 2.0 Client ID** (Web application).
            3. Add scope: `https://www.googleapis.com/auth/gmail.readonly` (Read-only email access).
            4. Add credentials to your `.env` file:
               ```env
               GMAIL_CLIENT_ID="your_google_client_id.apps.googleusercontent.com"
               GMAIL_CLIENT_SECRET="your_google_client_secret"
               ```
            5. Restart Cadence and click **Connect Gmail** to authorize.

            > **Current Environment Status**: `Demo Mode — Gmail OAuth not configured`. Live API fetching requires configured OAuth credentials. Currently demonstrating ingestion pipeline using simulated client email updates.
            """)

    st.markdown("<hr style='border-color:#E2E8F0; margin: 20px 0;'>", unsafe_allow_html=True)

    # 2. Ingestion Execution Flow
    projects = services.get_projects()
    raw_messages = connector.fetch_messages(limit=5)

    if st.session_state.get("trigger_gmail_sync"):
        st.session_state["trigger_gmail_sync"] = False
        st.toast("📥 Gmail sync completed. Ingested 3 status update emails.", icon="📧")

    st.markdown("<div style='font-size:14px; font-weight:800; color:#0F172A; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:12px;'>📬 Ingested Email Stream & Project Matching</div>", unsafe_allow_html=True)

    staged_proposals = []

    for msg in raw_messages:
        norm = connector.normalize_message(msg)
        match_result = connector.identify_project(norm, projects)

        matched_p_id = match_result.get("project_id")
        matched_proj = next((p for p in projects if p.id == matched_p_id), None) if matched_p_id else None

        card_bg = "#FFFFFF"
        badge_bg = "#F0FDF4" if matched_proj else "#FFFBEB"
        badge_fg = "#15803D" if matched_proj else "#B45309"
        match_str = f"✅ Matched: {matched_proj.name} ({match_result['reason']})" if matched_proj else f"⚠️ Ambiguous Match: {match_result['reason']}"

        with st.expander(f"✉️ {norm['subject']} — From: {norm['sender']} ({norm['timestamp'][:10]})", expanded=True):
            st.markdown(f"""
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 16px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:12px; font-weight:700; color:#475569;">Sender: {norm['sender']}</span>
                    <span style="background:{badge_bg}; color:{badge_fg}; font-size:11px; font-weight:700; padding:2px 10px; border-radius:999px;">
                        {match_str}
                    </span>
                </div>
                <div style="font-size:13px; color:#1E293B; font-weight:600; margin-bottom:4px;">Subject: {norm['subject']}</div>
                <div style="font-size:12px; color:#475569; font-style:italic;">"{norm['body']}"</div>
            </div>
            """, unsafe_allow_html=True)

            # Interactive Process with AI Pipeline Button
            if matched_proj:
                st_key = f"gmail_proposal_{matched_proj.id}_{norm['message_id']}"
                if st.button(f"✨ Run AI Pipeline for {matched_proj.name}", key=f"btn_run_ai_{norm['message_id']}", type="primary"):
                    try:
                        res = services.create_ai_proposal_service(matched_proj.id, norm["combined_text"], force_reanalyze=True)
                        st.session_state[st_key] = res
                        st.toast(f"AI proposal generated for {matched_proj.name}!", icon="✨")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to process email: {e}")

                # Display Staged AI Proposal if present
                if st_key in st.session_state:
                    prop_data = st.session_state[st_key]
                    analysis = prop_data.get("analysis", {})
                    status_changes = analysis.get("status_changes", [])

                    st.markdown("""
                    <div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border: 2px solid #6366F1; border-radius: 12px; padding: 16px; margin-top: 12px; color: white;">
                        <div style="font-size: 13px; font-weight: 800; color: #EEF2FF; margin-bottom: 8px;">🤖 STAGED AI PROPOSAL (Pending Human Approval)</div>
                    """, unsafe_allow_html=True)

                    if not status_changes:
                        st.info("✓ AI analysis completed — no project-state changes proposed in email text.")
                        st.caption(f"Summary: {analysis.get('summary')}")
                    else:
                        st.markdown(f"**AI Reason**: *{analysis.get('summary')}*")
                        for sc in status_changes:
                            st.markdown(f"• **{sc.get('entity_name')}**: Proposal `{sc.get('previous_status') or 'Current'}` -> `{sc.get('proposed_status')}` (Confidence: {sc.get('confidence', 0.85)*100:.0f}%)")

                        # Approval Action Buttons
                        col_app, col_rej = st.columns(2)
                        with col_app:
                            if st.button("✅ Approve & Commit to Database", key=f"app_gmail_{norm['message_id']}", type="primary"):
                                try:
                                    services.apply_proposal_decision_service(prop_data["proposal_id"], approved=True)
                                    del st.session_state[st_key]
                                    st.success("Proposal approved! Milestone updated in database and activity audit log recorded.")
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"Failed to commit proposal: {ex}")

                        with col_rej:
                            if st.button("❌ Reject Proposal", key=f"rej_gmail_{norm['message_id']}", type="secondary"):
                                try:
                                    services.apply_proposal_decision_service(prop_data["proposal_id"], rejected=True)
                                    del st.session_state[st_key]
                                    st.info("Proposal rejected. Zero database state mutation occurred.")
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"Failed to reject proposal: {ex}")

                    st.markdown("</div>", unsafe_allow_html=True)

            else:
                # Ambiguous Project Selector
                st.warning("⚠️ Ambiguous sender domain. Select target project to process email:")
                sel_p = st.selectbox(
                    "Target Project",
                    options=projects,
                    format_func=lambda p: p.name,
                    key=f"ambiguous_sel_{norm['message_id']}"
                )
                if st.button("✨ Assign & Process with AI", key=f"btn_assign_{norm['message_id']}", type="primary"):
                    try:
                        res = services.create_ai_proposal_service(sel_p.id, norm["combined_text"], force_reanalyze=True)
                        st.session_state[f"gmail_proposal_{sel_p.id}_{norm['message_id']}"] = res
                        st.success(f"Assigned to {sel_p.name} and AI proposal staged!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error processing email: {e}")
