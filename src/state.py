"""
state.py

Shared state schema for the Issue Matchmaker LangGraph pipeline.
Every node reads from and writes to this shared state.
"""

from typing import TypedDict, List, Optional


class SkillProfile(TypedDict):
    languages: List[str]
    frameworks: List[str]
    experience_level: str  # "beginner" | "intermediate" | "advanced"
    time_available: str    # "few hours" | "a weekend" | "a week+"
    interests: List[str]


class IssueUnderstanding(TypedDict):
    """Structured output from the issue_understanding_node."""
    summary: str                 # plain-language summary of what's actually needed
    issue_type: str              # "bug" | "feature" | "docs" | "refactor" | "unclear"
    scope_clarified_in_comments: bool  # did comments change/clarify the original ask?
    clarification_notes: str     # what changed, if anything (empty string if not)
    key_terms: List[str]         # function/class/file names or concepts mentioned


class EnrichedIssue(TypedDict):
    issue_number: int
    title: str
    url: str
    labels: List[str]
    understanding: IssueUnderstanding
    likely_files: List[str]
    code_context_summary: str
    difficulty_score: float
    difficulty_reasoning: str
    match_score: float
    match_reasoning: str
    starting_point: str


class GraphState(TypedDict):
    repo_owner: str
    repo_name: str
    skill_profile: SkillProfile
    raw_issues: List[dict]          # IssueRecord objects as dicts
    enriched_issues: List[EnrichedIssue]
    final_ranked_list: List[EnrichedIssue]
    errors: List[str]
