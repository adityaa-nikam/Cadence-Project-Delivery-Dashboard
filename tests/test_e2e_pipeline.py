"""End-to-end integration and workflow test suite for Cadence AI application pipeline."""

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from utils import database, health_engine, services
from utils.database import get_db, init_db
from utils.db_models import MilestoneDB, ProjectDB
from utils.query_engine import query_project_intelligence
from integrations.gmail import GmailConnector


class TestE2EPipeline(unittest.TestCase):
    """Full end-to-end test cases covering ingestion to database persistence."""

    def setUp(self):
        """Use isolated in-memory SQLite database for each test run."""
        self.db_url = "sqlite:///:memory:"
        database.DEFAULT_DB_URL = self.db_url
        init_db(self.db_url)

        self.project_id = f"test_e2e_{uuid.uuid4().hex[:8]}"

        # Seed minimal test project environment with unique project_id
        with get_db(self.db_url) as session:
            proj = ProjectDB(
                id=self.project_id,
                name="E2E Delivery Project",
                overall_status="On Track",
                owners=["Alice Lead"],
                health_score=95,
                health_status="Healthy",
                internal_notes="Internal engineering test notes.",
                last_update=datetime.now(timezone.utc).isoformat(),
            )
            session.add(proj)

            ms1 = MilestoneDB(
                id=f"ms_e2e_1_{uuid.uuid4().hex[:6]}",
                project_id=self.project_id,
                title="API Access",
                status="Open",
                due_date="2026-10-01",
                internal_only=False,
            )
            ms2 = MilestoneDB(
                id=f"ms_e2e_2_{uuid.uuid4().hex[:6]}",
                project_id=self.project_id,
                title="Internal Security Audit",
                status="Open",
                due_date="2026-10-15",
                internal_only=True,
            )
            session.add_all([ms1, ms2])

    def test_e2e_update_to_health_recalculation(self):
        """
        Test the complete pipeline:
        Raw update -> AI proposal -> Human approval -> DB update -> Activity Event -> Health recalculation.
        """
        raw_text = "API Access is completed successfully today."

        mock_ai_output = {
            "summary": "API Access completed.",
            "affected_milestones": ["API Access"],
            "status_changes": [
                {
                    "entity_type": "Milestone",
                    "entity_name": "API Access",
                    "previous_status": "Open",
                    "proposed_status": "Done",
                    "reason": "Completed today",
                    "confidence": 0.95,
                }
            ],
            "risks": [],
            "overall_confidence": 0.95,
            "reasoning_summary": "High confidence milestone completion.",
        }

        with patch("utils.services.parse_update", return_value=mock_ai_output):
            # 1. Create Proposal
            prop_res = services.create_ai_proposal_service(self.project_id, raw_text, db_url=self.db_url)
            self.assertIn("proposal_id", prop_res)
            self.assertFalse(prop_res["is_duplicate"])

            # Verify AI Telemetry event recorded
            ai_events = services.get_ai_events(self.project_id, db_url=self.db_url)
            self.assertTrue(len(ai_events) >= 1)

            # 2. Human Approves Proposal (index 0)
            proposal_id = prop_res["proposal_id"]
            decision_res = services.apply_proposal_decision_service(
                proposal_id, approved_change_indices=[0], rejected_change_indices=[], db_url=self.db_url
            )

            self.assertTrue(len(decision_res["applied_changes"]) > 0)

            # 3. Verify Database State Updated
            milestones = services.get_project_milestones(self.project_id, db_url=self.db_url)
            api_ms = next(m for m in milestones if m.title == "API Access")
            self.assertEqual(api_ms.status, "Done")

            # 4. Verify Activity History Logged
            activities = services.get_activity_history(self.project_id, db_url=self.db_url)
            self.assertTrue(len(activities) >= 1)
            self.assertEqual(activities[0].event_type, "MILESTONE_STATUS_CHANGE")
            self.assertEqual(activities[0].after_state, "Done")

            # 5. Verify Health Score Recalculated
            proj = services.get_project(self.project_id, db_url=self.db_url)
            issues = services.get_project_issues(self.project_id, db_url=self.db_url)
            updates = services.get_project_updates(self.project_id, db_url=self.db_url)
            health = health_engine.compute_project_health(proj, milestones, issues, updates)
            self.assertGreaterEqual(health["score"], 80)

    def test_rejected_ai_proposal(self):
        """Test that rejecting an AI proposal does NOT mutate project state but logs an audit event."""
        raw_text = "API Access is completed."
        mock_ai_output = {
            "summary": "API Access completed.",
            "affected_milestones": ["API Access"],
            "status_changes": [
                {
                    "entity_type": "Milestone",
                    "entity_name": "API Access",
                    "previous_status": "Open",
                    "proposed_status": "Done",
                    "reason": "Proposed completion",
                    "confidence": 0.90,
                }
            ],
            "risks": [],
            "overall_confidence": 0.90,
        }

        with patch("utils.services.parse_update", return_value=mock_ai_output):
            prop_res = services.create_ai_proposal_service(self.project_id, raw_text, db_url=self.db_url)
            proposal_id = prop_res["proposal_id"]

            # Reject change index 0
            decision_res = services.apply_proposal_decision_service(
                proposal_id, approved_change_indices=[], rejected_change_indices=[0], db_url=self.db_url
            )

            self.assertEqual(len(decision_res["applied_changes"]), 0)
            self.assertEqual(len(decision_res["rejected_changes"]), 1)

            # Ensure milestone remains Open
            milestones = services.get_project_milestones(self.project_id, db_url=self.db_url)
            api_ms = next(m for m in milestones if m.title == "API Access")
            self.assertEqual(api_ms.status, "Open")

            # Ensure rejection activity logged
            activities = services.get_activity_history(self.project_id, db_url=self.db_url)
            rejection_acts = [a for a in activities if a.event_type == "AI_PROPOSAL_REJECTED"]
            self.assertEqual(len(rejection_acts), 1)

    def test_duplicate_update_idempotency(self):
        """Test duplicate raw updates yield duplicate flag and existing proposal without duplicate AI calls."""
        raw_text = "Duplicate raw text testing."
        mock_ai_output = {
            "summary": "Duplicate summary",
            "affected_milestones": [],
            "status_changes": [],
            "risks": [],
            "overall_confidence": 0.8,
        }

        with patch("utils.services.parse_update", return_value=mock_ai_output) as mock_ai:
            res1 = services.create_ai_proposal_service(self.project_id, raw_text, db_url=self.db_url)
            self.assertFalse(res1["is_duplicate"])
            self.assertEqual(mock_ai.call_count, 1)

            res2 = services.create_ai_proposal_service(self.project_id, raw_text, db_url=self.db_url)
            self.assertTrue(res2["is_duplicate"])
            self.assertEqual(mock_ai.call_count, 1)

    def test_customer_vs_internal_visibility(self):
        """Test internal-only milestones and updates are excluded in customer-only service calls."""
        customer_milestones = services.get_project_milestones(self.project_id, customer_only=True, db_url=self.db_url)
        ms_titles = [m.title for m in customer_milestones]
        self.assertIn("API Access", ms_titles)
        self.assertNotIn("Internal Security Audit", ms_titles)

    def test_project_matching_gmail_connector(self):
        """Test Gmail connector project matching logic."""
        projects = services.get_projects(db_url=self.db_url)
        connector = GmailConnector()

        raw_msg_high = {
            "id": "g_1",
            "sender": "contact@acme.com",
            "subject": f"Update on {self.project_id}",
            "body": "API testing is progressing well.",
        }
        norm_high = connector.normalize_message(raw_msg_high)
        res_high = connector.identify_project(norm_high, projects)
        self.assertEqual(res_high["project_id"], self.project_id)
        self.assertFalse(res_high["match_uncertain"])

        raw_msg_amb = {
            "id": "g_2",
            "sender": "unknown@thirdparty.com",
            "subject": "General status inquiry",
            "body": "Hey there, checking in on delivery progress.",
        }
        norm_amb = connector.normalize_message(raw_msg_amb)
        res_amb = connector.identify_project(norm_amb, projects)
        self.assertTrue(res_amb["match_uncertain"])

    def test_natural_language_intent_query(self):
        """Test structured NL query intent extraction and execution."""
        res = query_project_intelligence("Which milestones are blocked?", db_url=self.db_url)
        self.assertEqual(res["intent"], "BLOCKED_MILESTONES")
        self.assertIn("answer", res)
        self.assertFalse(res["executed_raw_sql"])

    def test_ai_assistant_chip_callback(self):
        """Test suggested query chip click callbacks update session state and pending query queue."""
        import streamlit as st
        from components.ai_assistant import _on_chip_click, _on_ask_click

        _on_chip_click("What's at risk?")
        self.assertEqual(st.session_state.get("nl_query_field"), "What's at risk?")
        self.assertEqual(st.session_state.get("pending_query_run"), "What's at risk?")

        _on_ask_click()
        self.assertEqual(st.session_state.get("pending_query_run"), "What's at risk?")


if __name__ == "__main__":
    unittest.main()

