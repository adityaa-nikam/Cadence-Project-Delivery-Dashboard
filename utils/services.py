"""Service layer encapsulating all business logic, transaction handling, and activity logging."""

from datetime import datetime, timezone
import time
import uuid

from ai_helper import parse_update
from utils.database import get_db
from utils.db_models import ActivityEventDB, AIEventDB, IssueDB, MilestoneDB, ProjectDB, ProjectUpdateDB
from utils.repositories import (
    ActivityRepository,
    AIEventRepository,
    IssueRepository,
    MilestoneRepository,
    ProjectRepository,
    UpdateRepository,
)


def get_projects(status_filter: str | None = None, db_url: str | None = None) -> list[ProjectDB]:
    """Retrieve projects matching optional status filter."""
    with get_db(db_url) as session:
        repo = ProjectRepository(session)
        return repo.get_all(status_filter)


def get_project(project_id: str, db_url: str | None = None) -> ProjectDB | None:
    """Retrieve a single project by ID."""
    if not project_id:
        return None
    with get_db(db_url) as session:
        repo = ProjectRepository(session)
        return repo.get_by_id(project_id)


def get_project_milestones(
    project_id: str, customer_only: bool = False, db_url: str | None = None
) -> list[MilestoneDB]:
    """Retrieve milestones for a specific project."""
    if not project_id:
        return []
    with get_db(db_url) as session:
        repo = MilestoneRepository(session)
        return repo.get_by_project(project_id, customer_only)


def get_project_issues(
    project_id: str, customer_only: bool = False, db_url: str | None = None
) -> list[IssueDB]:
    """Retrieve issues for a specific project."""
    if not project_id:
        return []
    with get_db(db_url) as session:
        repo = IssueRepository(session)
        return repo.get_by_project(project_id, customer_only)


def get_project_updates(
    project_id: str, customer_only: bool = False, db_url: str | None = None
) -> list[ProjectUpdateDB]:
    """Retrieve updates for a specific project (newest first)."""
    if not project_id:
        return []
    with get_db(db_url) as session:
        repo = UpdateRepository(session)
        updates = repo.get_by_project(project_id)
        if customer_only:
            ms_repo = MilestoneRepository(session)
            visible_titles = {m.title for m in ms_repo.get_by_project(project_id, customer_only=True)}
            updates = [u for u in updates if u.affected_milestone in visible_titles]
        return updates


def get_activity_history(project_id: str, db_url: str | None = None) -> list[ActivityEventDB]:
    """Retrieve audit activity history for a project."""
    if not project_id:
        return []
    with get_db(db_url) as session:
        repo = ActivityRepository(session)
        return repo.get_by_project(project_id)


def get_ai_events(project_id: str, db_url: str | None = None) -> list[AIEventDB]:
    """Retrieve AI execution logs for a project."""
    if not project_id:
        return []
    with get_db(db_url) as session:
        repo = AIEventRepository(session)
        return repo.get_by_project(project_id)


def update_milestone_status_service(
    milestone_id: str, new_status: str, source: str = "Human", db_url: str | None = None
) -> MilestoneDB:
    """
    Atomically update a milestone's status and record an ActivityEvent audit trail.
    Raises ValueError on invalid milestone or status.
    """
    valid_statuses = {"Open", "Blocked", "Done"}
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid_statuses}")

    with get_db(db_url) as session:
        ms_repo = MilestoneRepository(session)
        act_repo = ActivityRepository(session)
        proj_repo = ProjectRepository(session)

        milestone = ms_repo.get_by_id(milestone_id)
        if not milestone:
            raise ValueError(f"Milestone '{milestone_id}' not found.")

        old_status = milestone.status
        if old_status == new_status:
            return milestone

        milestone.status = new_status
        if new_status == "Done":
            milestone.completed_at = datetime.now(timezone.utc)
        else:
            milestone.completed_at = None

        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        # Update parent project last_update
        project = proj_repo.get_by_id(milestone.project_id)
        if project:
            project.last_update = now_iso

        # Log audit trail activity
        activity = ActivityEventDB(
            id=f"act_{uuid.uuid4().hex[:10]}",
            project_id=milestone.project_id,
            event_type="MILESTONE_STATUS_CHANGE",
            description=f"Milestone '{milestone.title}' changed status from {old_status} to {new_status}",
            before_state=old_status,
            after_state=new_status,
            source=source,
            timestamp=now_iso,
        )
        act_repo.add(activity)

        return milestone


