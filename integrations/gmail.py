"""Gmail integration connector demonstrating email ingestion and deterministic project matching."""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional

from integrations.base import BaseIntegrationConnector


class GmailConnector(BaseIntegrationConnector):
    """
    Gmail ingestion connector (Demo Mode / Sample Stream).
    Supports deterministic project matching by domain, project name, or customer alias,
    with fallback flagging when project matching is ambiguous.
    NOTE: Live OAuth integration architecture present, but live runtime OAuth token is not configured in local environment.
    """

    DOMAIN_PROJECT_MAP = {
        "orionlogistics.com": "orion",
        "novabridge.io": "novabridge",
        "celerahealth.org": "celera",
        "driftwoodretail.com": "driftwood",
        "quantumperch.ai": "quantum",
        "stellardynamics.space": "stellar",
    }

    ALIAS_MAP = {
        "orion": "orion",
        "novabridge": "novabridge",
        "celera": "celera",
        "driftwood": "driftwood",
        "quantum": "quantum",
        "stellar": "stellar",
    }

    def fetch_messages(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Mock/API fetcher simulating incoming email status updates from clients.
        """
        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        return [
            {
                "id": "msg_gmail_101",
                "sender": "jake.network@orionlogistics.com",
                "subject": "Firewall Approval Confirmation & Prod Access",
                "body": "Hi team, firewall rules for Orion were approved by CIO. Prod access is live.",
                "timestamp": now_iso,
            },
            {
                "id": "msg_gmail_102",
                "sender": "sarah.ops@novabridge.io",
                "subject": "Database migration timeout issue escalation",
                "body": "Hi Priya, database migration timed out during second run. Please review.",
                "timestamp": now_iso,
            },
            {
                "id": "msg_gmail_103",
                "sender": "external.consultant@generic.com",
                "subject": "Weekly status update on project deliverables",
                "body": "Hi, integration testing is progressing well but we need secondary approval.",
                "timestamp": now_iso,
            },
        ][:limit]

    def normalize_message(self, raw_message: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw email payload into standard message dictionary."""
        sender = raw_message.get("sender", "")
        subject = raw_message.get("subject", "")
        body = raw_message.get("body", "")

        domain = sender.split("@")[-1].lower() if "@" in sender else ""
        combined_text = f"Subject: {subject}\n\n{body}"

        return {
            "message_id": raw_message.get("id", ""),
            "sender": sender,
            "domain": domain,
            "subject": subject,
            "body": body,
            "combined_text": combined_text,
            "timestamp": raw_message.get("timestamp", ""),
        }

    def identify_project(self, normalized_message: Dict[str, Any], projects: List[Any]) -> Dict[str, Any]:
        """
        Deterministic matching pipeline:
        1. Check email domain match
        2. Check project name / alias in subject or body
        3. Flag ambiguity if multiple or zero confident matches found.
        """
        domain = normalized_message.get("domain", "")
        combined = normalized_message.get("combined_text", "").lower()

        # 1. Deterministic Domain Match
        if domain in self.DOMAIN_PROJECT_MAP:
            matched_id = self.DOMAIN_PROJECT_MAP[domain]
            return {
                "project_id": matched_id,
                "confidence": 0.98,
                "match_uncertain": False,
                "reason": f"Matched sender email domain '@{domain}'",
                "candidates": [matched_id],
            }

        # 2. Text Search Match
        matches = []
        for proj in projects:
            p_id = getattr(proj, "id", "")
            p_name = getattr(proj, "name", "").lower()

            if p_name and p_name in combined:
                matches.append((p_id, 0.90, f"Found exact project name '{proj.name}' in email text"))
            elif p_id and p_id in combined:
                matches.append((p_id, 0.85, f"Found project identifier '{p_id}' in email text"))

        if len(matches) == 1:
            p_id, conf, reason = matches[0]
            return {
                "project_id": p_id,
                "confidence": conf,
                "match_uncertain": False,
                "reason": reason,
                "candidates": [p_id],
            }
        elif len(matches) > 1:
            candidate_ids = [m[0] for m in matches]
            return {
                "project_id": None,
                "confidence": 0.40,
                "match_uncertain": True,
                "reason": f"Multiple potential project matches found: {', '.join(candidate_ids)}",
                "candidates": candidate_ids,
            }

        # 3. Uncertain Match
        return {
            "project_id": None,
            "confidence": 0.20,
            "match_uncertain": True,
            "reason": "Project match uncertain. Sender domain and text did not match any active client.",
            "candidates": [getattr(p, "id", "") for p in projects],
        }

    def create_update(self, project_id: str, normalized_message: Dict[str, Any]) -> Dict[str, Any]:
        """Create structured update payload for human approval."""
        return {
            "project_id": project_id,
            "raw_text": normalized_message.get("combined_text", ""),
            "author": normalized_message.get("sender", "Email Integration"),
            "source": "Gmail Connector",
            "timestamp": normalized_message.get("timestamp", ""),
        }
