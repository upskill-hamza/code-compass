"""
difficulty_scoring_node.py

For each enriched issue (already has Phase 2 understanding + Phase 3 code
context), this node asks an LLM to estimate REAL difficulty - not based on
GitHub labels, but on:
- How many files are likely involved
- Whether the change touches core abstractions vs. leaf/isolated code
- Whether the issue type itself implies complexity (a "refactor" is usually
  harder than a "docs" fix)
- Whether scope was clarified/expanded in the comments (a sign the issue is
  trickier than its title suggests)

Outputs a 0.0-1.0 difficulty score, a plain-language reasoning string, and
a rough time estimate bucket - the time estimate is what the next node
(personalized_ranking_node) actually compares against the user's stated
time budget.
"""

import os
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

from state import GraphState


class DifficultyScoringSchema(BaseModel):
    difficulty_score: float = Field(description="0.0 (trivial) to 1.0 (very hard) difficulty estimate")
    difficulty_reasoning: str = Field(description="1-2 sentence plain-language explanation of why this score was given")
    estimated_time: str = Field(description="One of: 'few hours', 'a weekend', 'a week+'")


SYSTEM_PROMPT = """You are estimating the REAL difficulty of a GitHub issue for \
a developer deciding whether to work on it - not the difficulty implied by its \
labels, which are often stale or wrong.

Consider:
- How many files are likely involved (more files usually means more complexity \
and more places to break something)
- Whether the affected code looks like a core/shared abstraction (risky, needs \
care) versus an isolated/leaf piece of code (safer to change)
- The issue type: "docs" and small "bug" fixes are usually easier than \
"feature" or "refactor" work, but not always - use judgment based on the \
actual description, not just the type label
- Whether the comment thread clarified or expanded scope beyond the original \
description - this is often a sign the issue is trickier than it first looks
- Tests: if test files are among the likely-relevant files, the issue is \
probably more scoped/verifiable, which makes it a bit more approachable, not \
harder

Be realistic and specific in your reasoning - avoid generic statements like \
"this seems moderately difficult". Say what specifically makes it easy or hard.

You must respond ONLY with a single JSON object matching this exact schema, \
no other text:
{
  "difficulty_score": number between 0.0 and 1.0,
  "difficulty_reasoning": string,
  "estimated_time": one of "few hours" | "a weekend" | "a week+"
}"""


def _build_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY not set. Get a free key at console.groq.com and add it to your .env file."
        )
    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        api_key=api_key,
        temperature=0.1,
    )
    return llm.with_structured_output(DifficultyScoringSchema, method="json_mode")


def score_difficulty(structured_llm, enriched_issue: dict) -> dict:
    understanding = enriched_issue["understanding"]

    user_prompt = f"""Issue Title: {enriched_issue['title']}

Issue Summary: {understanding['summary']}
Issue Type: {understanding['issue_type']}
Scope clarified/changed in comments: {understanding['scope_clarified_in_comments']}
Clarification notes: {understanding['clarification_notes'] or '(none)'}
Key terms: {', '.join(understanding['key_terms'])}

Likely relevant files ({len(enriched_issue['likely_files'])} total):
{chr(10).join(enriched_issue['likely_files']) or '(none found)'}

Code context:
{enriched_issue['code_context_summary'] or '(no context available)'}"""

    result: DifficultyScoringSchema = structured_llm.invoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

    return {
        "difficulty_score": result.difficulty_score,
        "difficulty_reasoning": result.difficulty_reasoning,
        "estimated_time": result.estimated_time,
    }


def difficulty_scoring_node(state: GraphState) -> GraphState:
    structured_llm = _build_llm()
    errors = list(state.get("errors", []))

    for enriched in state["enriched_issues"]:
        try:
            scoring = score_difficulty(structured_llm, enriched)
            enriched["difficulty_score"] = scoring["difficulty_score"]
            enriched["difficulty_reasoning"] = scoring["difficulty_reasoning"]
            # estimated_time isn't in the EnrichedIssue schema from state.py,
            # but personalized_ranking_node needs it - stash it in
            # difficulty_reasoning's sibling field via a dict update. Since
            # EnrichedIssue is a TypedDict (not strict at runtime), this is
            # safe, but noted here explicitly for clarity.
            enriched["estimated_time"] = scoring["estimated_time"]
        except Exception as e:
            errors.append(f"Issue #{enriched['issue_number']}: failed difficulty scoring - {e}")
            enriched["difficulty_score"] = 0.5  # neutral fallback, not 0 - avoids falsely looking "easy"
            enriched["difficulty_reasoning"] = "Could not be scored due to an error."
            enriched["estimated_time"] = "a weekend"  # neutral fallback

    state["errors"] = errors
    return state