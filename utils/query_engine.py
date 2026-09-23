"""Intent-based natural language project query engine with parameterized database execution."""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ai_helper import _call_groq_api, _clean_response, _get_api_key
from utils import services
from utils.health_engine import compute_project_health


class QueryIntent(BaseModel):
    """Extracted intent for structured project querying."""

    intent_type: str = Field(
        description="Query intent type: STALE_PROJECTS, BLOCKED_MILESTONES, PROJECT_RISK_REASON, GO_LIVE_BLOCKERS, HIGH_SEVERITY_ISSUES, GENERAL"
    )
    target_project_id: Optional[str] = Field(default=None, description="Target project ID if question references a specific project")
    days_threshold: Optional[int] = Field(default=7, description="Days threshold if querying staleness")
    severity_filter: Optional[str] = Field(default=None, description="Severity filter if querying issues or risks")


def extract_query_intent(question: str, projects: list) -> QueryIntent:
    """Extract structured QueryIntent using LLM."""
    proj_map = "\n".join([f"- {p.id}: {p.name}" for p in projects])

    prompt = f"""You are a query intent classifier for a project delivery workspace.

Available Projects:
{proj_map}

User Question:
"{question}"

Classify into ONLY ONE intent_type:
- STALE_PROJECTS (questions about updates missing in X days, stale projects)
- BLOCKED_MILESTONES (questions about blocked tasks, deliverables, or milestones)
- PROJECT_RISK_REASON (questions asking why a specific project is at risk or critical)
- GO_LIVE_BLOCKERS (questions about launch delays, pilot risks, go-live blockers)
- HIGH_SEVERITY_ISSUES (questions about bugs, high severity issues, open support items)
- GENERAL (any other portfolio summary question)

Return ONLY valid JSON:
{{
  "intent_type": "<STALE_PROJECTS|BLOCKED_MILESTONES|PROJECT_RISK_REASON|GO_LIVE_BLOCKERS|HIGH_SEVERITY_ISSUES|GENERAL>",
  "target_project_id": "<project_id or null>",
  "days_threshold": 7,
  "severity_filter": "<HIGH|null>"
}}"""

    try:
        api_key = _get_api_key()
        if api_key:
            resp = _clean_response(_call_groq_api([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=200))
            parsed = json.loads(resp)
            return QueryIntent.model_validate(parsed)
    except Exception:
        pass

    # Heuristic fallback if LLM intent extraction fails
    q_lower = question.lower()
    if "stale" in q_lower or "7 days" in q_lower or "not updated" in q_lower:
        return QueryIntent(intent_type="STALE_PROJECTS", days_threshold=7)
    elif "blocked" in q_lower:
        return QueryIntent(intent_type="BLOCKED_MILESTONES")
    elif "risk" in q_lower or "novabridge" in q_lower or "why" in q_lower:
        target = "novabridge" if "novabridge" in q_lower else ("orion" if "orion" in q_lower else None)
        return QueryIntent(intent_type="PROJECT_RISK_REASON", target_project_id=target)
    elif "bug" in q_lower or "issue" in q_lower or "high" in q_lower:
        return QueryIntent(intent_type="HIGH_SEVERITY_ISSUES", severity_filter="HIGH")

    return QueryIntent(intent_type="GENERAL")


def execute_intent_query(question: str, db_url: str | None = None) -> str:
    """
    Execute structured intent-based query against persistent database.
    LLM explains structured facts; LLM does NOT execute direct SQL.
    """
    projects = services.get_projects(db_url=db_url)
    intent = extract_query_intent(question, projects)

    structured_facts = []

    if intent.intent_type == "STALE_PROJECTS":
        from pages.overview import is_project_stale
        threshold = intent.days_threshold or 7
        stale_projects = []
        for p in projects:
            p_updates = services.get_project_updates(p.id, db_url=db_url)
            if is_project_stale(p.id, p_updates, days_threshold=threshold):
                stale_projects.append(f"{p.name} (ID: {p.id}, Lead: {', '.join(p.owners)})")

        if stale_projects:
            structured_facts.append(f"Projects without updates in >{threshold} days: " + ", ".join(stale_projects))
        else:
            structured_facts.append(f"No projects are stale (all updated within {threshold} days).")

    elif intent.intent_type == "BLOCKED_MILESTONES":
        blocked_items = []
        for p in projects:
            ms_list = services.get_project_milestones(p.id, db_url=db_url)
            for m in ms_list:
                if m.status == "Blocked":
                    blocked_items.append(f"{p.name} -> Milestone '{m.title}' (Due {m.due_date})")

        if blocked_items:
            structured_facts.append("Currently Blocked Milestones: " + "; ".join(blocked_items))
        else:
            structured_facts.append("No milestones are currently blocked.")

    elif intent.intent_type == "PROJECT_RISK_REASON" and intent.target_project_id:
        p_id = intent.target_project_id
        target_p = services.get_project(p_id, db_url=db_url)
        if target_p:
            ms = services.get_project_milestones(p_id, db_url=db_url)
            issues = services.get_project_issues(p_id, db_url=db_url)
            upds = services.get_project_updates(p_id, db_url=db_url)
            health = compute_project_health(target_p, ms, issues, upds)

            structured_facts.append(
                f"Project {target_p.name} Status: {target_p.overall_status}, Health Score: {health['score']}/100 ({health['grade']}). "
                f"Concerns: {', '.join(health['flags'])}. Deductions: {', '.join(health['breakdown'])}."
            )

    elif intent.intent_type == "HIGH_SEVERITY_ISSUES":
        high_issues = []
        for p in projects:
            issues = services.get_project_issues(p.id, db_url=db_url)
            for i in issues:
                if getattr(i, "severity", "") == "High" or getattr(i, "category", "") == "Bug":
                    high_issues.append(f"{p.name}: {i.category} '{i.title}' ({getattr(i, 'severity', 'High')})")

        if high_issues:
            structured_facts.append("Open High Severity Issues & Bugs: " + "; ".join(high_issues))
        else:
            structured_facts.append("No open high-severity issues reported.")

    if not structured_facts:
        # Fallback to complete portfolio facts
        portfolio_parts = []
        for p in projects:
            ms = services.get_project_milestones(p.id, db_url=db_url)
            done = sum(1 for m in ms if m.status == "Done")
            blocked = sum(1 for m in ms if m.status == "Blocked")
            portfolio_parts.append(f"{p.name} ({p.overall_status}): {done}/{len(ms)} Done, {blocked} Blocked.")
        structured_facts.append("Portfolio Summary: " + " ".join(portfolio_parts))

    facts_text = "\n".join(structured_facts)

    prompt = f"""You are Cadence, an AI delivery intelligence assistant.
Synthesize a concise, executive-ready answer (2-3 sentences max) based STRICTLY on these database facts.

Database Facts:
{facts_text}

User Question:
"{question}"

Answer:"""

    try:
        api_key = _get_api_key()
        if api_key:
            return _call_groq_api([{"role": "user", "content": prompt}], temperature=0.2, max_tokens=300).strip()
    except Exception:
        pass

    return facts_text


def query_project_intelligence(question: str, db_url: str | None = None) -> dict:
    """
    Query project intelligence and return structured result dictionary.
    Includes extracted intent, synthesized answer, and raw SQL safety flag.
    """
    projects = services.get_projects(db_url=db_url)
    intent = extract_query_intent(question, projects)
    answer = execute_intent_query(question, db_url=db_url)

    return {
        "question": question,
        "intent": intent.intent_type,
        "target_project_id": intent.target_project_id,
        "answer": answer,
        "executed_raw_sql": False,
    }

