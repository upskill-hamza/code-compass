"""
Offline tests for difficulty_scoring_node.py and personalized_ranking_node.py.

Run with: python3 src/test_phase4_ranking.py
"""

import sys
import types
from unittest.mock import MagicMock

# --- Stub pydantic and langchain_groq, same pattern as test_issue_understanding_node.py ---
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

langchain_groq_stub = types.ModuleType("langchain_groq")
langchain_groq_stub.ChatGroq = MagicMock()
sys.modules["langchain_groq"] = langchain_groq_stub

import os

os.environ["GROQ_API_KEY"] = "fake-key-for-offline-test"

import difficulty_scoring_node as diff_module  # noqa: E402
from personalized_ranking_node import personalized_ranking_node, _time_match_score, _difficulty_match_score  # noqa: E402


def make_enriched_issue(issue_number, difficulty_score=0.5, estimated_time="a weekend"):
    return {
        "issue_number": issue_number,
        "title": f"Test issue {issue_number}",
        "understanding": {
            "summary": "test summary",
            "issue_type": "bug",
            "scope_clarified_in_comments": False,
            "clarification_notes": "",
            "key_terms": ["foo"],
        },
        "likely_files": ["foo.py"],
        "code_context_summary": "- foo.py",
        "difficulty_score": difficulty_score,
        "difficulty_reasoning": "",
        "estimated_time": estimated_time,
        "match_score": 0.0,
        "match_reasoning": "",
        "starting_point": "",
    }


def test_difficulty_scoring_builds_prompt_and_parses_result():
    fake_result = types.SimpleNamespace(
        difficulty_score=0.3,
        difficulty_reasoning="Only touches one isolated file, no core abstractions involved.",
        estimated_time="few hours",
    )
    fake_llm = MagicMock()
    fake_llm.invoke.return_value = fake_result

    enriched = make_enriched_issue(1)
    result = diff_module.score_difficulty(fake_llm, enriched)

    assert result["difficulty_score"] == 0.3
    assert result["estimated_time"] == "few hours"

    call_args = fake_llm.invoke.call_args[0][0]
    user_message = call_args[1]["content"]
    assert "foo.py" in user_message, "Likely files should be included in the prompt"
    print("PASS: difficulty scoring builds correct prompt and parses result.")


def test_difficulty_scoring_node_handles_failure_with_neutral_fallback():
    fake_llm = MagicMock()
    fake_llm.invoke.side_effect = RuntimeError("simulated failure")

    diff_module._build_llm = lambda: fake_llm
    state = {"enriched_issues": [make_enriched_issue(1)], "errors": []}
    result = diff_module.difficulty_scoring_node(state)

    assert result["enriched_issues"][0]["difficulty_score"] == 0.5, "Should fall back to neutral 0.5, not 0.0"
    assert len(result["errors"]) == 1
    print("PASS: difficulty scoring node falls back gracefully on failure.")


def test_time_match_score_exact_and_mismatched():
    assert _time_match_score("few hours", "few hours") == 1.0
    assert _time_match_score("a week+", "few hours") == 0.15, "Big overshoot should score low"
    assert _time_match_score("few hours", "a week+") == 0.85, "Being quicker than budget should score fairly well"
    print("PASS: time match scoring behaves correctly for exact and mismatched cases.")


def test_difficulty_match_score_beginner_prefers_low_difficulty():
    easy_score = _difficulty_match_score(0.2, "beginner")
    hard_score = _difficulty_match_score(0.9, "beginner")
    assert easy_score > hard_score, "Beginner profile should score easy issues higher than hard ones"
    print("PASS: difficulty match scoring correctly favors easier issues for beginners.")


def test_personalized_ranking_node_sorts_correctly_for_beginner_profile():
    state = {
        "skill_profile": {
            "languages": ["Python"],
            "frameworks": [],
            "experience_level": "beginner",
            "time_available": "few hours",
            "interests": [],
        },
        "enriched_issues": [
            make_enriched_issue(1, difficulty_score=0.9, estimated_time="a week+"),  # bad fit
            make_enriched_issue(2, difficulty_score=0.25, estimated_time="few hours"),  # great fit
            make_enriched_issue(3, difficulty_score=0.5, estimated_time="a weekend"),  # mediocre fit
        ],
    }

    result = personalized_ranking_node(state)
    ranked = result["final_ranked_list"]

    assert ranked[0]["issue_number"] == 2, f"Expected issue #2 (best fit) ranked first, got {ranked[0]['issue_number']}"
    assert ranked[-1]["issue_number"] == 1, f"Expected issue #1 (worst fit) ranked last, got {ranked[-1]['issue_number']}"
    assert all(r["match_reasoning"] for r in ranked), "Every issue should have a non-empty reasoning string"
    print("PASS: personalized ranking correctly orders issues for a beginner/few-hours profile.")


if __name__ == "__main__":
    test_difficulty_scoring_builds_prompt_and_parses_result()
    test_difficulty_scoring_node_handles_failure_with_neutral_fallback()
    test_time_match_score_exact_and_mismatched()
    test_difficulty_match_score_beginner_prefers_low_difficulty()
    test_personalized_ranking_node_sorts_correctly_for_beginner_profile()
    print("\nAll offline tests passed.")