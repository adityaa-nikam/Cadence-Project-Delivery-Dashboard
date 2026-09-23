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
    Calls Groq to extract structured info from a raw update.
    """
    try:
        api_key = _get_api_key()
        if not api_key:
            return {
                "affected_milestone": "Unknown",
                "new_status": None,
                "summary": raw_text[:100] + "...",
                "error": "⚠️ GROQ_API_KEY not set. Showing raw text as summary.",
            }

        milestone_list_str = "\n".join(
            [f"- {m.title} (current status: {m.status})" for m in milestones]
        )

        prompt = f"""You are helping a delivery team log project status updates.

The project has these milestones:
{milestone_list_str}

Given this raw update text:
"{raw_text}"

Extract:
1. Which milestone/task title it most likely relates to.
   Use the EXACT title from the list above. If unclear, use null.
2. The new status — ONLY if the update implies the status should change
   (Open / Blocked / Done). If no status change is implied, use null.
3. A clean one-sentence summary suitable for a customer-facing update feed.
   Professional tone, no typos, factual.

Return ONLY valid JSON, no markdown, no explanation:
{{
  "affected_milestone": "<exact title from list or null>",
  "new_status": "<Open|Blocked|Done|null>",
  "summary": "<one professional sentence>"
}}"""

        text = _clean_response(_call_groq_api([{"role": "user", "content": prompt}], temperature=0.2, max_tokens=500))
        parsed = json.loads(text)

        if parsed.get("new_status") in [None, "null", ""]:
            parsed["new_status"] = None
        if parsed.get("affected_milestone") in [None, "null", ""]:
            parsed["affected_milestone"] = "Unknown"

        parsed["error"] = None
        return parsed

    except json.JSONDecodeError:
        try:
            match = re.search(r"\{.*?\}", text, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                if parsed.get("new_status") in [None, "null", ""]:
                    parsed["new_status"] = None
                if parsed.get("affected_milestone") in [None, "null", ""]:
                    parsed["affected_milestone"] = "Unknown"
                parsed["error"] = None
                return parsed
        except Exception:
            pass
        return {
            "affected_milestone": "Unknown",
            "new_status": None,
            "summary": "Update received — could not parse automatically.",
            "error": "⚠️ AI returned unexpected format. Summary approximated.",
        }
    except Exception as e:
        return {
            "affected_milestone": "Unknown",
            "new_status": None,
            "summary": raw_text[:120],
            "error": f"⚠️ AI call failed: {str(e)[:80]}",
        }


def get_project_health(project, milestones, issues, updates) -> dict:
    """
    Returns a health assessment for a project using Groq AI.
    """
    from datetime import datetime

    done_count = sum(1 for m in milestones if m.status == "Done")
    open_count = sum(1 for m in milestones if m.status == "Open")
    blocked_count = sum(1 for m in milestones if m.status == "Blocked")
    total_milestones = len(milestones)

    issue_by_cat = {}
    for issue in issues:
        issue_by_cat[issue.category] = issue_by_cat.get(issue.category, 0) + 1
    issue_breakdown = ", ".join([f"{v} {k}" for k, v in issue_by_cat.items()]) if issue_by_cat else "none"

    project_updates = [u for u in updates if u.project_id == project.id]
    days_since_update = 999
    if project_updates:
        try:
            latest = max(project_updates, key=lambda u: u.timestamp)
            latest_dt = datetime.fromisoformat(latest.timestamp)
            days_since_update = (datetime.now() - latest_dt).days
        except Exception:
            pass

    try:
        api_key = _get_api_key()
        if api_key:
            prompt = f"""You are a project delivery health analyzer. Assess the health of this project.

Project: {project.name} | Status: {project.overall_status}
Milestones: {done_count} Done, {open_count} Open, {blocked_count} Blocked out of {total_milestones} total
Issues: {len(issues)} open issues ({issue_breakdown})
Last update: {days_since_update} days ago | Total updates: {len(project_updates)}

Return ONLY valid JSON:
{{
  "score": <integer 0-100>,
  "grade": "<Healthy|At Risk|Critical>",
  "reasoning": "<exactly 2 sentences explaining the score>",
  "flags": ["<specific concern 1>", "<specific concern 2>"]
}}

Scoring guide:
- Start at 100
- Deduct 15 per Blocked milestone
- Deduct 5 per Open milestone past 50% of project
- Deduct 10 if last update > 7 days ago
- Deduct 10 if more than 2 open Bugs
- Healthy = 75-100, At Risk = 45-74, Critical = 0-44"""

            text = _clean_response(_call_groq_api([{"role": "user", "content": prompt}], temperature=0.2, max_tokens=500))
            parsed = json.loads(text)

            score = max(0, min(100, int(parsed.get("score", 0))))
            grade = parsed.get("grade", "Critical")
            if grade not in ["Healthy", "At Risk", "Critical"]:
                grade = "Critical"
            reasoning = parsed.get("reasoning", "Health assessment completed.")
            flags = parsed.get("flags", [])
            if not isinstance(flags, list):
                flags = []

            return {
                "score": score,
                "grade": grade,
                "reasoning": reasoning,
                "flags": flags,
                "error": None
            }
    except Exception:
        pass  # Fall through to local fallback

    score = 100
    score -= blocked_count * 15
    if total_milestones > 0 and open_count > total_milestones // 2:
        score -= (open_count - total_milestones // 2) * 5
    if days_since_update > 7:
        score -= 10
    bug_count = sum(1 for i in issues if i.category == "Bug")
    if bug_count > 2:
        score -= 10
    score = max(0, min(100, score))

    if score >= 75:
        grade = "Healthy"
    elif score >= 45:
        grade = "At Risk"
    else:
        grade = "Critical"

    flags = []
    if blocked_count > 0:
        flags.append(f"{blocked_count} milestone{'s' if blocked_count > 1 else ''} blocked")
    if days_since_update > 7:
        flags.append(f"No update for {days_since_update} days")
    if bug_count > 2:
        flags.append(f"{bug_count} open bugs")
    if open_count > total_milestones // 2 and total_milestones > 0:
        flags.append(f"{open_count} milestones still open")

    reasoning = f"Project scored {score}/100 based on {total_milestones} milestones and {len(issues)} open issues. "
    if flags:
        reasoning += f"Key concerns: {', '.join(flags)}."
    else:
        reasoning += "No major risks detected."

    return {
        "score": score,
        "grade": grade,
        "reasoning": reasoning,
        "flags": flags,
        "error": "⚠️ AI unavailable — using local calculation."
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


def query_projects(question: str, projects: list, milestones: list, 
                   issues: list, updates: list) -> str:
    """Query the full project dataset in natural language."""
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
        if not api_key:
            return "⚠️ AI query requires GROQ_API_KEY to be configured."

        return _call_groq_api([{"role": "user", "content": prompt}], temperature=0.3, max_tokens=500).strip()
    except Exception as e:
        return f"⚠️ Query failed: {str(e)[:100]}"