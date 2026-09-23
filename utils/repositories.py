"""Repository pattern classes for Cadence ORM data access."""

from sqlalchemy.orm import Session

from utils.db_models import (
    ActivityEventDB,
    AIEventDB,
    IssueDB,
    MilestoneDB,
    ProjectDB,
    ProjectUpdateDB,
)


class ProjectRepository:
    """Data-access layer for ProjectDB entities."""

    def __init__(self, session: Session):
        self._session = session

    def get_all(self, status_filter: str | None = None) -> list[ProjectDB]:
        """Return all projects, optionally filtered by overall_status."""
        q = self._session.query(ProjectDB)
        if status_filter:
            q = q.filter(ProjectDB.overall_status == status_filter)
        return q.all()

    def get_by_id(self, project_id: str) -> ProjectDB | None:
        return self._session.query(ProjectDB).filter(ProjectDB.id == project_id).first()


class MilestoneRepository:
    """Data-access layer for MilestoneDB entities."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_project(self, project_id: str, customer_only: bool = False) -> list[MilestoneDB]:
        q = self._session.query(MilestoneDB).filter(MilestoneDB.project_id == project_id)
        if customer_only:
            q = q.filter(MilestoneDB.internal_only == False)  # noqa: E712
        return q.all()

    def get_by_id(self, milestone_id: str) -> MilestoneDB | None:
        return self._session.query(MilestoneDB).filter(MilestoneDB.id == milestone_id).first()


class IssueRepository:
    """Data-access layer for IssueDB entities."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_project(self, project_id: str, customer_only: bool = False) -> list[IssueDB]:
        q = self._session.query(IssueDB).filter(IssueDB.project_id == project_id)
        if customer_only:
            q = q.filter(IssueDB.internal_only == False)  # noqa: E712
        return q.all()


class UpdateRepository:
    """Data-access layer for ProjectUpdateDB entities."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_project(self, project_id: str) -> list[ProjectUpdateDB]:
        return (
            self._session.query(ProjectUpdateDB)
            .filter(ProjectUpdateDB.project_id == project_id)
            .order_by(ProjectUpdateDB.timestamp.desc())
            .all()
        )

    def add(self, update: ProjectUpdateDB):
        self._session.add(update)


class ActivityRepository:
    """Data-access layer for ActivityEventDB entities."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_project(self, project_id: str) -> list[ActivityEventDB]:
        return (
            self._session.query(ActivityEventDB)
            .filter(ActivityEventDB.project_id == project_id)
            .order_by(ActivityEventDB.timestamp.desc())
            .all()
        )

    def add(self, activity: ActivityEventDB):
        self._session.add(activity)


class AIEventRepository:
    """Data-access layer for AIEventDB entities."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_project(self, project_id: str) -> list[AIEventDB]:
        return (
            self._session.query(AIEventDB)
            .filter(AIEventDB.project_id == project_id)
            .order_by(AIEventDB.created_at.desc())
            .all()
        )

    def add(self, event: AIEventDB):
        self._session.add(event)
