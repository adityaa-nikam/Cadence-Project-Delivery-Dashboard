"""Deterministic health scoring engine for Cadence projects.

All scores are calculated purely from database state — no LLM involvement.
This ensures that identical inputs always produce identical outputs.
"""

from datetime import datetime, timezone


def compute_project_health(project, milestones: list, issues: list, updates: list) -> dict:
    """Compute a deterministic health score (0-100) and grade for a project.

    Scoring algorithm:
        Start at 100, apply deductions for risk factors:
        - Blocked milestones: -15 each
        - Open issues (severity=High): -10 each
        - Open issues (severity=Medium): -5 each
        - Open issues (severity=Low): -2 each
        - No updates in last 7 days: -10
        - Overall status is "At Risk": -15
        - Overall status is "Blocked": -25
        - More than 50% milestones incomplete: -10

    Returns:
        dict with keys: score, grade, flags, breakdown
    """
    score = 100
    flags: list[str] = []
    breakdown: list[str] = []

    # 1. Blocked milestones penalty
    blocked_milestones = [m for m in milestones if getattr(m, "status", "") == "Blocked"]
    if blocked_milestones:
        penalty = len(blocked_milestones) * 15
        score -= penalty
        breakdown.append(f"-{penalty} pts: {len(blocked_milestones)} blocked milestone(s)")
        flags.append("BLOCKED_MILESTONES")

    # 2. Open issue severity penalties
    open_issues = [i for i in issues if getattr(i, "status", "") in ("Open", "In Progress")]
    high_issues = [i for i in open_issues if getattr(i, "severity", "").lower() in ("high", "critical")]
    medium_issues = [i for i in open_issues if getattr(i, "severity", "").lower() == "medium"]
    low_issues = [i for i in open_issues if getattr(i, "severity", "").lower() == "low"]

    if high_issues:
        penalty = len(high_issues) * 10
        score -= penalty
        breakdown.append(f"-{penalty} pts: {len(high_issues)} high-severity open issue(s)")
        flags.append("HIGH_SEVERITY_ISSUES")

    if medium_issues:
        penalty = len(medium_issues) * 5
        score -= penalty
        breakdown.append(f"-{penalty} pts: {len(medium_issues)} medium-severity open issue(s)")

    if low_issues:
        penalty = len(low_issues) * 2
        score -= penalty
        breakdown.append(f"-{penalty} pts: {len(low_issues)} low-severity open issue(s)")

    # 3. Staleness penalty (no recent updates)
    if updates:
        try:
            latest_ts = max(
                datetime.fromisoformat(u.timestamp.replace("Z", "+00:00"))
                for u in updates
                if getattr(u, "timestamp", None)
            )
            days_since = (datetime.now(timezone.utc) - latest_ts).days
            if days_since > 7:
                score -= 10
                breakdown.append(f"-10 pts: No updates in {days_since} days")
                flags.append("STALE_PROJECT")
        except (ValueError, TypeError):
            pass
    else:
        score -= 10
        breakdown.append("-10 pts: No project updates recorded")
        flags.append("NO_UPDATES")

    # 4. Overall status penalty
    status = getattr(project, "overall_status", "On Track")
    if status == "At Risk":
        score -= 15
        breakdown.append("-15 pts: Project flagged At Risk")
        flags.append("AT_RISK")
    elif status == "Blocked":
        score -= 25
        breakdown.append("-25 pts: Project flagged Blocked")
        flags.append("PROJECT_BLOCKED")

    # 5. Milestone completion ratio & full completion bonus
    total_ms = len(milestones)
    done_ms = sum(1 for m in milestones if getattr(m, "status", "") == "Done")
    if total_ms > 0 and done_ms == total_ms:
        # 100% milestones delivered -> ensure high health score (95+)
        score = max(score + 20, 95)
        breakdown.append("+20 pts: 100% Milestones Delivered")
        flags.append("ALL_DELIVERABLES_DONE")
    elif total_ms > 0 and (done_ms / total_ms) < 0.5:
        score -= 10
        breakdown.append(f"-10 pts: Only {done_ms}/{total_ms} milestones completed")
        flags.append("LOW_COMPLETION")

    # Clamp score
    score = max(0, min(100, score))

    # Grade assignment
    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"

    return {
        "score": score,
        "grade": grade,
        "flags": flags,
        "breakdown": breakdown,
    }
