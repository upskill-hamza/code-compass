"""
Offline test for github_client.py using mocked responses.
This verifies our parsing logic (PR filtering, comment fetching, pagination
stop conditions) works correctly without needing live GitHub API access.
Run with: python3 src/test_github_client.py
"""

from unittest.mock import patch, MagicMock
from github_client import GitHubClient

MOCK_ISSUES_PAGE_1 = [
    {
        "id": 1001,
        "number": 42,
        "title": "Fix crash when config file is missing",
        "body": "Steps to reproduce...",
        "labels": [{"name": "bug"}, {"name": "good first issue"}],
        "html_url": "https://github.com/fake/repo/issues/42",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-02-01T00:00:00Z",
        "comments": 2,
    },
    {
        # This one is actually a PR and should be filtered out
        "id": 1002,
        "number": 43,
        "title": "Add feature X",
        "body": "This PR adds...",
        "labels": [],
        "html_url": "https://github.com/fake/repo/pull/43",
        "created_at": "2026-01-02T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
        "comments": 0,
        "pull_request": {"url": "https://api.github.com/fake"},
    },
    {
        "id": 1003,
        "number": 44,
        "title": "Docs typo in README",
        "body": "Line 12 has a typo",
        "labels": [{"name": "documentation"}],
        "html_url": "https://github.com/fake/repo/issues/44",
        "created_at": "2026-01-03T00:00:00Z",
        "updated_at": "2026-01-03T00:00:00Z",
        "comments": 0,
    },
]

MOCK_COMMENTS = [
    {"body": "I can confirm this happens on Windows too."},
    {"body": "Looking into it, seems related to the config loader."},
]


def make_response(json_data, status=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = json_data
    mock_resp.text = str(json_data)
    mock_resp.headers = {}
    return mock_resp


def test_filters_out_pull_requests_and_fetches_comments():
    client = GitHubClient()

    def fake_get(url, params=None):
        if url.endswith("/issues"):
            return make_response(MOCK_ISSUES_PAGE_1)
        elif "/comments" in url:
            return make_response(MOCK_COMMENTS)
        raise AssertionError(f"Unexpected URL called: {url}")

    with patch.object(client, "_get", side_effect=fake_get):
        issues = client.fetch_open_issues("fake", "repo", max_issues=5)

    assert len(issues) == 2, f"Expected 2 issues (PR filtered out), got {len(issues)}"
    numbers = {i.number for i in issues}
    assert numbers == {42, 44}, f"Wrong issues returned: {numbers}"

    issue_42 = next(i for i in issues if i.number == 42)
    assert len(issue_42.comments) == 2, "Issue #42 should have fetched 2 comments"
    assert issue_42.labels == ["bug", "good first issue"]

    issue_44 = next(i for i in issues if i.number == 44)
    assert issue_44.comments == [], "Issue #44 has 0 comments, should not fetch any"

    print("PASS: PR filtering, comment fetching, and label parsing all correct.")


def test_stops_at_max_issues():
    client = GitHubClient()

    def fake_get(url, params=None):
        if url.endswith("/issues"):
            return make_response(MOCK_ISSUES_PAGE_1)
        elif "/comments" in url:
            return make_response([])
        raise AssertionError(f"Unexpected URL called: {url}")

    with patch.object(client, "_get", side_effect=fake_get):
        issues = client.fetch_open_issues("fake", "repo", max_issues=1)

    assert len(issues) == 1, f"Expected max_issues=1 to be respected, got {len(issues)}"
    print("PASS: max_issues limit respected.")


if __name__ == "__main__":
    test_filters_out_pull_requests_and_fetches_comments()
    test_stops_at_max_issues()
    print("\nAll offline tests passed.")
