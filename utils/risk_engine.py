"""Risk management engine for Cadence projects."""

import uuid
from datetime import datetime, timezone

from utils.database import get_db
from utils.db_models import RiskDB


def add_risk_service(
    project_id: str,
    title: str,
    severity: str = "MEDIUM",
    impact: str = "",
    recommended_action: str = "",
    affected_milestone: str = "",
    source: str = "Human",
    db_url: str | None = None,
) -> RiskDB:
    """Add a new risk entry to a project and return the persisted RiskDB object."""
    risk_id = f"risk_{uuid.uuid4().hex[:10]}"
    risk = RiskDB(
        id=risk_id,
        project_id=project_id,
        title=title,
        severity=severity.upper(),
        impact=impact,
        recommended_action=recommended_action,
        affected_milestone=affected_milestone,
        source=source,
        status="Open",
    )
    with get_db(db_url) as session:
        session.add(risk)
        session.flush()
        # Expunge to detach from session so caller can inspect freely
        session.expunge(risk)
    return risk


def get_project_risks(project_id: str, db_url: str | None = None) -> list[RiskDB]:
    """Retrieve all risks for a project, newest first."""
    with get_db(db_url) as session:
        risks = (
            session.query(RiskDB)
            .filter(RiskDB.project_id == project_id)
            .order_by(RiskDB.created_at.desc())
            .all()
        )
        # Expunge to prevent detached-instance errors after session closes
        for r in risks:
            session.expunge(r)
        return risks


def update_risk_status(
    risk_id: str, new_status: str, db_url: str | None = None
) -> RiskDB | None:
    """Update a risk's status (Open, Mitigated, Closed)."""
    valid = {"Open", "Mitigated", "Closed"}
    if new_status not in valid:
        raise ValueError(f"Invalid risk status '{new_status}'. Must be one of {valid}")
    with get_db(db_url) as session:
        risk = session.query(RiskDB).filter(RiskDB.id == risk_id).first()
        if risk:
            risk.status = new_status
            risk.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.expunge(risk)
        return risk
