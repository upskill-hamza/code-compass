"""
job_manager.py

Manages background execution of the Code Compass pipeline (which takes
anywhere from ~30 seconds to a couple minutes - cloning a repo, building an
index, and multiple LLM calls are not instant) so the FastAPI layer can
return immediately with a job_id instead of making the HTTP request hang.

Deliberately has ZERO dependency on FastAPI - this is plain Python
(threading + a dict), which means it's fully testable offline with real
logic, unlike the FastAPI route layer in main.py which needs live testing
since fastapi/starlette aren't installed in this sandbox.

This is an in-memory job store - jobs are lost if the server restarts. Fine
for a free, single-instance portfolio project; would need a real queue
(Redis, etc.) for a production multi-instance deployment, which is out of
scope for this project's zero-budget constraint anyway.
"""

import threading
import traceback
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

# Valid job statuses
PENDING = "pending"
RUNNING = "running"
DONE = "done"
ERROR = "error"


class JobStore:
    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = {
                "status": PENDING,
                "result": None,
                "error": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        return job_id

    def get_job(self, job_id: str) -> Optional[dict]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None  # return a copy - don't leak the internal dict for mutation

    def _set_status(self, job_id: str, **updates):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(updates)

    def run_in_background(self, job_id: str, target_fn: Callable[[], dict]):
        """
        Runs target_fn() (expected to return the final pipeline state dict)
        in a background thread, updating job status as it goes. Any
        exception is caught and stored rather than crashing the thread
        silently - a silently-dead background thread would leave the job
        stuck at "running" forever with no way to diagnose why.
        """
        def _run():
            print(f"[job {job_id}] Background thread started.", flush=True)
            self._set_status(job_id, status=RUNNING)
            print(f"[job {job_id}] Status set to RUNNING, starting pipeline...", flush=True)
            try:
                result = target_fn()
                print(f"[job {job_id}] Pipeline finished successfully.", flush=True)
                self._set_status(job_id, status=DONE, result=result)
            except Exception as e:
                print(f"[job {job_id}] Pipeline failed:\n{traceback.format_exc()}", flush=True)
                self._set_status(job_id, status=ERROR, error=str(e))
        
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
# Module-level singleton - simplest possible approach for a single-instance
# free-tier deployment. main.py imports this directly.
job_store = JobStore()