"""
Offline tests for starting_point_node.py and GitHubClient.search_merged_prs.

Run with: python3 src/test_starting_point_node.py
"""

import sys
import types
from unittest.mock import MagicMock, patch

langchain_groq_stub = types.ModuleType("langchain_groq")
langchain_groq_stub.ChatGroq = MagicMock()
sys.modules["langchain_groq"] = langchain_groq_stub

import os

os.environ["GROQ_API_KEY"] = "fake-key-for-offline-test"

from github_client import GitHubClient  # noqa: E402
import starting_point_node as sp_module  # noqa: E402


def make_response(json_data, status=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = json_data
    mock_resp.headers = {}
    return mock_resp


def test_search_merged_prs_builds_correct_query_and_parses_results():
    client = GitHubClient()

    mock_search_response = {
        "items": [
            {"title": "Fix cache invalidation bug", "html_url": "https://github.com/fake/repo/pull/100", "number": 100},
            {"title": "Improve cache invalidation logic", "html_url": "https://github.com/fake/repo/pull/95", "number": 95},
        ]
    }

    captured_params = {}

    def fake_get(url, params=None):
        captured_params.update(params or {})
        return make_response(mock_search_response)

    with patch.object(client, "_get", side_effect=fake_get):
        results = client.search_merged_prs("fake", "repo", ["cache_manager.py", "invalidate_cache"], max_results=3)

    assert "repo:fake/repo" in captured_params["q"]
    assert "type:pr" in captured_params["q"]
    assert "is:merged" in captured_params["q"]
    assert len(results) == 2
    assert results[0]["number"] == 100

    print("PASS: search_merged_prs builds correct query and parses results.")


def test_search_merged_prs_returns_empty_on_no_keywords():
    client = GitHubClient()
    # Should not even make a network call if there are no keywords
    with patch.object(client, "_get") as mock_get:
        results = client.search_merged_prs("fake", "repo", [], max_results=3)
    assert results == []
    mock_get.assert_not_called()
    print("PASS: search_merged_prs skips the network call when keywords are empty.")


def test_search_merged_prs_fails_gracefully_on_api_error():
    client = GitHubClient()
    with patch.object(client, "_get", return_value=make_response({}, status=403)):
        results = client.search_merged_prs("fake", "repo", ["foo"], max_results=3)
    assert results == [], "Should return empty list, not raise, on search API failure"
    print("PASS: search_merged_prs fails gracefully (empty list) on API error.")


def make_enriched_issue(issue_number, match_score):
    return {
        "issue_number": issue_number,
        "title": f"Issue {issue_number}",
        "understanding": {
            "summary": "test",
            "issue_type": "bug",
            "scope_clarified_in_comments": False,
            "clarification_notes": "",
            "key_terms": ["foo.py"],
        },
        "likely_files": ["foo.py"],
        "code_context_summary": "- foo.py",
        "difficulty_score": 0.3,
        "difficulty_reasoning": "",
        "estimated_time": "few hours",
        "match_score": match_score,
        "match_reasoning": "",
        "starting_point": "",
    }


def test_starting_point_node_only_processes_top_n():
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = types.SimpleNamespace(content="Look at foo.py's bar() function first.")
    sp_module._build_llm = lambda: fake_llm

    fake_github_client = MagicMock()
    fake_github_client.search_merged_prs.return_value = []

    state = {
        "final_ranked_list": [
            make_enriched_issue(1, 0.9),
            make_enriched_issue(2, 0.8),
            make_enriched_issue(3, 0.5),
            make_enriched_issue(4, 0.2),  # should NOT get a starting point (top_n=3)
        ],
        "errors": [],
    }

    result = sp_module.starting_point_node(state, fake_github_client, "fake", "repo", top_n=3)

    processed = [e for e in result["final_ranked_list"] if e["starting_point"]]
    assert len(processed) == 3, f"Expected exactly 3 issues processed, got {len(processed)}"
    assert result["final_ranked_list"][3]["starting_point"] == "", "4th-ranked issue should be untouched"
    print("PASS: starting_point_node only processes the top N issues.")


def test_starting_point_node_handles_failure_gracefully():
    fake_llm = MagicMock()
    fake_llm.invoke.side_effect = RuntimeError("simulated failure")
    sp_module._build_llm = lambda: fake_llm

    fake_github_client = MagicMock()
    fake_github_client.search_merged_prs.return_value = []

    state = {"final_ranked_list": [make_enriched_issue(1, 0.9)], "errors": []}
    result = sp_module.starting_point_node(state, fake_github_client, "fake", "repo", top_n=3)

    assert result["final_ranked_list"][0]["starting_point"] == ""
    assert len(result["errors"]) == 1
    print("PASS: starting_point_node handles LLM failure gracefully.")


if __name__ == "__main__":
    test_search_merged_prs_builds_correct_query_and_parses_results()
    test_search_merged_prs_returns_empty_on_no_keywords()
    test_search_merged_prs_fails_gracefully_on_api_error()
    test_starting_point_node_only_processes_top_n()
    test_starting_point_node_handles_failure_gracefully()
    print("\nAll offline tests passed.")