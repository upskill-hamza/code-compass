"""
personalized_ranking_node.py

Combines each issue's difficulty_score/estimated_time (from
difficulty_scoring_node) with the user's own skill_profile to produce a
match_score and a plain-language explanation of why it ranks where it does.

Deliberately NOT an LLM call - this is comparison logic against numbers and
categories the user themselves provided, so a deterministic formula is more
appropriate than spending an API call to have a model "reason" about it.
This also means the ranking is reproducible and fully explainable, which
matters for a tool whose entire pitch is "trust this ranking more than a
GitHub label".
"""

from state import GraphState

# How well each estimated_time bucket matches a given time_available
# preference. 1.0 = perfect match, lower = bigger mismatch. Being over-budget
# (issue takes longer than the user wants) is penalized more heavily than
# being under-budget (issue is quicker than the user was prepared for),
# since a beginner running out of time mid-issue is a worse experience than
# finishing early.
_TIME_ORDER = ["few hours", "a weekend", "a week+"]

def _time_match_score(estimated_time: str, time_available: str) -> float:
    if estimated_time not in _TIME_ORDER or time_available not in _TIME_ORDER:
        return 0.5  # unknown/malformed value - neutral score rather than crashing
    est_idx = _TIME_ORDER.index(estimated_time)
    avail_idx = _TIME_ORDER.index(time_available)
    diff = est_idx - avail_idx
    if diff == 0:
        return 1.0
    elif diff == 1:
        return 0.5   # issue takes one bucket longer than user wants
    elif diff <= -1:
        return 0.85  # issue is quicker than user's budget - mild bonus reduction only
    else:  # diff >= 2, issue takes much longer than user wants
        return 0.15


# Ideal difficulty_score (0-1) target per experience level - a beginner's
# "sweet spot" isn't 0.0 (trivial/boring, often a one-line typo fix with no
# learning value), it's a bit above zero.
_IDEAL_DIFFICULTY_BY_EXPERIENCE = {
    "beginner": 0.25,
    "intermediate": 0.5,
    "advanced": 0.75,
}


def _difficulty_match_score(difficulty_score: float, experience_level: str) -> float:
    ideal = _IDEAL_DIFFICULTY_BY_EXPERIENCE.get(experience_level, 0.5)
    distance = abs(difficulty_score - ideal)
    # Convert distance (0 to ~1) into a score (1.0 to 0.0), floor at 0
    return max(0.0, 1.0 - distance * 1.5)


def _build_reasoning(
    difficulty_score: float,
    estimated_time: str,
    time_score: float,
    difficulty_score_match: float,
    skill_profile: dict,
) -> str:
    parts = []

    if difficulty_score_match >= 0.8:
        parts.append(f"Difficulty ({difficulty_score:.2f}) is a strong fit for your {skill_profile['experience_level']} level")
    elif difficulty_score_match >= 0.5:
        parts.append(f"Difficulty ({difficulty_score:.2f}) is a reasonable fit for your {skill_profile['experience_level']} level")
    else:
        if difficulty_score > _IDEAL_DIFFICULTY_BY_EXPERIENCE.get(skill_profile["experience_level"], 0.5):
            parts.append(f"Difficulty ({difficulty_score:.2f}) is likely harder than ideal for your {skill_profile['experience_level']} level")
        else:
            parts.append(f"Difficulty ({difficulty_score:.2f}) is likely too simple to be a good learning fit")

    if time_score >= 0.9:
        parts.append(f"estimated time ({estimated_time}) matches your available time well")
    elif time_score >= 0.5:
        parts.append(f"estimated time ({estimated_time}) is somewhat more than your available time ({skill_profile['time_available']})")
    else:
        parts.append(f"estimated time ({estimated_time}) likely exceeds your available time ({skill_profile['time_available']})")

    return "; ".join(parts) + "."


def personalized_ranking_node(state: GraphState) -> GraphState:
    skill_profile = state["skill_profile"]

    for enriched in state["enriched_issues"]:
        difficulty_score = enriched.get("difficulty_score", 0.5)
        estimated_time = enriched.get("estimated_time", "a weekend")

        time_score = _time_match_score(estimated_time, skill_profile["time_available"])
        difficulty_match = _difficulty_match_score(difficulty_score, skill_profile["experience_level"])

        # Weighted combination: time fit matters slightly more than difficulty
        # fit for a beginner specifically, since running out of time on an
        # issue is a worse experience than an issue being a little too easy
        # or hard. This weighting could reasonably be made configurable later.
        match_score = (0.55 * time_score) + (0.45 * difficulty_match)

        enriched["match_score"] = round(match_score, 3)
        enriched["match_reasoning"] = _build_reasoning(
            difficulty_score, estimated_time, time_score, difficulty_match, skill_profile
        )

    # Sort descending by match_score - this becomes the final ranked list
    state["final_ranked_list"] = sorted(
        state["enriched_issues"], key=lambda e: e["match_score"], reverse=True
    )

    return state