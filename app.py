"""
Cadence Streamlit Application Entry Point.

DEVELOPER CONFIGURATION NOTE:
------------------------------
The file .streamlit/config.toml should contain:

[theme]
primaryColor = "#0F172A"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F8FAFC"
textColor = "#0F172A"
font = "sans serif"
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Load .env FIRST before any other imports that might read env vars
load_dotenv()

from mock_data import MILESTONES, PROJECTS, UPDATES
from pages.detail import render_detail
from pages.overview import render_overview
from pages.observability import render_observability_page
from utils.state import init_state
from utils.theme import load_custom_css

# Global Page Configuration
st.set_page_config(
    page_title="Cadence — Project Delivery Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_custom_css()


# API key check
def _get_api_key():
    key = os.environ.get("GROQ_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("GROQ_API_KEY", "") or st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            pass
    return key


st.session_state["has_gemini_api_key"] = bool(_get_api_key())
init_state(PROJECTS, MILESTONES, UPDATES)

if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "portfolio"

# Advanced Enterprise Sidebar Rail
with st.sidebar:
    # Cadence Brand Header Box
    brand_header_html = (
        f'<div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 14px 16px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); display: flex; align-items: center; gap: 12px;">'
        f'<div style="background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%); width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-size: 20px; box-shadow: 0 2px 8px rgba(79,70,229,0.4); flex-shrink: 0;">'
        f'📊'
        f'</div>'
        f'<div>'
        f'<div style="font-weight: 800; font-size: 17px; letter-spacing: -0.02em; color: #FFFFFF; line-height: 1.2;">CADENCE</div>'
        f'<div style="font-size: 11px; color: #94A3B8; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; margin-top: 2px;">AI Project Delivery Platform</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(brand_header_html, unsafe_allow_html=True)

    # Section: Main Navigation
    st.markdown("<div style='font-size: 10px; font-weight: 700; color: #64748B; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 8px;'>Main Navigation</div>", unsafe_allow_html=True)

    is_portfolio = st.session_state["active_tab"] == "portfolio" and st.session_state.get("selected_project_id") is None
    if st.button("🏠 Portfolio Overview", use_container_width=True, type="primary" if is_portfolio else "secondary"):
        st.session_state["selected_project_id"] = None
        st.session_state["active_tab"] = "portfolio"
        st.rerun()

    is_obs = st.session_state["active_tab"] == "observability"
    if st.button("📊 AI Observability Center", use_container_width=True, type="primary" if is_obs else "secondary"):
        st.session_state["selected_project_id"] = None
        st.session_state["active_tab"] = "observability"
        st.rerun()

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 20px 0;'>", unsafe_allow_html=True)

    # Section: Delivery Metrics
    st.markdown("<div style='font-size: 10px; font-weight: 700; color: #64748B; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 8px;'>Delivery Metrics</div>", unsafe_allow_html=True)

    from utils import services

    projects = services.get_projects()
    total_projects = len(projects)
    on_track = sum(1 for p in projects if p.overall_status == "On Track")
    at_risk = sum(1 for p in projects if p.overall_status == "At Risk")
    delayed = sum(1 for p in projects if p.overall_status == "Delayed")

    metrics_card_html = (
        f'<div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 14px; margin-bottom: 20px;">'
        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 8px;">'
        f'<span style="font-size:12px; font-weight:600; color:#94A3B8;">Active Programs</span>'
        f'<span style="font-size:16px; font-weight:800; color:#F8FAFC;">{total_projects} Projects</span>'
        f'</div>'
        f'<div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size:11px;">'
        f'<div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.2); padding:6px 10px; border-radius:6px; color:#34D399; font-weight:700;">'
        f'● {on_track} On Track'
        f'</div>'
        f'<div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.2); padding:6px 10px; border-radius:6px; color:#FBBF24; font-weight:700;">'
        f'● {at_risk} At Risk'
        f'</div>'
        f'<div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2); padding:6px 10px; border-radius:6px; color:#F87171; font-weight:700; grid-column: span 2;">'
        f'● {delayed} Schedule Delayed'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(metrics_card_html, unsafe_allow_html=True)

    # Section: AI System Engine
    st.markdown("<div style='font-size: 10px; font-weight: 700; color: #64748B; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 8px;'>AI System Engine</div>", unsafe_allow_html=True)

    if st.session_state["has_gemini_api_key"]:
        ai_status_html = (
            f'<div style="background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); padding: 10px 14px; border-radius: 10px; font-size: 12px; color: #34D399; font-weight: 700; display: flex; align-items: center; justify-content: space-between;">'
            f'<span style="display: flex; align-items: center; gap: 8px;">'
            f'<span style="width: 8px; height: 8px; border-radius: 50%; background: #34D399; box-shadow: 0 0 8px #34D399;"></span>'
            f'Groq LLM Engine'
            f'</span>'
            f'<span style="background: rgba(16,185,129,0.2); color: #34D399; font-size: 10px; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; font-weight: 800;">Online</span>'
            f'</div>'
        )
    else:
        ai_status_html = (
            f'<div style="background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); padding: 10px 14px; border-radius: 10px; font-size: 12px; color: #FBBF24; font-weight: 700; display: flex; align-items: center; justify-content: space-between;">'
            f'<span style="display: flex; align-items: center; gap: 8px;">'
            f'<span style="width: 8px; height: 8px; border-radius: 50%; background: #FBBF24;"></span>'
            f'AI Offline (Key Missing)'
            f'</span>'
            f'<span style="background: rgba(245,158,11,0.2); color: #FBBF24; font-size: 10px; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; font-weight: 800;">Standby</span>'
            f'</div>'
        )
    st.markdown(ai_status_html, unsafe_allow_html=True)

if st.session_state.get("active_tab") == "observability":
    render_observability_page()
elif st.session_state.get("selected_project_id") is None:
    render_overview()
else:
    render_detail()