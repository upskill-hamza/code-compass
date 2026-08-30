"""
Offline tests for job_manager.py. Uses real threading (not mocked) since
this module has no external dependencies to stub - it's plain Python.

Run with: python3 src/test_job_manager.py
"""

import time
from job_manager import JobStore, PENDING, RUNNING, DONE, ERROR


def test_create_job_starts_as_pending():
    store = JobStore()
    job_id = store.create_job()
    job = store.get_job(job_id)
    assert job["status"] == PENDING
    assert job["result"] is None
    assert job["error"] is None
    print("PASS: new job starts in pending state.")


def test_get_job_returns_none_for_unknown_id():
    store = JobStore()
    assert store.get_job("does-not-exist") is None
    print("PASS: unknown job_id returns None instead of raising.")


def test_run_in_background_success_path():
    store = JobStore()
    job_id = store.create_job()

    def fake_pipeline():
        time.sleep(0.05)  # simulate work
        return {"final_ranked_list": [{"issue_number": 1}]}

    store.run_in_background(job_id, fake_pipeline)

    # Immediately after starting, should be pending or running, NOT done yet
    # (the whole point of background execution is not blocking the caller)
    immediate_status = store.get_job(job_id)["status"]
    assert immediate_status in (PENDING, RUNNING), f"Expected non-terminal status immediately, got {immediate_status}"

    deadline = time.time() + 3.0
    final_job = store.get_job(job_id)
    while final_job["status"] not in (DONE, ERROR) and time.time() < deadline:
        time.sleep(0.05)
        final_job = store.get_job(job_id)

    assert final_job["status"] == DONE, f"Job did not complete in time, final status: {final_job['status']}"
    assert final_job["result"]["final_ranked_list"][0]["issue_number"] == 1
    print("PASS: background job runs asynchronously and completes with correct result.")


def test_run_in_background_failure_path():
    store = JobStore()
    job_id = store.create_job()

    def failing_pipeline():
        raise RuntimeError("simulated pipeline crash")

    store.run_in_background(job_id, failing_pipeline)
    time.sleep(0.2)

    final_job = store.get_job(job_id)
    assert final_job["status"] == ERROR
    assert "simulated pipeline crash" in final_job["error"]
    print("PASS: failing background job is caught and recorded as ERROR, not silently lost.")


def test_get_job_returns_a_copy_not_a_live_reference():
    store = JobStore()
    job_id = store.create_job()
    job_copy = store.get_job(job_id)
    job_copy["status"] = "tampered"

    real_job = store.get_job(job_id)
    assert real_job["status"] == PENDING, "Mutating the returned dict should not affect internal state"
    print("PASS: get_job returns a safe copy, not a live mutable reference.")


if __name__ == "__main__":
    test_create_job_starts_as_pending()
    test_get_job_returns_none_for_unknown_id()
    test_run_in_background_success_path()
    test_run_in_background_failure_path()
    test_get_job_returns_a_copy_not_a_live_reference()
    print("\nAll offline tests passed.")