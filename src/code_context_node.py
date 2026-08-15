"""
code_context_node.py

For each enriched issue (already processed by issue_understanding_node),
this node queries the repo's vector index to find files/code likely
relevant to that issue - using the issue's summary + key_terms as the
search query.

If the top results all have weak similarity (high distance), the node
retries once with a broader query built only from key_terms (dropping
the summary text) - this is the "loop back with alt search strategy"
mentioned in the original spec, implemented here as a simple retry rather
than a full graph cycle, since a single retry covers the common case
without adding real graph complexity.
"""

from state import GraphState
from repo_indexer import RepoIndex

TOP_K = 5
WEAK_MATCH_DISTANCE_THRESHOLD = 1.5  # Chroma's default distance metric (cosine-ish); tune after seeing real results


def _build_query(understanding: dict, use_key_terms_only: bool = False) -> str:
    if use_key_terms_only:
        return " ".join(understanding.get("key_terms", []))
    terms = " ".join(understanding.get("key_terms", []))
    return f"{understanding.get('summary', '')} {terms}".strip()


def _query_with_retry(index: RepoIndex, understanding: dict) -> list[dict]:
    query = _build_query(understanding)
    results = index.query(query, top_k=TOP_K)

    if not results:
        return results

    best_distance = min(r["distance"] for r in results)
    if best_distance > WEAK_MATCH_DISTANCE_THRESHOLD:
        # Weak match - retry with a narrower, key-terms-only query
        retry_query = _build_query(understanding, use_key_terms_only=True)
        if retry_query.strip():
            retry_results = index.query(retry_query, top_k=TOP_K)
            if retry_results and min(r["distance"] for r in retry_results) < best_distance:
                return retry_results

    return results


def code_context_node(state: GraphState, index: RepoIndex) -> GraphState:
    """
    NOTE: unlike other nodes, this one takes `index` as an explicit second
    argument rather than pulling it from state. A built RepoIndex wraps a
    live Chroma collection object, which isn't naturally JSON-serializable -
    keeping it out of the TypedDict state avoids confusion if this graph is
    ever run with LangGraph's checkpointing/persistence enabled. The caller
    (graph wiring in main.py) is responsible for building the index once per
    repo and passing it through.
    """
    errors = list(state.get("errors", []))

    for enriched in state["enriched_issues"]:
        try:
            results = _query_with_retry(index, enriched["understanding"])
            enriched["likely_files"] = sorted(
                set(r["file_path"] for r in results if r["file_path"])
            )
            if results:
                summary_lines = [
                    f"- {r['file_path']} (around line {r['start_line_estimate']})"
                    for r in results
                ]
                enriched["code_context_summary"] = "\n".join(summary_lines)
            else:
                enriched["code_context_summary"] = "No relevant files found in index."
        except Exception as e:
            errors.append(f"Issue #{enriched['issue_number']}: failed code context - {e}")
            enriched["likely_files"] = []
            enriched["code_context_summary"] = ""

    state["errors"] = errors
    return state
