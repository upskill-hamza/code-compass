"""
llm_utils.py

Shared helper for calling an LLM with automatic retry specifically on
Groq's rate-limit errors (HTTP 429, tokens-per-minute limits). Free-tier
Groq accounts have a fairly low TPM ceiling, and this project's pipeline
can fire 20+ LLM calls in a single run across issue_understanding_node,
difficulty_scoring_node, and starting_point_node - easy to hit the limit
even though each individual call is well within reason.

This is deliberately narrow: only rate-limit-shaped errors get retried.
Real errors (bad model name, invalid API key, malformed schema) are
re-raised immediately, matching the existing fail-fast behavior each node
already has for genuine failures.
"""

import re
import time


class RateLimitRetryExhausted(Exception):
    """Raised when every retry attempt still hit a rate limit."""
    pass


def invoke_with_retry(llm, messages, max_retries: int = 4, base_delay: float = 2.0):
    """
    Calls llm.invoke(messages), automatically retrying on rate-limit errors.

    On the first retry, tries to respect Groq's own suggested wait time
    from the error message (e.g. "try again in 90ms"). If that's not
    parseable, or on later retries, falls back to exponential backoff
    (base_delay, base_delay*2, base_delay*4, ...) since a single rate-limit
    window is unlikely to have cleared after only the suggested wait if
    we're still being hit repeatedly.
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except Exception as e:
            last_exception = e
            error_text = str(e)
            is_rate_limit = "rate_limit_exceeded" in error_text or "429" in error_text

            if not is_rate_limit:
                raise  # not a rate-limit error - fail fast, same as before

            if attempt == max_retries - 1:
                break  # about to exhaust retries, skip the sleep and fall through to raise below

            wait_seconds = _parse_suggested_wait(error_text)
            if wait_seconds is None:
                wait_seconds = base_delay * (2 ** attempt)
            time.sleep(wait_seconds)

    raise RateLimitRetryExhausted(
        f"Still rate-limited after {max_retries} attempts. Last error: {last_exception}"
    )


def _parse_suggested_wait(error_text: str):
    """Extracts a wait time from Groq's error message, e.g. 'try again in 90ms' -> 0.09"""
    match = re.search(r"try again in ([\d.]+)(ms|s)", error_text)
    if not match:
        return None
    value, unit = match.groups()
    value = float(value)
    return value / 1000 if unit == "ms" else value