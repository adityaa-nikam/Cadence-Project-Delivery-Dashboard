"""Validation utilities for AI-proposed state changes in Cadence."""

import hashlib


# Valid milestone and issue statuses
VALID_STATUSES = {"Open", "Blocked", "Done", "In Progress"}

# Allowed status transitions (from_status -> set of allowed to_statuses)
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "Open":        {"Blocked", "Done", "In Progress"},
    "In Progress": {"Blocked", "Done", "Open"},
    "Blocked":     {"Open", "Done", "In Progress"},
    "Done":        {"Open", "Blocked", "In Progress"},  # Reopening is allowed
}


def get_confidence_level(confidence: float) -> str:
    """Classify a confidence float into HIGH, MEDIUM, or LOW."""
    if confidence >= 0.85:
        return "HIGH"
    elif confidence >= 0.65:
        return "MEDIUM"
    return "LOW"


def is_transition_allowed(from_status: str, to_status: str) -> bool:
    """Return True if a status transition is permitted by the transition matrix."""
    if to_status not in VALID_STATUSES:
        return False
    allowed = ALLOWED_TRANSITIONS.get(from_status, set())
    return to_status in allowed


def compute_update_hash(project_id: str, raw_text: str) -> str:
    """Compute a stable SHA-256 hash for deduplication of raw updates.

    Normalises the text (lowercase, strip whitespace) before hashing so
    that minor formatting differences don't create duplicate proposals.
    """
    normalised = f"{project_id}::{raw_text.strip().lower()}"
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def validate_status_change_proposal(
    proposal: dict,
    project_id: str,
    milestones: list,
    issues: list,
) -> tuple[bool, str | None, object | None]:
    """Validate an AI-proposed status change against known project entities.

    Returns:
        (is_valid, error_reason, matched_entity)
        - is_valid: True if the proposal passes all checks
        - error_reason: Human-readable rejection reason, or None on success
        - matched_entity: The matched Milestone/Issue ORM object, or None
    """
    entity_name = proposal.get("entity_name", "").strip()
    proposed_status = proposal.get("proposed_status", "").strip()

    if not entity_name:
        return False, "Proposal is missing entity_name.", None

    if proposed_status not in VALID_STATUSES:
        return False, f"Proposed status '{proposed_status}' is not a valid status.", None

    # Search milestones first
    for m in milestones:
        if m.title.strip().lower() == entity_name.lower():
            if not is_transition_allowed(m.status, proposed_status):
                return False, (
                    f"Status transition from '{m.status}' to '{proposed_status}' is not allowed."
                ), None
            return True, None, m

    # Search issues
    for i in issues:
        title = getattr(i, "title", "").strip()
        if title.lower() == entity_name.lower():
            current = getattr(i, "status", "Open")
            if not is_transition_allowed(current, proposed_status):
                return False, (
                    f"Status transition from '{current}' to '{proposed_status}' is not allowed."
                ), None
            return True, None, i

    return False, (
        f"Entity '{entity_name}' does not belong to project '{project_id}' "
        f"or was not found in its milestones/issues."
    ), None
