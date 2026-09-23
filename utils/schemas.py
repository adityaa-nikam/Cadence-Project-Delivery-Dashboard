"""Pydantic v2 schema models for AI output validation in Cadence."""

from typing import List, Optional
from pydantic import BaseModel, Field


class RiskProposal(BaseModel):
    """Structured AI-proposed risk event."""

    title: str = Field(description="Short risk title")
    severity: str = Field(description="Severity level: HIGH, MEDIUM, or LOW")
    impact: str = Field(default="", description="Potential impact description")
    recommended_action: str = Field(default="", description="Suggested mitigation action")
    affected_milestone: Optional[str] = Field(default=None, description="Affected milestone title or null")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score 0.0-1.0")


class StatusChangeProposal(BaseModel):
    """Structured AI-proposed milestone or issue status change."""

    entity_type: str = Field(description="Entity type: Milestone or Issue")
    entity_name: str = Field(description="Exact entity title matching known entities")
    previous_status: Optional[str] = Field(default=None, description="Current status before change")
    proposed_status: str = Field(description="Proposed new status: Open, Blocked, Done, In Progress")
    reason: str = Field(default="", description="Justification for the proposed change")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Confidence score 0.0-1.0")


class ProjectUpdateAnalysis(BaseModel):
    """Complete structured AI analysis result for a raw project status update."""

    summary: str = Field(description="Clean 1-sentence executive summary")
    affected_milestones: List[str] = Field(default_factory=list, description="List of affected milestone titles")
    affected_issues: List[str] = Field(default_factory=list, description="List of affected issue titles")
    risks: List[RiskProposal] = Field(default_factory=list, description="Detected risks")
    status_changes: List[StatusChangeProposal] = Field(default_factory=list, description="Proposed status changes")
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Overall extraction confidence")
    reasoning_summary: str = Field(default="", description="Brief AI reasoning explanation")
