from dotenv import load_dotenv
load_dotenv("../.env")

from github_client import GitHubClient
from issue_understanding_node import issue_understanding_node
from repo_indexer import build_repo_index
from code_context_node import code_context_node

# Phase 1: fetch issues
client = GitHubClient()
issues = client.fetch_open_issues("Textualize", "rich", max_issues=5)
print(f"Fetched {len(issues)} real (non-PR) issues")
state = {"raw_issues": [i.__dict__ for i in issues], "errors": []}

# Phase 2: understand issues
state = issue_understanding_node(state)
print("Phase 2 done. Enriched:", len(state["enriched_issues"]), "Errors:", state["errors"])

# Phase 3: build the code index (embedding model is already cached now, should be fast)
print("\nBuilding repo index...")
index = build_repo_index("Textualize", "rich")
print("Index built successfully")

# Phase 3: find relevant code for each issue
state = code_context_node(state, index)
print("\nErrors after code context:", state["errors"])

for e in state["enriched_issues"]:
    print(f"\n#{e['issue_number']}: {e['title']}")
    print("Summary:", e["understanding"]["summary"])
    print("Likely files:", e["likely_files"])