"""
Offline test for issue_understanding_node.py.

This sandbox can't reach PyPI right now, so real pydantic/langchain_groq
aren't installed here. We stub the minimum surface of both libraries so we
can still exercise OUR logic (prompt construction, comment formatting,
state merging) - the part actually worth catching bugs in before you run
this for real with your Groq key.

On your machine, with the real packages installed, this same
issue_understanding_node.py will work unmodified against the real Groq API.

Run with: python3 src/test_issue_understanding_node.py
"""

import sys
import types
from unittest.mock import MagicMock


# --- Stub pydantic (minimal BaseModel + Field so the schema class is importable) ---
pydantic_stub = types.ModuleType("pydantic")


class _FakeBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _fake_field(*args, **kwargs):
    return None


pydantic_stub.BaseModel = _FakeBaseModel
pydantic_stub.Field = _fake_field
sys.modules["pydantic"] = pydantic_stub

# --- Stub langchain_groq (we only need ChatGroq to be constructible/mockable) ---
langchain_groq_stub = types.ModuleType("langchain_groq")
langchain_groq_stub.ChatGroq = MagicMock()
sys.modules["langchain_groq"] = langchain_groq_stub

import os

os.environ["GROQ_API_KEY"] = "fake-key-for-offline-test"

import issue_understanding_node as node_module  # noqa: E402


def test_understand_issue_builds_correct_prompt_and_parses_result():
    fake_result = types.SimpleNamespace(
        summary="Config loader crashes when the file is absent instead of using defaults.",
        issue_type="bug",
        scope_clarified_in_comments=True,
        clarification_notes="A commenter noted it should fall back to defaults, not just avoid crashing.",
        key_terms=["config_loader.py", "load_config", "FileNotFoundError"],
    )

    fake_structured_llm = MagicMock()
    fake_structured_llm.invoke.return_value = fake_result

    issue = {
        "number": 42,
        "title": "Fix crash when config file is missing",
        "body": "App crashes with FileNotFoundError instead of using defaults.",
        "labels": ["bug", "good first issue"],
        "comments": [
            "I can reproduce this on Linux too.",
            "It should fall back to defaults, not just avoid crashing - that's the real fix needed.",
        ],
    }

    result = node_module.understand_issue(fake_structured_llm, issue)

    # Verify the prompt sent to the LLM actually included the comments
    # (this is the whole point of the node - catching scope drift in comments)
    call_args = fake_structured_llm.invoke.call_args[0][0]
    user_message = call_args[1]["content"]
    assert "fall back to defaults" in user_message, "Comment content missing from prompt!"
    assert "Fix crash when config file is missing" in user_message, "Issue title missing from prompt!"

    # Verify the structured result was correctly translated into our IssueUnderstanding dict
    assert result["issue_type"] == "bug"
    assert result["scope_clarified_in_comments"] is True
    assert "config_loader.py" in result["key_terms"]

    print("PASS: prompt correctly includes comments, result correctly parsed.")


def test_node_handles_partial_failure_gracefully():
    """If one issue fails LLM analysis, the node should record the error
    and continue processing other issues, not crash the whole pipeline."""

    good_result = types.SimpleNamespace(
        summary="Typo in README line 12.",
        issue_type="docs",
        scope_clarified_in_comments=False,
        clarification_notes="",
        key_terms=["README.md"],
    )

    call_count = {"n": 0}

    def flaky_invoke(messages):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated API timeout")
        return good_result

    fake_structured_llm = MagicMock()
    fake_structured_llm.invoke.side_effect = flaky_invoke

    state = {
        "raw_issues": [
            {"number": 1, "title": "Broken issue", "body": "x", "labels": [], "comments": [], "url": "https://github.com/fake/repo/issues/1"},
            {"number": 2, "title": "Docs typo", "body": "y", "labels": [], "comments": [], "url": "https://github.com/fake/repo/issues/2"},
        ],
        "errors": [],
    }

    # Patch _build_llm to return our fake instead of hitting the real API
    original_build_llm = node_module._build_llm
    node_module._build_llm = lambda: fake_structured_llm
    try:
        result_state = node_module.issue_understanding_node(state)
    finally:
        node_module._build_llm = original_build_llm

    assert len(result_state["enriched_issues"]) == 1, "Should have 1 successful issue, not crashed on the failed one"
    assert result_state["enriched_issues"][0]["issue_number"] == 2
    assert len(result_state["errors"]) == 1, "Failure should be recorded in errors"
    assert "Issue #1" in result_state["errors"][0]

    print("PASS: partial failure handled gracefully, pipeline continues.")


if __name__ == "__main__":
    test_understand_issue_builds_correct_prompt_and_parses_result()
    test_node_handles_partial_failure_gracefully()
    print("\nAll offline tests passed.")
