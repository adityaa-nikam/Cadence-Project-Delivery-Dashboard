"""Comprehensive test suite for AI reliability, Pydantic extraction, validation, human-in-the-loop, deterministic health scoring, and idempotency."""

import unittest
from unittest.mock import patch

from utils.database import get_db, init_db
from utils.db_models import ActivityEventDB, MilestoneDB, ProjectDB, RiskDB
from utils import health_engine, risk_engine, services, validation
from utils.schemas import ProjectUpdateAnalysis, StatusChangeProposal, RiskProposal
from utils.seed import seed_database


class AIReliabilityTests(unittest.TestCase):
    """Test suite for AI trustworthiness, validation layer, and human-in-the-loop approval."""

    def setUp(self):
        """Use isolated in-memory SQLite database for test execution."""
        import utils.database as db
        db._engine = None
        db._session_factory = None
        db.DEFAULT_DB_URL = "sqlite:///:memory:"
        self.db_url = "sqlite:///:memory:"
        init_db(self.db_url)
        seed_database(self.db_url, force_reseed=True)

    # 1. Pydantic Schema Validation
    def test_01_pydantic_schema_validation(self):
        data = {
            "summary": "SSO milestone completed ahead of schedule.",
            "affected_milestones": ["Discovery & Requirements"],
            "affected_issues": [],
            "risks": [
                {
                    "title": "API rate limits",
                    "severity": "HIGH",
                    "impact": "Slow sync",
                    "recommended_action": "Add caching",
                    "confidence": 0.88,
                }
            ],
            "status_changes": [
                {
                    "entity_type": "Milestone",
                    "entity_name": "Discovery & Requirements",
                    "previous_status": "Open",
                    "proposed_status": "Done",
                    "reason": "Engineering confirmed completion",
                    "confidence": 0.95,
                }
            ],
            "overall_confidence": 0.92,
            "reasoning_summary": "High confidence extraction",
        }

        model = ProjectUpdateAnalysis.model_validate(data)
        self.assertEqual(model.summary, data["summary"])
        self.assertEqual(model.status_changes[0].proposed_status, "Done")
        self.assertEqual(model.risks[0].severity, "HIGH")

    # 2. Confidence Level Classification
    def test_02_confidence_level_thresholds(self):
        self.assertEqual(validation.get_confidence_level(0.95), "HIGH")
        self.assertEqual(validation.get_confidence_level(0.85), "HIGH")
        self.assertEqual(validation.get_confidence_level(0.75), "MEDIUM")
        self.assertEqual(validation.get_confidence_level(0.50), "LOW")

    # 3. Status Transition Matrix Rules
    def test_03_status_transition_rules(self):
        self.assertTrue(validation.is_transition_allowed("Blocked", "Done"))
        self.assertTrue(validation.is_transition_allowed("Open", "Blocked"))
        self.assertTrue(validation.is_transition_allowed("Done", "Open"))  # Reopening allowed
        self.assertFalse(validation.is_transition_allowed("Done", "InvalidStatus"))

    # 4. Cross-Project Entity Injection & Validation Layer
    def test_04_cross_project_entity_injection_validation(self):
        milestones = services.get_project_milestones("orion", db_url=self.db_url)
        issues = services.get_project_issues("orion", db_url=self.db_url)

        # Attempt proposal with a milestone title from Novabridge project
        fake_proposal = {
            "entity_type": "Milestone",
            "entity_name": "Database Migration",  # Belongs to novabridge, not orion
            "proposed_status": "Done",
            "confidence": 0.90,
        }

        is_valid, err, entity = validation.validate_status_change_proposal(
            fake_proposal, "orion", milestones, issues
        )

        self.assertFalse(is_valid)
        self.assertIn("does not belong to project 'orion'", err)
        self.assertIsNone(entity)

    # 5. Idempotency Hashing & Duplicate Proposal Detection
    def test_05_idempotency_duplicate_detection(self):
        h1 = validation.compute_update_hash("orion", "Firewall Access Approval is done.")
        h2 = validation.compute_update_hash("orion", "FIREWALL ACCESS APPROVAL IS DONE. ")
        self.assertEqual(h1, h2)

        # Generate proposal
        prop1 = services.create_ai_proposal_service(
            "orion", "Firewall Access Approval is done.", db_url=self.db_url
        )
        self.assertFalse(prop1["is_duplicate"])

        # Second call with identical normalized text should flag duplicate
        prop2 = services.create_ai_proposal_service(
            "orion", "Firewall Access Approval is done.", db_url=self.db_url
        )
        self.assertTrue(prop2["is_duplicate"])

    # 6. Human Approval Workflow
    def test_06_human_approval_workflow(self):
        prop = services.create_ai_proposal_service(
            "novabridge", "Database Migration is finished and now Done.", db_url=self.db_url
        )
        proposal_id = prop["proposal_id"]

        # Apply approval for index 0
        result = services.apply_proposal_decision_service(
            proposal_id, approved_change_indices=[0], rejected_change_indices=[], db_url=self.db_url
        )

        self.assertTrue(len(result["applied_changes"]) > 0)
        self.assertIn("Database Migration", result["applied_changes"][0])

        # Verify DB status updated
        nova_ms = services.get_project_milestones("novabridge", db_url=self.db_url)
        db_mig = next(m for m in nova_ms if m.title == "Database Migration")
        self.assertEqual(db_mig.status, "Done")

    # 7. Human Rejection Workflow
    def test_07_human_rejection_workflow(self):
        prop = services.create_ai_proposal_service(
            "novabridge", "Firewall Rules Configuration is unblocked.", db_url=self.db_url
        )
        proposal_id = prop["proposal_id"]

        # Apply rejection for index 0
        result = services.apply_proposal_decision_service(
            proposal_id, approved_change_indices=[], rejected_change_indices=[0], db_url=self.db_url
        )

        self.assertEqual(len(result["applied_changes"]), 0)
        self.assertTrue(len(result["rejected_changes"]) > 0)

        # Verify Activity event logged for rejection
        activities = services.get_activity_history("novabridge", db_url=self.db_url)
        rejected_act = next(a for a in activities if a.event_type == "AI_PROPOSAL_REJECTED")
        self.assertIn("rejected AI proposed status change", rejected_act.description)

    # 8. Deterministic Health Calculation Engine
    def test_08_deterministic_health_engine(self):
        project = services.get_project("orion", db_url=self.db_url)
        milestones = services.get_project_milestones("orion", db_url=self.db_url)
        issues = services.get_project_issues("orion", db_url=self.db_url)
        updates = services.get_project_updates("orion", db_url=self.db_url)

        res1 = health_engine.compute_project_health(project, milestones, issues, updates)
        res2 = health_engine.compute_project_health(project, milestones, issues, updates)

        # Scores must be 100% identical and deterministic
        self.assertEqual(res1["score"], res2["score"])
        self.assertEqual(res1["grade"], res2["grade"])

    # 9. Risk Engine Tracking
    def test_09_risk_engine_ai_vs_human(self):
        r_ai = risk_engine.add_risk_service(
            "celera",
            title="HIPAA Audit Delay",
            severity="HIGH",
            impact="Schedule slip",
            recommended_action="Escalate to legal",
            source="AI",
            db_url=self.db_url,
        )

        risks = risk_engine.get_project_risks("celera", db_url=self.db_url)
        self.assertTrue(any(r.id == r_ai.id and r.source == "AI" for r in risks))

    # 10. Graceful AI Failure Handling
    @patch("ai_helper._call_groq_api", side_effect=RuntimeError("Groq API Timeout"))
    def test_10_ai_failure_handling(self, mock_groq):
        milestones = services.get_project_milestones("orion", db_url=self.db_url)
        from ai_helper import parse_update

        res = parse_update("Some status update text", milestones)
        self.assertIsNotNone(res.get("error"))
        self.assertEqual(res.get("overall_confidence"), 0.0)

    # 11. No Database Mutation Before Approval
    def test_11_no_database_mutation_before_approval(self):
        project = services.get_project("novabridge", db_url=self.db_url)
        milestones_before = services.get_project_milestones("novabridge", db_url=self.db_url)
        issues = services.get_project_issues("novabridge", db_url=self.db_url)
        updates = services.get_project_updates("novabridge", db_url=self.db_url)

        target_m = milestones_before[1]
        original_status = target_m.status
        health_before = health_engine.compute_project_health(project, milestones_before, issues, updates)

        # Create proposal
        prop = services.create_ai_proposal_service(
            "novabridge", f"{target_m.title} is completed and verified by security team.", db_url=self.db_url
        )
        self.assertIsNotNone(prop["proposal_id"])

        # BEFORE approval: DB, milestone status, and health must remain 100% UNCHANGED
        milestones_after = services.get_project_milestones("novabridge", db_url=self.db_url)
        target_after = next(m for m in milestones_after if m.id == target_m.id)
        self.assertEqual(target_after.status, original_status)

        health_after = health_engine.compute_project_health(project, milestones_after, issues, updates)
        self.assertEqual(health_after["score"], health_before["score"])

    # 12. Prerequisite Completion vs Milestone Completion Rule
    def test_12_prerequisite_vs_milestone_completion(self):
        milestones = services.get_project_milestones("novabridge", db_url=self.db_url)
        from ai_helper import parse_update

        # Ambiguous prerequisite update
        prereq_input = "Firewall approval has been completed, clearing a prerequisite for firewall rules configuration."
        analysis_prereq = parse_update(prereq_input, milestones)
        
        # Must NOT propose setting Firewall Rules to Done
        status_changes_prereq = analysis_prereq.get("status_changes", [])
        fw_done_proposals = [
            c for c in status_changes_prereq 
            if c.get("proposed_status") == "Done" and "Firewall" in c.get("entity_name", "")
        ]
        self.assertEqual(len(fw_done_proposals), 0)

        # Explicit completion update
        explicit_input = "Firewall Rules Configuration is now complete and has been verified by the security team."
        analysis_explicit = parse_update(explicit_input, milestones)
        status_changes_explicit = analysis_explicit.get("status_changes", [])
        self.assertGreaterEqual(len(status_changes_explicit), 1)

    # 13. No-Change Update Handling
    def test_13_no_change_update_detection(self):
        milestones = services.get_project_milestones("novabridge", db_url=self.db_url)
        from ai_helper import parse_update

        no_change_input = "Team had a routine sync meeting today to review open action items."
        analysis = parse_update(no_change_input, milestones)
        self.assertEqual(len(analysis.get("status_changes", [])), 0)


if __name__ == "__main__":
    unittest.main()
