"""SQLAlchemy ORM models for Cadence database persistence."""

from datetime import datetime, timezone
import json
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from utils.database import Base


def _utc_now():
    return datetime.now(timezone.utc)


class ProjectDB(Base):
    """Project ORM model."""

    __tablename__ = "projects"

    id = Column(String(50), primary_key=True)
    name = Column(String(150), nullable=False)
    overall_status = Column(String(50), nullable=False, default="On Track")
    _owners_json = Column("owners", Text, nullable=False, default="[]")
    health_score = Column(Integer, nullable=True, default=100)
    health_status = Column(String(50), nullable=True, default="Healthy")
    internal_notes = Column(Text, nullable=True, default="")
    last_update = Column(String(50), nullable=True, default="")
    created_at = Column(DateTime, default=_utc_now)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    milestones = relationship("MilestoneDB", back_populates="project", cascade="all, delete-orphan")
    issues = relationship("IssueDB", back_populates="project", cascade="all, delete-orphan")
    updates = relationship("ProjectUpdateDB", back_populates="project", cascade="all, delete-orphan")
    activities = relationship("ActivityEventDB", back_populates="project", cascade="all, delete-orphan")
    ai_events = relationship("AIEventDB", back_populates="project", cascade="all, delete-orphan")
    risks = relationship("RiskDB", back_populates="project", cascade="all, delete-orphan")
    proposals = relationship("ProposalDB", back_populates="project", cascade="all, delete-orphan")

    @property
    def owners(self) -> list[str]:
        """Return owners as a Python list."""
        if not self._owners_json:
            return []
        try:
            return json.loads(self._owners_json)
        except Exception:
            return [o.strip() for o in self._owners_json.split(",") if o.strip()]

    @owners.setter
    def owners(self, value: list[str] | str):
        """Set owners list as JSON string."""
        if isinstance(value, list):
            self._owners_json = json.dumps(value)
        elif isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    self._owners_json = json.dumps(parsed)
                else:
                    self._owners_json = json.dumps([value])
            except Exception:
                self._owners_json = json.dumps([o.strip() for o in value.split(",") if o.strip()])
        else:
            self._owners_json = "[]"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "owners": self.owners,
            "overall_status": self.overall_status,
            "health_score": self.health_score,
            "health_status": self.health_status,
            "internal_notes": self.internal_notes,
            "last_update": self.last_update,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MilestoneDB(Base):
    """Milestone ORM model."""

    __tablename__ = "milestones"

    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    status = Column(String(50), nullable=False, default="Open")
    due_date = Column(String(50), nullable=False, default="")
    internal_only = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utc_now)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    project = relationship("ProjectDB", back_populates="milestones")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "status": self.status,
            "due_date": self.due_date,
            "internal_only": self.internal_only,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class IssueDB(Base):
    """Issue ORM model."""

    __tablename__ = "issues"

    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False, default="Bug")
    severity = Column(String(50), nullable=False, default="Medium")
    status = Column(String(50), nullable=False, default="Open")
    internal_only = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=_utc_now)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    project = relationship("ProjectDB", back_populates="issues")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "category": self.category,
            "severity": self.severity,
            "status": self.status,
            "internal_only": self.internal_only,
        }


class ProjectUpdateDB(Base):
    """ProjectUpdate ORM model."""

    __tablename__ = "project_updates"

    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_text = Column(Text, nullable=False)
    structured_summary = Column(Text, nullable=True, default="")
    affected_milestone = Column(String(200), nullable=True, default="Unknown")
    status_change = Column(String(100), nullable=True, default="")
    is_ai_processed = Column(Boolean, nullable=False, default=False)
    source = Column(String(50), nullable=False, default="Streamlit UI")
    author = Column(String(100), nullable=False, default="User")
    timestamp = Column(String(50), nullable=False)
    processed_status = Column(String(50), nullable=False, default="Completed")

    project = relationship("ProjectDB", back_populates="updates")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "raw_text": self.raw_text,
            "structured_summary": self.structured_summary,
            "affected_milestone": self.affected_milestone,
            "status_change": self.status_change,
            "is_ai_processed": self.is_ai_processed,
            "source": self.source,
            "author": self.author,
            "timestamp": self.timestamp,
            "processed_status": self.processed_status,
        }


class AIEventDB(Base):
    """AIEvent ORM model for tracking LLM execution telemetry."""

    __tablename__ = "ai_events"

    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    update_id = Column(String(50), nullable=True)
    event_type = Column(String(50), nullable=False)  # parse_update, project_health, email_draft, nl_query
    model = Column(String(100), nullable=False)
    latency_ms = Column(Float, nullable=True, default=0.0)
    confidence = Column(Float, nullable=True, default=1.0)
    input_summary = Column(Text, nullable=True, default="")
    structured_output = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, default=_utc_now)

    project = relationship("ProjectDB", back_populates="ai_events")


class ActivityEventDB(Base):
    """ActivityEvent ORM model for audit trail logging."""

    __tablename__ = "activity_events"

    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)  # MILESTONE_STATUS_CHANGE, UPDATE_PROCESSED, HEALTH_RECALCULATED
    description = Column(Text, nullable=False)
    before_state = Column(Text, nullable=True, default="")
    after_state = Column(Text, nullable=True, default="")
    source = Column(String(50), nullable=False, default="System")  # Human / AI / System
    timestamp = Column(String(50), nullable=False)

    project = relationship("ProjectDB", back_populates="activities")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "event_type": self.event_type,
            "description": self.description,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "source": self.source,
            "timestamp": self.timestamp,
        }


class RiskDB(Base):
    """Structured Risk ORM model."""

    __tablename__ = "risks"

    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    severity = Column(String(50), nullable=False, default="MEDIUM")  # HIGH, MEDIUM, LOW
    impact = Column(Text, nullable=True, default="")
    recommended_action = Column(Text, nullable=True, default="")
    affected_milestone = Column(String(200), nullable=True, default="")
    source = Column(String(50), nullable=False, default="AI")  # AI or Human
    status = Column(String(50), nullable=False, default="Open")  # Open, Mitigated, Closed
    created_at = Column(DateTime, default=_utc_now)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    project = relationship("ProjectDB", back_populates="risks")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "severity": self.severity,
            "impact": self.impact,
            "recommended_action": self.recommended_action,
            "affected_milestone": self.affected_milestone,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ProposalDB(Base):
    """Staged AI Proposal ORM model prior to human approval."""

    __tablename__ = "proposals"

    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    update_hash = Column(String(64), nullable=True, index=True)
    raw_text = Column(Text, nullable=False)
    analysis_json = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="Pending")  # Pending, Approved, Rejected, Partially Approved
    created_at = Column(DateTime, default=_utc_now)

    project = relationship("ProjectDB", back_populates="proposals")