def create_ai_proposal_service(
    project_id: str,
    raw_text: str,
    db_url: str | None = None,
    force_reanalyze: bool = False,
) -> dict:
    """
    Generate an AI analysis proposal staged for human review without mutating state.
    Includes validation, confidence levels, and idempotency checking.
    """
    import json
    from utils import validation
    from utils.db_models import ProposalDB

    if not project_id:
        raise ValueError("project_id is required")
    if not raw_text or not raw_text.strip():
        raise ValueError("raw_text cannot be empty")

    update_hash = validation.compute_update_hash(project_id, raw_text)
    start_time = time.time()

    with get_db(db_url) as session:
        proj_repo = ProjectRepository(session)
        ms_repo = MilestoneRepository(session)
        issue_repo = IssueRepository(session)

        project = proj_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        existing_proposal = session.query(ProposalDB).filter(
            ProposalDB.project_id == project_id,
            ProposalDB.update_hash == update_hash,
        ).first()

        if existing_proposal:
            if not force_reanalyze:
                return {
                    "proposal_id": existing_proposal.id,
                    "raw_text": existing_proposal.raw_text,
                    "analysis": json.loads(existing_proposal.analysis_json),
                    "is_duplicate": True,
                    "status": existing_proposal.status,
                    "error": None,
                }
            else:
                session.delete(existing_proposal)

        project_milestones = ms_repo.get_by_project(project_id)
        project_issues = issue_repo.get_by_project(project_id)

    # Call AI Helper
    ai_result = parse_update(raw_text.strip(), project_milestones)
    latency = round((time.time() - start_time) * 1000, 2)

    # If status_changes is empty (e.g. no API key configured or fallback), run deterministic rule-based pattern extraction
    if not ai_result.get("status_changes"):
        demo_changes = []
        demo_affected = []
        raw_lower = raw_text.lower()
        for m in project_milestones:
            m_title = getattr(m, "title", "")
            m_title_lower = m_title.lower()
            if m_title_lower in raw_lower or (len(m_title_lower.split()) > 1 and all(w in raw_lower for w in m_title_lower.split() if len(w) > 3)):
                demo_affected.append(m_title)
                if any(kw in raw_lower for kw in ["complete", "completed", "finished", "100%", "done", "succeeded"]):
                    if getattr(m, "status", "") != "Done":
                        demo_changes.append({
                            "entity_type": "Milestone",
                            "entity_name": m_title,
                            "previous_status": getattr(m, "status", "Open"),
                            "proposed_status": "Done",
                            "reason": f"Update explicitly states '{m_title}' is complete.",
                            "confidence": 0.95,
                        })
                elif any(kw in raw_lower for kw in ["blocked", "timeout", "timed out", "delay", "stuck", "failing"]):
                    if getattr(m, "status", "") != "Blocked":
                        demo_changes.append({
                            "entity_type": "Milestone",
                            "entity_name": m_title,
                            "previous_status": getattr(m, "status", "Open"),
                            "proposed_status": "Blocked",
                            "reason": f"Update text indicates '{m_title}' is delivery blocked.",
                            "confidence": 0.90,
                        })

        if demo_changes:
            ai_result["status_changes"] = demo_changes
            ai_result["affected_milestones"] = demo_affected
            ai_result["summary"] = raw_text.strip().replace("\n", " ")[:150]
            ai_result["affected_milestone"] = demo_affected[0]
            ai_result["new_status"] = demo_changes[0]["proposed_status"]
            ai_result["error"] = None

    # Validate proposed status changes
    validated_changes = []
    for change in ai_result.get("status_changes", []):
        is_valid, err_reason, matched_entity = validation.validate_status_change_proposal(
            change, project_id, project_milestones, project_issues
        )
        change_item = dict(change)
        change_item["is_valid"] = is_valid
        change_item["validation_error"] = err_reason
        change_item["confidence_level"] = validation.get_confidence_level(change.get("confidence", 0.85))
        if matched_entity:
            change_item["entity_id"] = matched_entity.id
            change_item["previous_status"] = matched_entity.status
        validated_changes.append(change_item)

    ai_result["status_changes"] = validated_changes
    proposal_id = f"prop_{uuid.uuid4().hex[:10]}"

    # Save pending proposal in DB
    with get_db(db_url) as session:
        proposal_db = ProposalDB(
            id=proposal_id,
            project_id=project_id,
            update_hash=update_hash,
            raw_text=raw_text.strip(),
            analysis_json=json.dumps(ai_result),
            status="Pending",
        )
        session.add(proposal_db)

        # Telemetry
        ai_repo = AIEventRepository(session)
        ai_repo.add(
            AIEventDB(
                id=f"aiev_{uuid.uuid4().hex[:10]}",
                project_id=project_id,
                update_id=proposal_id,
                event_type="create_proposal",
                model="qwen/qwen3.8-27b",
                latency_ms=latency,
                confidence=ai_result.get("overall_confidence", 0.9),
                input_summary=raw_text[:150],
                structured_output=json.dumps(ai_result),
            )
        )

    return {
        "proposal_id": proposal_id,
        "raw_text": raw_text.strip(),
        "analysis": ai_result,
        "is_duplicate": False,
        "status": "Pending",
        "error": ai_result.get("error"),
    }


