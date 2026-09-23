"""State management helpers delegating to persistent database services."""

import streamlit as st

from utils.seed import seed_database
from utils import services


def init_state(projects=None, milestones=None, updates=None) -> None:
    """Initialize database and set up transient Streamlit UI state defaults."""
    # Ensure DB is created and seeded with demo data if empty
    seed_database()

    # UI state defaults ONLY (transient, non-source-of-truth)
    if "selected_project_id" not in st.session_state:
        st.session_state["selected_project_id"] = None
    if "view_mode" not in st.session_state:
        st.session_state["view_mode"] = "internal"


def get_project(project_id: str):
    """Return a project from the persistent database service."""
    return services.get_project(project_id)


def get_milestones(project_id: str):
    """Return the selected project's milestones from the database."""
    return services.get_project_milestones(project_id)


def get_issues(project_id: str):
    """Return the selected project's issues from the database."""
    return services.get_project_issues(project_id)


def get_updates(project_id: str):
    """Return updates newest first for the selected project from the database."""
    return services.get_project_updates(project_id)


def update_milestone_status(milestone_id: str, new_status: str) -> None:
    """Mutate the status of one milestone in the database with audit tracking."""
    services.update_milestone_status_service(milestone_id, new_status)


def prepend_update(update_obj) -> None:
    """Legacy helper maintained for backwards compatibility."""
    pass


def get_or_compute_health(project_id, project, milestones, issues, updates):
    """
    Compute project health score with signature invalidation.
    Cache updates instantly whenever milestones or issues change.
    """
    cache_key = f"health_cache_{project_id}"
    ms_sig = tuple((m.id, m.status) for m in milestones)
    iss_sig = tuple((getattr(i, 'id', ''), getattr(i, 'status', '')) for i in issues)
    sig_key = (ms_sig, iss_sig)

    if cache_key not in st.session_state or st.session_state.get(f"sig_{project_id}") != sig_key:
        from ai_helper import get_project_health
        health = get_project_health(project, milestones, issues, updates)
        st.session_state[cache_key] = health
        st.session_state[f"sig_{project_id}"] = sig_key

    return st.session_state[cache_key]