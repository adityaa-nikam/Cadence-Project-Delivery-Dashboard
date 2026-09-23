"""Custom design system & CSS injection for Cadence Project Delivery Dashboard."""

import streamlit as st


def load_custom_css() -> None:
    """Inject modern B2B SaaS design system CSS into Streamlit page."""
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --cadence-primary: #0F172A;
        --cadence-bg: #FFFFFF;
        --cadence-surface: #F8FAFC;
        --cadence-surface-hover: #F1F5F9;
        --cadence-border: #E2E8F0;
        --cadence-text: #0F172A;
        --cadence-text-muted: #64748B;
        --cadence-text-subtle: #94A3B8;
        --cadence-accent: #6366F1;
        --cadence-accent-dark: #4F46E5;
        --cadence-success: #15803D;
        --cadence-success-bg: #F0FDF4;
        --cadence-success-border: #BBF7D0;
        --cadence-warning: #B45309;
        --cadence-warning-bg: #FFFBEB;
        --cadence-warning-border: #FDE68A;
        --cadence-danger: #B91C1C;
        --cadence-danger-bg: #FEF2F2;
        --cadence-danger-border: #FECACA;
        --cadence-radius: 12px;
    }

    /* Global Typography & Font Family */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        color: var(--cadence-text) !important;
    }

    /* Clean Streamlit Header & Hide Unnecessary Visual Remnants */
    header[data-testid="stHeader"] {
        background: rgba(255, 255, 255, 0.85) !important;
        backdrop-filter: blur(12px) !important;
        border-bottom: 1px solid var(--cadence-border) !important;
    }

    #MainMenu, footer {
        visibility: hidden !important;
    }

    /* Hide Default Streamlit Navigation Links */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    /* Page Background */
    .stApp {
        background: var(--cadence-surface) !important;
    }

    /* Container Constraints & Spacing */
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1440px !important;
    }

    /* Advanced Enterprise Sidebar Navigation Rail Styling */
    section[data-testid="stSidebar"] {
        background: #0B1120 !important;
        border-right: 1px solid #1E293B !important;
    }

    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] label {
        color: #F8FAFC !important;
    }

    section[data-testid="stSidebar"] .stButton > button {
        background: rgba(255, 255, 255, 0.03) !important;
        color: #94A3B8 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        padding: 0.6rem 1rem !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(99, 102, 241, 0.15) !important;
        border-color: rgba(99, 102, 241, 0.4) !important;
        color: #FFFFFF !important;
        transform: translateX(2px) !important;
    }

    /* Primary Action Buttons */
    .stButton > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        padding: 0.55rem 1.25rem !important;
        box-shadow: 0 2px 4px rgba(79, 70, 229, 0.25) !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button[kind="primary"]:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        background: linear-gradient(135deg, #4338CA 0%, #4F46E5 100%) !important;
        box-shadow: 0 4px 8px rgba(79, 70, 229, 0.35) !important;
        transform: translateY(-1px) !important;
    }

    /* Secondary Buttons */
    .stButton > button[kind="secondary"] {
        background: #FFFFFF !important;
        color: #334155 !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.04) !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button[kind="secondary"]:hover {
        background: #F8FAFC !important;
        border-color: #94A3B8 !important;
        color: #0F172A !important;
        transform: translateY(-1px) !important;
    }

    /* Form Fields (Inputs, Textarea, Selectbox) */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        border-radius: 8px !important;
        border: 1px solid #CBD5E1 !important;
        padding: 0.55rem 0.875rem !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.875rem !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {
        border-color: var(--cadence-accent) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
        outline: none !important;
    }

    /* Custom Scrollbars */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #F1F5F9;
    }
    ::-webkit-scrollbar-thumb {
        background: #CBD5E1;
        border-radius: 999px;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background-color: transparent !important;
        border-bottom: 1px solid #E2E8F0 !important;
        padding-bottom: 4px !important;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        padding: 8px 16px !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        color: #64748B !important;
        border: 1px solid transparent !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #4F46E5 !important;
        border-color: #E2E8F0 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    }

    /* Targeted Cadence Utility Classes */
    .cadence-card {
        background: #FFFFFF;
        border: 1px solid var(--cadence-border);
        border-radius: var(--cadence-radius);
        padding: 20px 24px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    }

    .cadence-section-header {
        font-size: 14px;
        font-weight: 800;
        color: var(--cadence-text);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 12px;
    }

    .cadence-empty-state {
        background: #FFFFFF;
        border: 1px dashed var(--cadence-border);
        border-radius: var(--cadence-radius);
        padding: 24px;
        text-align: center;
        color: var(--cadence-text-muted);
        font-size: 13px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