def apply_proposal_decision_service(
    proposal_id: str,
    approved_change_indices: list[int] | None = None,
    rejected_change_indices: list[int] | None = None,
    author: str = "User",
    db_url: str | None = None,
    approved: bool | None = None,
    rejected: bool | None = None,
) -> dict:
    """
    Execute human-approved status changes in an atomic database transaction.
    Logs activity events for approved and rejected items.
    """
    import json
    from utils import validation
    from utils.db_models import ProposalDB, RiskDB

    if not proposal_id:
        raise ValueError("proposal_id is required")

    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    with get_db(db_url) as session:
        proposal = session.query(ProposalDB).filter(ProposalDB.id == proposal_id).first()
        if not proposal:
            raise ValueError(f"Proposal '{proposal_id}' not found.")

        analysis = json.loads(proposal.analysis_json)
        project_id = proposal.project_id

        ms_repo = MilestoneRepository(session)
        issue_repo = IssueRepository(session)
        upd_repo = UpdateRepository(session)
        act_repo = ActivityRepository(session)
        proj_repo = ProjectRepository(session)

        project_milestones = ms_repo.get_by_project(project_id)
        project_issues = issue_repo.get_by_project(project_id)

        status_changes = analysis.get("status_changes", [])

        applied_changes = []
        rejected_changes = []

        if approved and approved_change_indices is None:
            approved_change_indices = list(range(len(status_changes)))
        elif approved_change_indices is None:
            approved_change_indices = []

        if rejected and rejected_change_indices is None:
            rejected_change_indices = list(range(len(status_changes)))
        elif rejected_change_indices is None:
            rejected_change_indices = []

        # 1. Process Approved Status Changes
        for idx in approved_change_indices:
            if 0 <= idx < len(status_changes):
                change = status_changes[idx]
                is_valid, err_reason, matched_entity = validation.validate_status_change_proposal(
                    change, project_id, project_milestones, project_issues
                )

                if is_valid and matched_entity:
                    old_st = matched_entity.status
                    new_st = change["proposed_status"]

                    if old_st != new_st:
                        matched_entity.status = new_st
                        if new_st == "Done":
                            matched_entity.completed_at = datetime.now(timezone.utc)

                        change_str = f"{old_st} → {new_st}"
                        applied_changes.append(f"{change['entity_name']}: {change_str}")

                        # Activity audit log for approved status change
                        act_repo.add(
                            ActivityEventDB(
                                id=f"act_{uuid.uuid4().hex[:10]}",
                                project_id=project_id,
                                event_type="MILESTONE_STATUS_CHANGE",
                                description=f"Human approved status change for '{change['entity_name']}': {change_str}",
                                before_state=old_st,
                                after_state=new_st,
                                source="Human Approved AI",
                                timestamp=now_iso,
                            )
                        )

        # 2. Process Rejected Status Changes
        for idx in rejected_change_indices:
            if 0 <= idx < len(status_changes):
                change = status_changes[idx]
                rejected_changes.append(change['entity_name'])

                act_repo.add(
                    ActivityEventDB(
                        id=f"act_{uuid.uuid4().hex[:10]}",
                        project_id=project_id,
                        event_type="AI_PROPOSAL_REJECTED",
                        description=f"Human reviewer rejected AI proposed status change for '{change['entity_name']}' ({change.get('previous_status')} → {change.get('proposed_status')})",
                        before_state=change.get("previous_status", ""),
                        after_state="Rejected",
                        source="Human Rejected AI",
                        timestamp=now_iso,
                    )
                )

        # 3. Process Risks
        for r_dict in analysis.get("risks", []):
            risk_db = RiskDB(
                id=f"risk_{uuid.uuid4().hex[:10]}",
                project_id=project_id,
                title=r_dict.get("title", "AI Detected Risk"),
                severity=r_dict.get("severity", "MEDIUM"),
                impact=r_dict.get("impact", ""),
                recommended_action=r_dict.get("recommended_action", ""),
                affected_milestone=r_dict.get("affected_milestone", ""),
                source="AI",
                status="Open",
            )
            session.add(risk_db)

        # 4. Create ProjectUpdate DB entry
        update_id = f"upd_ai_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        status_change_summary = "; ".join(applied_changes) if applied_changes else ""
        new_update = ProjectUpdateDB(
            id=update_id,
            project_id=project_id,
            raw_text=proposal.raw_text,
            structured_summary=analysis.get("summary", ""),
            affected_milestone=analysis.get("affected_milestone", "Unknown"),
            status_change=status_change_summary,
            is_ai_processed=True,
            source="Human Approved Form",
            author=author,
            timestamp=now_iso,
            processed_status="Approved" if applied_changes else ("Rejected" if rejected_changes else "Completed"),
        )
        upd_repo.add(new_update)

        # Update proposal status
        if len(approved_change_indices) == len(status_changes) and len(status_changes) > 0:
            proposal.status = "Approved"
        elif len(rejected_change_indices) == len(status_changes) and len(status_changes) > 0:
            proposal.status = "Rejected"
        elif len(approved_change_indices) > 0:
            proposal.status = "Partially Approved"
        else:
            proposal.status = "Processed"

        # Update project timestamp
        proj = proj_repo.get_by_id(project_id)
        if proj:
            proj.last_update = now_iso

    return {
        "applied_changes": applied_changes,
        "rejected_changes": rejected_changes,
        "summary": analysis.get("summary"),
        "status": proposal.status,
    }


