"""
Offline tests for llm_utils.py.

time.sleep is patched to a no-op so these tests run instantly instead of
actually waiting through backoff delays - we're testing the RETRY LOGIC
(does it retry the right number of times, does it stop on non-rate-limit
errors, does it eventually give up), not real timing.

Run with: python3 src/test_llm_utils.py
"""

from unittest.mock import MagicMock, patch

from llm_utils import invoke_with_retry, RateLimitRetryExhausted, _parse_suggested_wait


def test_succeeds_immediately_when_no_error():
    llm = MagicMock()
    llm.invoke.return_value = "success"

    with patch("time.sleep"):
        result = invoke_with_retry(llm, ["msg"])

    assert result == "success"
    assert llm.invoke.call_count == 1, "Should not retry at all if the first call succeeds"
    print("PASS: succeeds immediately with no retries when there's no error.")


def test_retries_on_rate_limit_then_succeeds():
    llm = MagicMock()
    call_count = {"n": 0}

    def flaky_invoke(messages):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise RuntimeError("Error code: 429 - rate_limit_exceeded: try again in 90ms")
        return "success after retries"

    llm.invoke.side_effect = flaky_invoke

    with patch("time.sleep") as mock_sleep:
        result = invoke_with_retry(llm, ["msg"], max_retries=5)

    assert result == "success after retries"
    assert call_count["n"] == 3, f"Expected exactly 3 calls (2 failures + 1 success), got {call_count['n']}"
    assert mock_sleep.call_count == 2, "Should have slept between the 2 failed attempts"
    print("PASS: retries on rate-limit errors and succeeds once the limit clears.")


def test_does_not_retry_non_rate_limit_errors():
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("model_not_found: no such model")

    with patch("time.sleep") as mock_sleep:
        try:
            invoke_with_retry(llm, ["msg"], max_retries=5)
            assert False, "Should have raised, not returned normally"
        except RuntimeError as e:
            assert "model_not_found" in str(e)

    assert llm.invoke.call_count == 1, "Should fail fast on a real error, not retry it"
    mock_sleep.assert_not_called()
    print("PASS: real (non-rate-limit) errors fail immediately without retrying.")


def test_raises_retry_exhausted_after_max_attempts():
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("Error code: 429 - rate_limit_exceeded")

    with patch("time.sleep"):
        try:
            invoke_with_retry(llm, ["msg"], max_retries=3)
            assert False, "Should have raised RateLimitRetryExhausted"
        except RateLimitRetryExhausted as e:
            assert "3 attempts" in str(e)

    assert llm.invoke.call_count == 3, f"Expected exactly max_retries=3 calls, got {llm.invoke.call_count}"
    print("PASS: gives up and raises RateLimitRetryExhausted after max_retries attempts.")


def test_parse_suggested_wait_milliseconds():
    assert _parse_suggested_wait("...try again in 90ms...") == 0.09
    print("PASS: parses millisecond wait times correctly.")


def test_parse_suggested_wait_seconds():
    assert _parse_suggested_wait("...try again in 2.5s...") == 2.5
    print("PASS: parses second wait times correctly.")


def test_parse_suggested_wait_returns_none_when_unparseable():
    assert _parse_suggested_wait("some other error with no wait hint") is None
    print("PASS: returns None gracefully when no wait time is present in the error.")


if __name__ == "__main__":
    test_succeeds_immediately_when_no_error()
    test_retries_on_rate_limit_then_succeeds()
    test_does_not_retry_non_rate_limit_errors()
    test_raises_retry_exhausted_after_max_attempts()
    test_parse_suggested_wait_milliseconds()
    test_parse_suggested_wait_seconds()
    test_parse_suggested_wait_returns_none_when_unparseable()
    print("\nAll offline tests passed.")