"""Demo mode scenario utilities for Cadence Project Delivery Intelligence Platform."""

from typing import Any, Dict, List


def get_demo_scenarios_for_project(project_id: str) -> List[Dict[str, Any]]:
    """Return pre-built demo scenarios for interactive simulation targeting active open/blocked milestones."""
    scenarios = {
        "novabridge": [
            {
                "title": "Firewall Rules Approved & Completed",
                "raw_text": "Firewall Rules Configuration is now complete and has been verified by the security team.",
                "text": "Firewall Rules Configuration is now complete and has been verified by the security team.",
                "category": "explicit_completion"
            },
            {
                "title": "Database Migration Unblocked",
                "raw_text": "Database Migration is unblocked and ready for testing following the devops patch.",
                "text": "Database Migration is unblocked and ready for testing following the devops patch.",
                "category": "unblock"
            }
        ],
        "orion": [
            {
                "title": "Dispatcher Pilot Complete",
                "raw_text": "Dispatcher Pilot & Go-Live is 100% complete and verified by Orion Ops team.",
                "text": "Dispatcher Pilot & Go-Live is 100% complete and verified by Orion Ops team.",
                "category": "explicit_completion"
            }
        ],
        "celera": [
            {
                "title": "HIPAA Review Unblocked",
                "raw_text": "Legal team signed off on DPA. HIPAA Compliance Review is no longer blocked and resumed review.",
                "text": "Legal team signed off on DPA. HIPAA Compliance Review is no longer blocked and resumed review.",
                "category": "unblock"
            },
            {
                "title": "Audit Export Feature Completed",
                "raw_text": "Audit Export Feature is finished and verified by clinical team.",
                "text": "Audit Export Feature is finished and verified by clinical team.",
                "category": "explicit_completion"
            }
        ],
        "driftwood": [
            {
                "title": "Holiday Launch Prep Done",
                "raw_text": "Holiday Launch Prep completed with zero open issues.",
                "text": "Holiday Launch Prep completed with zero open issues.",
                "category": "explicit_completion"
            }
        ],
        "quantum": [
            {
                "title": "Telemetry Pipeline Completed",
                "raw_text": "Telemetry Pipeline Design milestone has been completed and signed off.",
                "text": "Telemetry Pipeline Design milestone has been completed and signed off.",
                "category": "explicit_completion"
            }
        ],
        "stellar": [
            {
                "title": "Simulation Data Import Blocked",
                "raw_text": "Simulation Data Import is currently blocked because customer data export contains corrupted checksums.",
                "text": "Simulation Data Import is currently blocked because customer data export contains corrupted checksums.",
                "category": "blocker"
            }
        ]
    }

    default_scenarios = [
        {
            "title": "Milestone Completion Update",
            "raw_text": "Project milestones completed successfully and verified by QA.",
            "text": "Project milestones completed successfully and verified by QA.",
            "category": "explicit_completion"
        }
    ]

    return scenarios.get(project_id.lower(), default_scenarios)
