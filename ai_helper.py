"""AI-powered update parsing with Groq (OpenAI-compatible API), robust fallback, and safe key loading."""

import json
import os
import re

import streamlit as st

# Groq API - supported models list with fallback
GROQ_MODELS = [
    "qwen/qwen3.8-27b",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "llama-3.1-8b-instant",
]
GROQ_MODEL = GROQ_MODELS[0]
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _get_api_key() -> str:
    """Get API key from environment, dotenv, or Streamlit secrets."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    key = os.environ.get("GROQ_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("GROQ_API_KEY", "") or st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            pass
    return key.strip()


def _call_groq_api(messages: list, temperature: float = 0.3, max_tokens: int = 500) -> str:
    """
    Call Groq API using OpenAI SDK or urllib HTTP fallback across supported models.
    Returns response text string or raises Exception.
    """
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    last_exception = None

    # 1. Try OpenAI SDK across candidate models
    try:
        from openai import OpenAI
        client = OpenAI(base_url=GROQ_BASE_URL, api_key=api_key)
        for model in GROQ_MODELS:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_exception = e
                continue
    except Exception as e:
        last_exception = e

    # 2. Direct HTTP Fallback across candidate models
    import urllib.request
    for model in GROQ_MODELS:
        try:
            req = urllib.request.Request(
                f"{GROQ_BASE_URL}/chat/completions",
                data=json.dumps({
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            last_exception = e
            continue

    if last_exception:
        raise last_exception
    raise RuntimeError("Failed to get response from Groq API.")



def _clean_response(text: str) -> str:
    """Remove markdown code fences from API response."""
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def parse_update(raw_text: str, milestones: list) -> dict:
    """
    Extract structured update proposals, confidence, risks, and summary using Groq AI and Pydantic.
    """
    from utils.schemas import ProjectUpdateAnalysis, StatusChangeProposal, RiskProposal

    if not raw_text or not raw_text.strip():
        return {
            "summary": "Empty update provided.",
            "affected_milestones": [],
            "affected_issues": [],
            "risks": [],
            "status_changes": [],
            "overall_confidence": 0.0,
            "reasoning_summary": "Empty input text.",
            "affected_milestone": "Unknown",
            "new_status": None,
            "error": "Empty update text provided.",
        }

    milestone_list_str = "\n".join(
        [f"- {m.title} (current status: {m.status})" for m in milestones]
    )

    prompt = f"""You are a senior AI project delivery analyst. Analyze this project status update.

Target Project Milestones:
{milestone_list_str}

Raw Update Text:
"{raw_text}"

Instructions:
1. Extract a clean 1-sentence executive summary suitable for a customer status feed.
2. List affected milestone titles matching the EXACT titles above.
3. Identify any proposed status changes for milestones (Open, Blocked, Done, In Progress). Only propose changes clearly implied by the update.
CRITICAL CONSTRAINT ON PREREQUISITES vs MILESTONES:
Do NOT interpret prerequisite completion or dependency approval as milestone completion.
For example, if the update text says "Firewall approval has been completed, clearing a prerequisite for firewall rules configuration", do NOT propose setting the milestone "Firewall Rules Configuration" to "Done", because completing a prerequisite is NOT completing the milestone itself.
Only propose setting a milestone status to "Done" if the update text explicitly states that the target milestone ITSELF is complete, finished, delivered, or verified.
4. Estimate a realistic confidence score (0.0 to 1.0) for each status change.
5. Identify any new risks (severity HIGH, MEDIUM, LOW) with recommended action.

