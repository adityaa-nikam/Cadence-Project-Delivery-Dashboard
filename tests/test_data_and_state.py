from datetime import datetime
import unittest

import streamlit as st

from mock_data import ISSUES, MILESTONES, PROJECTS, UPDATES
from utils.state import (
    get_issues,
    get_milestones,
    get_project,
    get_updates,
    init_state,
    prepend_update,
    update_milestone_status,
)


class MockDataAndStateTests(unittest.TestCase):
    def test_mock_data_has_complete_realistic_distribution(self):
        self.assertEqual(len(PROJECTS), 6)
        self.assertEqual(
            {project.name for project in PROJECTS},
            {
                "Orion Logistics",
                "NovaBridge Systems",
                "Celera Health",
                "Driftwood Retail",
                "Quantum Perch",
                "Stellar Dynamics",
            },
        )

        for project in PROJECTS:
            milestones = [m for m in MILESTONES if m.project_id == project.id]
            issues = [issue for issue in ISSUES if issue.project_id == project.id]
            updates = [update for update in UPDATES if update.project_id == project.id]
            self.assertTrue(4 <= len(milestones) <= 5)
            self.assertTrue(2 <= len(issues) <= 3)
            self.assertEqual(len(updates), 3)
            self.assertTrue(all(update.affected_milestone in {m.title for m in milestones} for update in updates))
            self.assertTrue(all(update.structured_summary == "" and not update.is_ai_processed for update in updates))
            self.assertTrue(any(m.internal_only for m in milestones))
            self.assertTrue(any(issue.internal_only for issue in issues))

    def test_state_helpers_use_mutable_copies_and_sort_updates_newest_first(self):
        st.session_state.clear()
        init_state(PROJECTS, MILESTONES, UPDATES)
        project = PROJECTS[0]
        original_milestone = next(m for m in MILESTONES if m.project_id == project.id)

        fetched_proj = get_project(project.id)
        self.assertEqual(fetched_proj.id, project.id)
        self.assertEqual(
            [i.id for i in get_issues(project.id)],
            [i.id for i in ISSUES if i.project_id == project.id]
        )

        new_status = "Open" if original_milestone.status != "Open" else "Done"
        update_milestone_status(original_milestone.id, new_status)
        self.assertEqual(
            next(m for m in get_milestones(project.id) if m.id == original_milestone.id).status,
            new_status,
        )

        import uuid
        test_upd_id = f"test-update-{uuid.uuid4().hex[:8]}"
        from utils.database import get_db
        from utils.db_models import ProjectUpdateDB
        with get_db() as session:
            session.add(
                ProjectUpdateDB(
                    id=test_upd_id,
                    project_id=project.id,
                    timestamp="2099-01-01T00:00:00",
                    raw_text="newest update",
                    structured_summary="newest update summary",
                    affected_milestone=original_milestone.title,
                    status_change="",
                    is_ai_processed=False,
                )
            )

        project_updates = get_updates(project.id)
        self.assertEqual(project_updates[0].id, test_upd_id)
        self.assertEqual(
            [datetime.fromisoformat(update.timestamp) for update in project_updates],
            sorted((datetime.fromisoformat(update.timestamp) for update in project_updates), reverse=True),
        )


if __name__ == "__main__":
    unittest.main()
