"""Comprehensive test suite for database initialization, ORM entities, repository/service layer, and transactions."""

import unittest
from unittest.mock import patch
from sqlalchemy.orm import Session

from utils.database import get_db, init_db
from utils.db_models import ActivityEventDB, IssueDB, MilestoneDB, ProjectDB, ProjectUpdateDB
from utils.seed import seed_database
from utils import services


class DatabaseAndServicesTests(unittest.TestCase):
    """Unit tests covering all required persistent storage, service, and transaction requirements."""

    def setUp(self):
        """Use an isolated in-memory SQLite database for each test."""
        import os
        import utils.database as db
        db._engine = None
        db._session_factory = None
        db.DEFAULT_DB_URL = "sqlite:///:memory:"
        self.db_url = "sqlite:///:memory:"
        init_db(self.db_url)
        seed_database(self.db_url, force_reseed=True)

    # 1. Database Initialization
    def test_01_database_initialization(self):
        with get_db(self.db_url) as session:
            projects_count = session.query(ProjectDB).count()
            milestones_count = session.query(MilestoneDB).count()
            issues_count = session.query(IssueDB).count()
            self.assertGreater(projects_count, 0)
            self.assertGreater(milestones_count, 0)
            self.assertGreater(issues_count, 0)

    # 2. Project Creation & Retrieval
    def test_02_project_creation_and_retrieval(self):
        with get_db(self.db_url) as session:
            new_project = ProjectDB(
                id="test-proj-99",
                name="Acme Quantum Portal",
                overall_status="On Track",
                owners=["Alice Architect", "Bob Backend"],
                internal_notes="Test notes",
            )
            session.add(new_project)

        fetched = services.get_project("test-proj-99", db_url=self.db_url)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Acme Quantum Portal")
        self.assertEqual(fetched.owners, ["Alice Architect", "Bob Backend"])

    # 3. Milestone Retrieval
    def test_03_milestone_retrieval(self):
        milestones = services.get_project_milestones("orion", db_url=self.db_url)
        self.assertTrue(len(milestones) >= 4)
        self.assertTrue(all(m.project_id == "orion" for m in milestones))

    # 4. Milestone Update
    def test_04_milestone_update(self):
        milestones = services.get_project_milestones("orion", db_url=self.db_url)
        target = milestones[0]
        initial_status = target.status
        new_status = "Blocked" if initial_status != "Blocked" else "Done"

        updated = services.update_milestone_status_service(
            target.id, new_status, source="TestRunner", db_url=self.db_url
        )
        self.assertEqual(updated.status, new_status)

        # Verify persisted state
        refetched = services.get_project_milestones("orion", db_url=self.db_url)
        matched = next(m for m in refetched if m.id == target.id)
        self.assertEqual(matched.status, new_status)

    # 5. Issue Retrieval
    def test_05_issue_retrieval(self):
        issues = services.get_project_issues("novabridge", db_url=self.db_url)
        self.assertTrue(len(issues) > 0)
        self.assertTrue(all(i.project_id == "novabridge" for i in issues))

    # 6. Activity Creation
    def test_06_activity_creation(self):
        milestones = services.get_project_milestones("celera", db_url=self.db_url)
        target = next(m for m in milestones if m.status != "Done")

        services.update_milestone_status_service(target.id, "Done", source="AuditTest", db_url=self.db_url)

        activities = services.get_activity_history("celera", db_url=self.db_url)
        self.assertTrue(len(activities) > 0)
        latest_act = activities[0]
        self.assertIn(target.title, latest_act.description)
        self.assertEqual(latest_act.source, "AuditTest")

    # 7. Project-Scoped Data Retrieval
    def test_07_project_scoped_data_retrieval(self):
        orion_milestones = services.get_project_milestones("orion", db_url=self.db_url)
        nova_milestones = services.get_project_milestones("novabridge", db_url=self.db_url)

        orion_ids = {m.id for m in orion_milestones}
        nova_ids = {m.id for m in nova_milestones}

        self.assertTrue(orion_ids.isdisjoint(nova_ids))

    # 8. Duplicate Seed Prevention
    def test_08_duplicate_seed_prevention(self):
        initial_proj_count = len(services.get_projects(db_url=self.db_url))

        # Re-run seed_database without force_reseed
        seeded_again = seed_database(self.db_url, force_reseed=False)
        self.assertFalse(seeded_again)

        after_proj_count = len(services.get_projects(db_url=self.db_url))
        self.assertEqual(initial_proj_count, after_proj_count)

    # 9. Transaction Rollback
    def test_09_transaction_rollback(self):
        # Attempt to insert invalid record causing DB constraint error inside get_db
        try:
            with get_db(self.db_url) as session:
                # Primary key collision or invalid object
                dup = ProjectDB(id="orion", name="Duplicate Orion")
                session.add(dup)
        except Exception:
            pass  # Expected rollback

        # Verify existing record was untouched
        orion = services.get_project("orion", db_url=self.db_url)
        self.assertNotEqual(orion.name, "Duplicate Orion")

    # 10. Invalid Project ID Handling
    def test_10_invalid_project_id(self):
        invalid_proj = services.get_project("non-existent-id-12345", db_url=self.db_url)
        self.assertIsNone(invalid_proj)

        milestones = services.get_project_milestones("non-existent-id-12345", db_url=self.db_url)
        self.assertEqual(milestones, [])

        with self.assertRaises(ValueError):
            services.create_ai_proposal_service("non-existent-id-12345", "test update text", db_url=self.db_url)

    # 11. Invalid Milestone ID Handling
    def test_11_invalid_milestone_id(self):
        with self.assertRaises(ValueError):
            services.update_milestone_status_service("invalid-ms-9999", "Done", db_url=self.db_url)


if __name__ == "__main__":
    unittest.main()
