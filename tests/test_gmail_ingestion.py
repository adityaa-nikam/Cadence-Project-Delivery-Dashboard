"""
Automated unit test suite for Gmail Ingestion Connector & AI Proposal Workflow integration.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
from integrations.gmail import GmailConnector
from utils import services
from utils.database import get_db, init_db
from utils.seed import seed_database


class TestGmailIngestionPipeline(unittest.TestCase):
    """Test suite verifying Gmail Connector, OAuth status checking, project matching, and proposal staging."""

    @classmethod
    def setUpClass(cls):
        cls.db_url = "sqlite:///:memory:"
        init_db(cls.db_url)
        seed_database(cls.db_url, force_reseed=True)
        cls.connector = GmailConnector()

    def test_01_oauth_connection_status_demo_mode(self):
        """Verify GmailConnector identifies unconfigured OAuth and displays Demo Mode label."""
        status = self.connector.get_connection_status()
        self.assertFalse(status["configured"], "OAuth should be unconfigured in test environment")
        self.assertFalse(status["authenticated"], "OAuth should be unauthenticated")
        self.assertEqual(status["scope"], "https://www.googleapis.com/auth/gmail.readonly")
        self.assertEqual(status["mode_label"], "Demo Mode — Gmail OAuth not configured")

    def test_02_fetch_and_normalize_messages(self):
        """Verify fetching and normalizing emails into standard dictionary structures."""
        raw_msgs = self.connector.fetch_messages(limit=3)
        self.assertEqual(len(raw_msgs), 3)

        norm = self.connector.normalize_message(raw_msgs[0])
        self.assertIn("message_id", norm)
        self.assertIn("sender", norm)
        self.assertIn("domain", norm)
        self.assertIn("subject", norm)
        self.assertIn("body", norm)
        self.assertEqual(norm["domain"], "orionlogistics.com")

    def test_03_deterministic_project_matching_domain(self):
        """Verify deterministic project matching via email domain."""
        projects = services.get_projects(db_url=self.db_url)
        
        # Test Orion Logistics domain match
        msg_orion = {"sender": "jake.network@orionlogistics.com", "subject": "Update", "body": "Firewall rules done"}
        norm_orion = self.connector.normalize_message(msg_orion)
        match_orion = self.connector.identify_project(norm_orion, projects)
        
        self.assertEqual(match_orion["project_id"], "orion")
        self.assertFalse(match_orion["match_uncertain"])
        self.assertGreaterEqual(match_orion["confidence"], 0.95)

        # Test NovaBridge domain match
        msg_nova = {"sender": "sarah.ops@novabridge.io", "subject": "Database update", "body": "Migration blocked"}
        norm_nova = self.connector.normalize_message(msg_nova)
        match_nova = self.connector.identify_project(norm_nova, projects)
        
        self.assertEqual(match_nova["project_id"], "novabridge")
        self.assertFalse(match_nova["match_uncertain"])

    def test_04_ambiguous_project_matching(self):
        """Verify generic external email sender is flagged as ambiguous match."""
        projects = services.get_projects(db_url=self.db_url)
        msg_generic = {"sender": "consultant@generic.com", "subject": "Weekly status", "body": "Progress report"}
        norm_generic = self.connector.normalize_message(msg_generic)
        match_generic = self.connector.identify_project(norm_generic, projects)

        self.assertIsNone(match_generic["project_id"])
        self.assertTrue(match_generic["match_uncertain"])

    def test_05_ingested_email_stages_proposal_without_auto_mutation(self):
        """Verify email ingestion passes through create_ai_proposal_service staging for human review."""
        msg = {"sender": "jake.network@orionlogistics.com", "subject": "Pilot complete", "body": "Dispatcher Pilot & Go-Live is 100% complete and approved."}
        norm = self.connector.normalize_message(msg)
        
        # Create staged AI proposal
        prop_res = services.create_ai_proposal_service("orion", norm["combined_text"], db_url=self.db_url)
        
        self.assertIn("proposal_id", prop_res)
        self.assertEqual(prop_res["status"], "Pending")

        # Verify database milestone status is NOT automatically modified before human approval
        ms_list = services.get_project_milestones("orion", db_url=self.db_url)
        pilot_ms = next(m for m in ms_list if m.id == "orion-m5")
        self.assertNotEqual(pilot_ms.status, "Done", "Milestone must NOT be automatically modified before human approval")

    def test_06_human_approval_executes_database_state_change(self):
        """Verify human approval executes state change and logs activity event."""
        msg = {"sender": "jake.network@orionlogistics.com", "subject": "Pilot complete", "body": "Dispatcher Pilot & Go-Live is 100% complete."}
        norm = self.connector.normalize_message(msg)
        prop_res = services.create_ai_proposal_service("orion", norm["combined_text"], db_url=self.db_url)

        # Execute Human Approval
        services.apply_proposal_decision_service(prop_res["proposal_id"], approved=True, db_url=self.db_url)

        # Verify Milestone Status in database is now updated
        ms_list = services.get_project_milestones("orion", db_url=self.db_url)
        pilot_ms = next(m for m in ms_list if m.id == "orion-m5")
        self.assertEqual(pilot_ms.status, "Done")

        # Verify Activity Log Audit Event recorded
        activities = services.get_activity_audit_trail(db_url=self.db_url)
        self.assertTrue(any("Human approved" in a.description for a in activities))

    @patch("urllib.request.urlopen")
    @patch("integrations.gmail.GmailConnector.is_authenticated", return_value=True)
    def test_07_live_gmail_api_fetch_authenticated(self, mock_auth, mock_urlopen):
        """Verify live Gmail API REST fetch when authenticated with OAuth token."""
        import json
        from io import BytesIO

        list_resp = json.dumps({"messages": [{"id": "msg_live_999"}]}).encode("utf-8")
        msg_resp = json.dumps({
            "id": "msg_live_999",
            "snippet": "Live production email status update snippet.",
            "payload": {
                "headers": [
                    {"name": "From", "value": "ops@orionlogistics.com"},
                    {"name": "Subject", "value": "Live API Status Update"},
                ]
            }
        }).encode("utf-8")

        mock_conn1 = MagicMock()
        mock_conn1.read.return_value = list_resp
        mock_conn1.__enter__.return_value = mock_conn1

        mock_conn2 = MagicMock()
        mock_conn2.read.return_value = msg_resp
        mock_conn2.__enter__.return_value = mock_conn2

        mock_urlopen.side_effect = [mock_conn1, mock_conn2]

        with patch("builtins.open", mock_open(read_data='{"access_token": "test_token_xyz"}')):
            fetched = self.connector.fetch_messages(limit=1)

        self.assertEqual(len(fetched), 1)
        self.assertEqual(fetched[0]["id"], "msg_live_999")
        self.assertEqual(fetched[0]["sender"], "ops@orionlogistics.com")
        self.assertEqual(fetched[0]["subject"], "Live API Status Update")
        self.assertEqual(fetched[0]["body"], "Live production email status update snippet.")

    @patch("urllib.request.urlopen")
    @patch.dict("os.environ", {"GMAIL_CLIENT_ID": "test_cid", "GMAIL_CLIENT_SECRET": "test_sec"})
    def test_08_oauth_token_exchange(self, mock_urlopen):
        """Verify OAuth 2.0 authorization code token exchange."""
        import json
        token_payload = json.dumps({"access_token": "ya29.test_token", "expires_in": 3600}).encode("utf-8")

        mock_conn = MagicMock()
        mock_conn.read.return_value = token_payload
        mock_conn.__enter__.return_value = mock_conn
        mock_urlopen.return_value = mock_conn

        with patch("builtins.open", mock_open()) as mock_file:
            res = self.connector.exchange_code_for_token("test_auth_code_123")

        self.assertTrue(res["success"])
        self.assertEqual(res["token"]["access_token"], "ya29.test_token")


if __name__ == "__main__":
    unittest.main()