Return ONLY valid JSON matching this schema:
{{
  "summary": "<clean 1-sentence summary>",
  "affected_milestones": ["<exact title from list>"],
  "affected_issues": [],
  "risks": [
    {{
      "title": "<short risk title>",
      "severity": "HIGH|MEDIUM|LOW",
      "impact": "<potential impact>",
      "recommended_action": "<suggested action>",
      "affected_milestone": "<milestone title or null>",
      "confidence": 0.85
    }}
  ],
  "status_changes": [
    {{
      "entity_type": "Milestone",
      "entity_name": "<exact title from list>",
      "previous_status": "<Open|Blocked|Done|null>",
      "proposed_status": "<Open|Blocked|Done|In Progress>",
      "reason": "<justification>",
      "confidence": 0.90
    }}
  ],
  "overall_confidence": 0.92,
  "reasoning_summary": "<brief explanation>"
}}"""

    try:
        api_key = _get_api_key()
        if not api_key:
            return {
                "summary": raw_text[:100] + "...",
                "affected_milestones": [],
                "affected_issues": [],
                "risks": [],
                "status_changes": [],
                "overall_confidence": 0.5,
                "reasoning_summary": "API Key missing.",
                "affected_milestone": "Unknown",
                "new_status": None,
                "error": "⚠️ GROQ_API_KEY not set. Showing raw text.",
            }

        text = _clean_response(_call_groq_api([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=700))
        parsed_dict = json.loads(text)

        # Validate with Pydantic
        analysis = ProjectUpdateAnalysis.model_validate(parsed_dict)
        analysis_dict = analysis.model_dump()

        # Legacy compatibility keys for existing UI widgets
        affected_ms = analysis_dict["affected_milestones"][0] if analysis_dict["affected_milestones"] else "Unknown"
        first_change = analysis_dict["status_changes"][0] if analysis_dict["status_changes"] else None
        new_st = first_change["proposed_status"] if first_change else None

        analysis_dict["affected_milestone"] = affected_ms
        analysis_dict["new_status"] = new_st
        analysis_dict["error"] = None
        return analysis_dict

    except Exception as e:
        # Graceful fallback: zero state mutation on failure
        return {
            "summary": raw_text[:120],
            "affected_milestones": [],
            "affected_issues": [],
            "risks": [],
            "status_changes": [],
            "overall_confidence": 0.0,
            "reasoning_summary": f"Fallback due to error: {str(e)}",
            "affected_milestone": "Unknown",
            "new_status": None,
            "error": f"⚠️ AI extraction fallback: {str(e)[:100]}",
        }


def get_project_health(project, milestones, issues, updates) -> dict:
    """
    Calculate deterministic project health in Python and use Groq AI to explain the score.
    AI explains the score; Python calculates it.
    """
    from utils.health_engine import compute_project_health

    health = compute_project_health(project, milestones, issues, updates)
    score = health["score"]
    grade = health["grade"]
    flags = health["flags"]
    breakdown = health["breakdown"]

    if breakdown:
        reasoning = f"{project.name} received a {grade} rating ({score}/100) due to: {', '.join(breakdown)}. The team should focus on resolving these active risk factors to ensure delivery stability."
    else:
        reasoning = f"{project.name} achieved an optimal {score}/100 health score ({grade}), driven by complete milestone progress and zero active delivery blockages."

    return {
        "score": score,
        "grade": grade,
        "reasoning": reasoning,
        "flags": flags,
        "error": None,
    }


def draft_customer_email(project, milestones, issues, updates) -> dict:
    """
    Generates a professional customer-facing status update email using Groq.
    """
    done_ms = [m for m in milestones if m.status == "Done" and not m.internal_only]
    open_ms = [m for m in milestones if m.status == "Open" and not m.internal_only]
    blocked_ms = [m for m in milestones if m.status == "Blocked" and not m.internal_only]

    project_updates = [u for u in updates if u.project_id == project.id]
    recent_updates = sorted(project_updates, key=lambda u: u.timestamp, reverse=True)[:3]
    summaries = [u.structured_summary for u in recent_updates if u.structured_summary]

    prompt = f"""You are a professional Solutions Engineer writing a project 
status update email to a customer. Write a concise, confident, professional email.

Project: {project.name}
Overall Status: {project.overall_status}
Completed Milestones: {[m.title for m in done_ms]}
In Progress: {[m.title for m in open_ms]}
Blocked Items: {[m.title for m in blocked_ms]}
Recent Activity: {summaries}

Rules:
- 3 paragraphs maximum
- Never mention internal notes, internal processes, or team names
- If there are blocked items: acknowledge them briefly and state action being taken
- If everything is on track: be positive but professional, not salesy
- End with a clear next step or expected update date
- Subject line: 7 words or less, specific to this project

