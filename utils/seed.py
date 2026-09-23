"""Database seeding logic to load initial hackathon mock data idempotently."""

from datetime import datetime
import uuid

from mock_data import ISSUES, MILESTONES, PROJECTS, UPDATES
from utils.database import get_db, init_db
from utils.db_models import ActivityEventDB, IssueDB, MilestoneDB, ProjectDB, ProjectUpdateDB


def seed_database(db_url: str | None = None, force_reseed: bool = False) -> bool:
    """
    Seed database with hackathon mock data if empty or force_reseed is True.
    Returns True if seeding occurred, False if skipped because data already existed.
    """
    init_db(db_url)

    with get_db(db_url) as session:
        existing_projects_count = session.query(ProjectDB).count()
        if existing_projects_count > 0 and not force_reseed:
            return False

        if force_reseed:
            session.query(ActivityEventDB).delete()
            session.query(ProjectUpdateDB).delete()
            session.query(IssueDB).delete()
            session.query(MilestoneDB).delete()
            session.query(ProjectDB).delete()

        # 1. Insert Projects
        for p in PROJECTS:
            proj_db = ProjectDB(
                id=p.id,
                name=p.name,
                overall_status=p.overall_status,
                owners=p.owners,
                health_score=100 if p.overall_status == "On Track" else (60 if p.overall_status == "At Risk" else 35),
                health_status=p.overall_status,
                internal_notes=p.internal_notes,
                last_update="",
            )
            session.add(proj_db)

        # 2. Insert Milestones
        for m in MILESTONES:
            ms_db = MilestoneDB(
                id=m.id,
                project_id=m.project_id,
                title=m.title,
                status=m.status,
                due_date=m.due_date,
                internal_only=m.internal_only,
                completed_at=datetime.now() if m.status == "Done" else None,
            )
            session.add(ms_db)

        # 3. Insert Issues
        for i in ISSUES:
            issue_db = IssueDB(
                id=i.id,
                project_id=i.project_id,
                title=i.title,
                category=i.category,
                severity="High" if i.category == "Bug" else "Medium",
                status="Open",
                internal_only=i.internal_only,
            )
            session.add(issue_db)

        # 4. Insert Updates & Initial Activity Audit Trail
        for u in UPDATES:
            upd_db = ProjectUpdateDB(
                id=u.id,
                project_id=u.project_id,
                raw_text=u.raw_text,
                structured_summary=u.structured_summary,
                affected_milestone=u.affected_milestone,
                status_change=u.status_change,
                is_ai_processed=u.is_ai_processed,
                source="Demo Data",
                author="System Seeder",
                timestamp=u.timestamp,
                processed_status="Completed",
            )
            session.add(upd_db)

            # Create corresponding activity event
            activity = ActivityEventDB(
                id=f"act_{uuid.uuid4().hex[:10]}",
                project_id=u.project_id,
                event_type="UPDATE_LOGGED",
                description=u.structured_summary or f"Activity recorded for {u.affected_milestone}",
                before_state="",
                after_state=u.status_change or "",
                source="AI" if u.is_ai_processed else "Human",
                timestamp=u.timestamp,
            )
            session.add(activity)

        # Update project last_update timestamps
        for p in PROJECTS:
            p_updates = [u for u in UPDATES if u.project_id == p.id]
            if p_updates:
                latest_ts = max(u.timestamp for u in p_updates)
                proj = session.query(ProjectDB).filter(ProjectDB.id == p.id).first()
                if proj:
                    proj.last_update = latest_ts

    return True