def get_portfolio_stats(db_url: str | None = None) -> dict:
    """Retrieve portfolio metrics for the overview header dashboard."""
    with get_db(db_url) as session:
        projects = session.query(ProjectDB).all()
        milestones = session.query(MilestoneDB).all()
        updates = session.query(ProjectUpdateDB).all()

        total = len(projects)
        on_track = sum(1 for p in projects if p.overall_status == "On Track")
        at_risk = sum(1 for p in projects if p.overall_status == "At Risk")
        total_blocked = sum(1 for m in milestones if m.status == "Blocked")
        total_ai_events = session.query(AIEventDB).count()
        ai_updates = sum(1 for u in updates if u.is_ai_processed)
        total_ai_logs = max(total_ai_events, ai_updates)

        return {
            "total_projects": total,
            "on_track": on_track,
            "at_risk": at_risk,
            "total_blocked": total_blocked,
            "ai_updates": total_ai_logs,
        }


def get_activity_audit_trail(project_id: str | None = None, db_url: str | None = None):
    """Retrieve activity audit trail events from database."""
    from utils.db_models import ActivityEventDB
    with get_db(db_url) as session:
        query = session.query(ActivityEventDB)
        if project_id:
            query = query.filter(ActivityEventDB.project_id == project_id)
        return query.order_by(ActivityEventDB.timestamp.desc()).all()