Return ONLY valid JSON:
{{
  "subject": "<email subject>",
  "body": "<full email body, use \\n for line breaks>",
  "tone": "<positive|cautious|urgent>"
}}"""

    try:
        api_key = _get_api_key()
        if not api_key:
            return {
                "subject": f"{project.name} — Status Update",
                "body": "GROQ_API_KEY is missing. Please set your API key in .env.",
                "tone": "cautious",
                "error": "API key not set"
            }

        text = _clean_response(_call_groq_api([{"role": "user", "content": prompt}], temperature=0.3, max_tokens=800))
        parsed = json.loads(text.strip())
        parsed["error"] = None
        return parsed
    except Exception as e:
        return {
            "subject": f"{project.name} — Status Update",
            "body": f"Could not generate email: {str(e)[:100]}",
            "tone": "cautious",
            "error": str(e)
        }


def _deterministic_query_projects(question: str, projects: list, milestones: list,
                                   issues: list, updates: list) -> str:
    """Deterministic, factual database answer fallback when LLM is unavailable or fails."""
    q_lower = question.lower().strip()

    # 1. Blocked projects or milestones
    if "blocked" in q_lower:
        blocked_items = []
        for p in projects:
            p_ms = [m for m in milestones if m.project_id == p.id and m.status == "Blocked"]
            if p.overall_status == "Blocked" or p_ms:
                ms_names = [f"'{m.title}'" for m in p_ms]
                ms_str = f" ({', '.join(ms_names)})" if ms_names else ""
                blocked_items.append(f"**{p.name}**{ms_str}")
        if blocked_items:
            return f"The following project(s) have blocked status or deliverables: {'; '.join(blocked_items)}."
        return "No projects currently have blocked milestones or blocked status."

    # 2. Risk / At Risk
    if "risk" in q_lower:
        at_risk = [p.name for p in projects if p.overall_status in ["At Risk", "Critical"]]
        if at_risk:
            return f"Projects currently flagged as At Risk: **{', '.join(at_risk)}**."
        return "No projects are currently flagged as At Risk."

    # 3. Ownership / Who owns
    if "own" in q_lower or "owner" in q_lower:
        matched = []
        for p in projects:
            p_name_clean = p.name.lower()
            words = [w for w in p_name_clean.split() if len(w) > 3]
            if p_name_clean in q_lower or any(w in q_lower for w in words):
                owners_str = ", ".join(p.owners) if p.owners else "Unassigned"
                matched.append(f"**{p.name}** is owned by {owners_str}.")
        if matched:
            return " ".join(matched)

        all_owners = []
        for p in projects:
            owners_str = ", ".join(p.owners) if p.owners else "Unassigned"
            all_owners.append(f"**{p.name}**: {owners_str}")
        return "Project ownership: " + " | ".join(all_owners)

    # 4. Open Bugs / Issues
    if "bug" in q_lower or "issue" in q_lower:
        issue_items = []
        for p in projects:
            p_issues = [i for i in issues if i.project_id == p.id]
            if p_issues:
                iss_descs = [f"'{getattr(i, 'title', 'Issue')}' ({getattr(i, 'severity', 'Medium')})" for i in p_issues]
                issue_items.append(f"**{p.name}**: {', '.join(iss_descs)}")
        if issue_items:
            return "Open issues & bugs in portfolio: " + " | ".join(issue_items)
        return "No open bugs or issues found in the portfolio."

    # 5. Default portfolio summary
    summary_parts = []
    for p in projects:
        p_ms = [m for m in milestones if m.project_id == p.id]
        done = sum(1 for m in p_ms if m.status == "Done")
        total = len(p_ms)
        summary_parts.append(f"**{p.name}** ({p.overall_status}, {done}/{total} milestones completed)")

    return f"Portfolio Database Overview: {'; '.join(summary_parts)}."


def query_projects(question: str, projects: list, milestones: list, 
                   issues: list, updates: list) -> str:
    """Query the full project dataset in natural language with AI and deterministic fallback."""
    context_parts = []
    for p in projects:
        p_milestones = [m for m in milestones if m.project_id == p.id]
        p_updates = sorted(
            [u for u in updates if u.project_id == p.id],
            key=lambda u: u.timestamp, reverse=True
        )
        p_issues = [i for i in issues if i.project_id == p.id]
        
        done = sum(1 for m in p_milestones if m.status == "Done")
        blocked = sum(1 for m in p_milestones if m.status == "Blocked")
        total = len(p_milestones)
        last_update = p_updates[0].timestamp[:10] if p_updates else "No updates"
        
        context_parts.append(
            f"Project: {p.name} | Owners: {', '.join(p.owners)} | "
            f"Status: {p.overall_status} | "
            f"Milestones: {done}/{total} Done, {blocked} Blocked | "
            f"Issues: {len(p_issues)} | Last update: {last_update}"
        )
    
    context = "\n".join(context_parts)
    
    prompt = f"""You are a helpful project status assistant for a delivery team.
Answer questions about project status based ONLY on the data below.
Be concise (2-3 sentences max). Be specific — use project names and numbers.
If you cannot answer from the data, say so honestly.

Project Data:
{context}

Question: {question}

Answer:"""
    
    try:
        api_key = _get_api_key()
        if api_key:
            return _call_groq_api([{"role": "user", "content": prompt}], temperature=0.3, max_tokens=500).strip()
    except Exception:
        pass

    return _deterministic_query_projects(question, projects, milestones, issues, updates)