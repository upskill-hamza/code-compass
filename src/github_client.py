"""
github_client.py

Handles all communication with the GitHub REST API for Issue Matchmaker.

Free-tier notes:
- Unauthenticated requests: 60 requests/hour (fine for quick tests).
- Authenticated requests (with a personal access token, no paid scopes
  needed): 5,000 requests/hour. Set the GITHUB_TOKEN environment variable
  to use one. A token is NOT required for public repos, just recommended
  once you're testing repeatedly.

To create a free token: GitHub -> Settings -> Developer settings ->
Personal access tokens -> generate one with only the `public_repo`
(read) scope checked.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

GITHUB_API_BASE = "https://api.github.com"


@dataclass
class IssueRecord:
    issue_id: int
    number: int
    title: str
    body: str
    comments: list = field(default_factory=list)
    labels: list = field(default_factory=list)
    url: str = ""
    created_at: str = ""
    updated_at: str = ""


class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.session = requests.Session()
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers.update(headers)

    def _get(self, url: str, params: Optional[dict] = None) -> requests.Response:
        resp = self.session.get(url, params=params, timeout=15)
        # Basic rate-limit courtesy: if we're close to the limit, slow down.
        remaining = resp.headers.get("X-RateLimit-Remaining")
        if remaining is not None and int(remaining) < 3:
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 5))
            wait = max(0, reset - int(time.time())) + 1
            print(f"[rate-limit] Close to limit, waiting {wait}s...")
            time.sleep(wait)
        return resp

    def fetch_open_issues(
        self, owner: str, repo: str, max_issues: int = 30, fetch_comments: bool = True
    ) -> list[IssueRecord]:
        """
        Fetches open issues for a repo, excluding pull requests (GitHub's
        issues endpoint returns both; PRs have a 'pull_request' key we
        filter out).
        """
        issues: list[IssueRecord] = []
        page = 1
        per_page = min(30, max_issues)

        while len(issues) < max_issues:
            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
            params = {
                "state": "open",
                "per_page": per_page,
                "page": page,
                "sort": "updated",
                "direction": "desc",
            }
            resp = self._get(url, params=params)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"GitHub API error {resp.status_code}: {resp.text[:300]}"
                )
            batch = resp.json()
            if not batch:
                break

            for item in batch:
                if "pull_request" in item:
                    continue  # skip PRs
                record = IssueRecord(
                    issue_id=item["id"],
                    number=item["number"],
                    title=item["title"],
                    body=item.get("body") or "",
                    labels=[lbl["name"] for lbl in item.get("labels", [])],
                    url=item["html_url"],
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                )
                if fetch_comments and item.get("comments", 0) > 0:
                    record.comments = self._fetch_comments(owner, repo, record.number)
                issues.append(record)
                if len(issues) >= max_issues:
                    break

            page += 1
            if len(batch) < per_page:
                break  # last page

        return issues

    def _fetch_comments(self, owner: str, repo: str, issue_number: int) -> list[str]:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        resp = self._get(url, params={"per_page": 20})
        if resp.status_code != 200:
            return []
        return [c["body"] for c in resp.json() if c.get("body")]


if __name__ == "__main__":
    # Quick manual smoke test
    client = GitHubClient()
    test_issues = client.fetch_open_issues("tiangolo", "typer", max_issues=5)
    for iss in test_issues:
        print(f"#{iss.number}: {iss.title} ({len(iss.comments)} comments)")
