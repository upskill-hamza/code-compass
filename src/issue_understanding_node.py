"""
issue_understanding_node.py

For each raw issue, this node asks an LLM to figure out:
- What's actually being asked (in plain language)
- What type of task it is (bug/feature/docs/refactor)
- Whether the comment thread clarified or changed the original scope
  (issues often drift from their original description once maintainers
  or other contributors weigh in - this catches that)
- Key terms (function names, file names, concepts) to help the next
  node (code_context_node) search the codebase effectively

Uses Groq's free tier with structured output (Pydantic + LangChain's
with_structured_output) so we get clean, parseable results instead of
having to regex a free-text response.
"""

import os
from typing import List

from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

from state import GraphState, IssueUnderstanding


class IssueUnderstandingSchema(BaseModel):
    summary: str = Field(description="Plain-language summary of what the issue actually needs, in 1-2 sentences")
    issue_type: str = Field(description="One of: bug, feature, docs, refactor, unclear")
    scope_clarified_in_comments: bool = Field(description="True if the comment thread changed or clarified what's actually needed compared to the original issue body")
    clarification_notes: str = Field(description="If scope_clarified_in_comments is true, briefly explain what changed. Empty string otherwise.")
    key_terms: List[str] = Field(description="Function names, file names, class names, or specific technical concepts mentioned in the issue or comments, useful for searching the codebase. Max 8 terms.")


SYSTEM_PROMPT = """You are analyzing a GitHub issue to help a developer understand \
what work is actually required. Read the issue title, body, and comment thread \
carefully.

Important: issue descriptions are often incomplete or get clarified/changed in \
the comments. A maintainer might say "actually this also needs X" or "this is \
simpler than it sounds, just change Y". Pay close attention to the comments for \
this kind of scope drift - it's the most valuable thing to catch, since it's \
exactly what a quick skim of the issue would miss.

Be concise and concrete. Avoid vague summaries like "this issue is about fixing \
a bug" - say what the bug actually is.

You must respond ONLY with a single JSON object matching this exact schema, \
no other text:
{
  "summary": string,
  "issue_type": one of "bug" | "feature" | "docs" | "refactor" | "unclear",
  "scope_clarified_in_comments": boolean (true or false, not a string),
  "clarification_notes": string (empty string if not applicable),
  "key_terms": array of strings (max 8)
}"""


def _build_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY not set. Get a free key at console.groq.com and add it to your .env file."
        )
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=api_key,
        temperature=0.1,  # low temperature - we want consistent, factual analysis, not creativity
    )
    # Using json_mode instead of the default function_calling method: Groq's
    # tool-calling occasionally emits "true"/"false" as JSON strings instead
    # of real booleans, which fails Groq's own strict server-side schema
    # validation before it ever reaches our code. json_mode is more lenient,
    # and Pydantic itself will coerce "true"/"false" strings into real
    # booleans during parsing, so this sidesteps the issue entirely.
    return llm.with_structured_output(IssueUnderstandingSchema, method="json_mode")


def understand_issue(structured_llm, issue: dict) -> IssueUnderstanding:
    """Runs the LLM analysis for a single issue and returns structured output."""
    comments_text = "\n\n".join(
        f"Comment {i+1}: {c}" for i, c in enumerate(issue.get("comments", []))
    ) or "(no comments)"

    user_prompt = f"""Issue Title: {issue['title']}

Issue Body:
{issue['body'] or '(no description provided)'}

Labels: {', '.join(issue.get('labels', [])) or '(none)'}

Comment Thread:
{comments_text}"""

    result: IssueUnderstandingSchema = structured_llm.invoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

    return IssueUnderstanding(
        summary=result.summary,
        issue_type=result.issue_type,
        scope_clarified_in_comments=result.scope_clarified_in_comments,
        clarification_notes=result.clarification_notes,
        key_terms=result.key_terms,
    )


def issue_understanding_node(state: GraphState) -> GraphState:
    """
    LangGraph node function: reads state['raw_issues'], produces understanding
    for each, stores intermediate result on state['enriched_issues'] (partially
    filled - later nodes add more fields to each entry).
    """
    structured_llm = _build_llm()
    enriched = []
    errors = list(state.get("errors", []))

    for issue in state["raw_issues"]:
        try:
            understanding = understand_issue(structured_llm, issue)
            enriched.append(
                {
                    "issue_number": issue["number"],
                    "title": issue["title"],
                    "url": issue["url"],
                    "labels": issue.get("labels", []),
                    "understanding": understanding,
                    # fields below get filled in by later nodes
                    "likely_files": [],
                    "code_context_summary": "",
                    "difficulty_score": 0.0,
                    "difficulty_reasoning": "",
                    "match_score": 0.0,
                    "match_reasoning": "",
                    "starting_point": "",
                }
            )
        except Exception as e:
            errors.append(f"Issue #{issue['number']}: failed understanding - {e}")

    state["enriched_issues"] = enriched
    state["errors"] = errors
    return state