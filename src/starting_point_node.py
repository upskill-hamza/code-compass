"""
starting_point_node.py

For the TOP N issues only (by match_score, from personalized_ranking_node's
final_ranked_list) - not all issues, to keep API usage sensible - this node:

1. Searches the repo for a similar already-merged PR, using the issue's
   key_terms as a search query (via GitHub's Search API)
2. Asks an LLM to draft a concrete starting point: which file/function to
   look at first, what the actual first code change probably looks like in
   plain language, and references the similar PR if one was found

This is plain free-text output (no structured schema needed here, unlike
earlier nodes) since the result is meant to be read directly, not parsed.
"""

import os
from langchain_groq import ChatGroq

from state import GraphState
from github_client import GitHubClient
from llm_utils import invoke_with_retry

DEFAULT_TOP_N = 3

SYSTEM_PROMPT = """You are helping a developer - possibly a beginner to open \
source - figure out exactly how to start working on a GitHub issue they've \
decided to take on.

Write a short, concrete starting point (3-5 sentences max). Be specific: \
name the actual file and function/area to look at first, and describe in \
plain language what the first code change probably looks like. Do not write \
actual code - just a clear, actionable plan a developer can follow.

If a similar merged PR is provided, mention it explicitly as a reference \
pattern to look at ("this past PR fixed a similar issue by doing X - your \
fix will likely follow a similar shape").

Do not be vague. Avoid phrases like "start by exploring the codebase" - the \
developer needs a specific first move, not general advice."""


def _build_llm():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY not set. Get a free key at console.groq.com and add it to your .env file."
        )
    return ChatGroq(model="openai/gpt-oss-120b", api_key=api_key, temperature=0.2)


def draft_starting_point(llm, enriched_issue: dict, similar_prs: list[dict]) -> str:
    understanding = enriched_issue["understanding"]

    if similar_prs:
        pr_text = "\n".join(f"- \"{pr['title']}\" ({pr['url']})" for pr in similar_prs)
    else:
        pr_text = "(none found)"

    user_prompt = f"""Issue: {enriched_issue['title']}
Summary: {understanding['summary']}
Issue type: {understanding['issue_type']}

Likely relevant files:
{chr(10).join(enriched_issue['likely_files']) or '(none found)'}

Code context:
{enriched_issue['code_context_summary'] or '(none available)'}

Similar past merged PRs in this repo:
{pr_text}"""

    response = invoke_with_retry(
        llm,
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.content.strip()


def starting_point_node(
    state: GraphState, github_client: GitHubClient, repo_owner: str, repo_name: str, top_n: int = DEFAULT_TOP_N
) -> GraphState:
    """
    NOTE: like code_context_node, this takes github_client/repo_owner/repo_name
    as explicit arguments rather than pulling them from state. github_client
    wraps a live network client (not serializable state); repo_owner/repo_name
    are passed explicitly too since none of the earlier test scripts actually
    populate those keys on the state dict - requiring them here instead avoids
    a silent KeyError if that stays true when this gets wired into main.py.
    """
    llm = _build_llm()
    errors = list(state.get("errors", []))

    ranked = state.get("final_ranked_list") or state["enriched_issues"]
    top_issues = ranked[:top_n]

    for enriched in top_issues:
        try:
            key_terms = enriched["understanding"].get("key_terms", [])
            similar_prs = github_client.search_merged_prs(
                repo_owner, repo_name, key_terms, max_results=3
            )
            enriched["starting_point"] = draft_starting_point(llm, enriched, similar_prs)
        except Exception as e:
            errors.append(f"Issue #{enriched['issue_number']}: failed starting point generation - {e}")
            enriched["starting_point"] = ""

    state["errors"] = errors
    return state