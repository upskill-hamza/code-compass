"""
graph.py

Wires all 5 backend nodes into a single LangGraph StateGraph:

    fetch_issues -> understand_issues -> build_index -> code_context
        -> difficulty_scoring -> personalized_ranking -> starting_point -> END

This is what Phase 7's FastAPI backend will call as a single unit.

Design note on external resources (GitHubClient, the Chroma index):
code_context_node and starting_point_node both need access to a live
GitHubClient and/or the built repo index, but neither of those belongs in
GraphState (state.py) - they're not JSON-serializable and aren't really
"pipeline data", they're infrastructure. Rather than smuggle them through
state, build_graph() below builds them once as closures over the node
functions, matching the pattern already used when calling these nodes
directly (see run_phase4_test.py / the Phase 5 test script).

Design note on build_index's position in the graph: it only depends on
repo_owner/repo_name (known before the graph even starts), not on anything
fetch_issues or understand_issues produce. It's placed sequentially after
understand_issues here for simplicity, but it could run in parallel with
those two steps as a real optimization later (LangGraph supports parallel
branches) - noted here rather than implemented now, since correctness comes
first.
"""

from langgraph.graph import StateGraph, END

from state import GraphState, SkillProfile
from github_client import GitHubClient
from issue_understanding_node import issue_understanding_node
from repo_indexer import build_repo_index
from code_context_node import code_context_node
from difficulty_scoring_node import difficulty_scoring_node
from personalized_ranking_node import personalized_ranking_node
from starting_point_node import starting_point_node


def build_graph(
    repo_owner: str,
    repo_name: str,
    skill_profile: SkillProfile,
    max_issues: int = 10,
    top_n_starting_points: int = 3,
):
    """
    Builds and compiles the full Code Compass pipeline as a LangGraph
    graph, bound to a specific repo and skill profile.

    Returns a compiled graph - call .invoke({}) on it to run the full
    pipeline (the initial empty dict is fine since fetch_issues below fills
    in repo_owner/repo_name/skill_profile/raw_issues itself).
    """
    client = GitHubClient()
    index_holder: dict = {}  # closure cell for the built repo index (not JSON-serializable, kept out of state)

    def fetch_issues(state: GraphState) -> GraphState:
        issues = client.fetch_open_issues(repo_owner, repo_name, max_issues=max_issues)
        state["repo_owner"] = repo_owner
        state["repo_name"] = repo_name
        state["skill_profile"] = skill_profile
        state["raw_issues"] = [i.__dict__ for i in issues]
        state["errors"] = state.get("errors", [])
        return state

    def build_index(state: GraphState) -> GraphState:
        index_holder["index"] = build_repo_index(repo_owner, repo_name)
        return state

    def code_context(state: GraphState) -> GraphState:
        return code_context_node(state, index_holder["index"])

    def starting_point(state: GraphState) -> GraphState:
        return starting_point_node(state, client, repo_owner, repo_name, top_n=top_n_starting_points)

    graph = StateGraph(GraphState)
    graph.add_node("fetch_issues", fetch_issues)
    graph.add_node("understand_issues", issue_understanding_node)
    graph.add_node("build_index", build_index)
    graph.add_node("code_context", code_context)
    graph.add_node("difficulty_scoring", difficulty_scoring_node)
    graph.add_node("personalized_ranking", personalized_ranking_node)
    graph.add_node("starting_point", starting_point)

    graph.set_entry_point("fetch_issues")
    graph.add_edge("fetch_issues", "understand_issues")
    graph.add_edge("understand_issues", "build_index")
    graph.add_edge("build_index", "code_context")
    graph.add_edge("code_context", "difficulty_scoring")
    graph.add_edge("difficulty_scoring", "personalized_ranking")
    graph.add_edge("personalized_ranking", "starting_point")
    graph.add_edge("starting_point", END)

    return graph.compile()


if __name__ == "__main__":
    # Manual smoke test - mirrors the exact scenario already validated
    # step-by-step across Phases 1-5.
    import os
    from dotenv import load_dotenv

    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    load_dotenv(env_path)

    skill_profile: SkillProfile = {
        "languages": ["Python"],
        "frameworks": ["LangChain", "LangGraph"],
        "experience_level": "beginner",
        "time_available": "few hours",
        "interests": ["backend", "dev tools"],
    }

    compiled_graph = build_graph("Textualize", "rich", skill_profile, max_issues=5, top_n_starting_points=3)
    final_state = compiled_graph.invoke({})

    print("Errors:", final_state["errors"])
    print("\n=== FINAL RANKED RESULTS ===")
    for e in final_state["final_ranked_list"]:
        print(f"\n#{e['issue_number']}: {e['title']} (match: {e['match_score']})")
        if e["starting_point"]:
            print("Starting point:", e["starting_point"][:200], "...")