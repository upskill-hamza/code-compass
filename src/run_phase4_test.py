import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
load_dotenv(env_path)

from github_client import GitHubClient
from issue_understanding_node import issue_understanding_node
from repo_indexer import build_repo_index
from code_context_node import code_context_node
from difficulty_scoring_node import difficulty_scoring_node
from personalized_ranking_node import personalized_ranking_node

skill_profile = {
    "languages": ["Python"],
    "frameworks": ["LangChain", "LangGraph"],
    "experience_level": "beginner",
    "time_available": "few hours",
    "interests": ["backend", "dev tools"],
}

client = GitHubClient()
issues = client.fetch_open_issues("Textualize", "rich", max_issues=5)
state = {"raw_issues": [i.__dict__ for i in issues], "errors": [], "skill_profile": skill_profile}

state = issue_understanding_node(state)
index = build_repo_index("Textualize", "rich")
state = code_context_node(state, index)
state = difficulty_scoring_node(state)
state = personalized_ranking_node(state)

print("All errors:", state["errors"])
print("\n=== RANKED RESULTS ===")
for e in state["final_ranked_list"]:
    print(f"\n#{e['issue_number']}: {e['title']}")
    print(f"  Match score: {e['match_score']}")
    print(f"  Difficulty: {e['difficulty_score']} ({e['estimated_time']})")
    print(f"  Why: {e['difficulty_reasoning']}")
    print(f"  Match reasoning: {e['match_reasoning']}")