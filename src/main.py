"""
main.py

FastAPI backend for Issue Matchmaker. Exposes 3 endpoints:

  POST /analyze          - kick off analysis for a repo, returns a job_id immediately
  GET  /status/{job_id}   - poll job status ("pending" | "running" | "done" | "error")
  GET  /results/{job_id}  - get the final ranked results once status is "done"

Run locally with:
  uvicorn main:app --reload --port 8000

The actual pipeline logic lives in graph.py (Phase 6) - this file is
intentionally thin, just HTTP plumbing + the background job wiring from
job_manager.py (which is already offline-tested with real logic).

NOTE: fastapi/starlette aren't installed in the sandbox this was built in
(same PyPI restriction that's affected every other package here), so this
file has NOT been live-tested the way every other module in this project
has been. Verify it runs correctly on your machine before treating it as
done - see the live-test instructions that accompany this file.
"""

from typing import List, Optional

import os
from dotenv import load_dotenv

# Load .env before anything else - main.py is the actual entry point when
# run via `uvicorn main:app`, so unlike the manual test scripts (which each
# called load_dotenv() themselves), nothing else in the import chain does
# this. Using the same absolute-path-safe pattern established earlier so it
# works regardless of what directory uvicorn is launched from.
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
load_dotenv(env_path)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from job_manager import job_store, PENDING, RUNNING, DONE, ERROR
from graph import build_graph

app = FastAPI(title="Issue Matchmaker API")

# Allow the React dev server (typically localhost:5173 for Vite) to call this
# API during local development. Tighten this to a specific origin before any
# real deployment - "*" is fine for local dev only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SkillProfileRequest(BaseModel):
    languages: List[str] = []
    frameworks: List[str] = []
    experience_level: str = "intermediate"  # "beginner" | "intermediate" | "advanced"
    time_available: str = "a weekend"       # "few hours" | "a weekend" | "a week+"
    interests: List[str] = []


class AnalyzeRequest(BaseModel):
    repo_owner: str
    repo_name: str
    skill_profile: SkillProfileRequest
    max_issues: int = 10
    top_n_starting_points: int = 3


class AnalyzeResponse(BaseModel):
    job_id: str


class StatusResponse(BaseModel):
    status: str  # "pending" | "running" | "done" | "error"
    error: Optional[str] = None


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    job_id = job_store.create_job()

    def run_pipeline():
        compiled_graph = build_graph(
            repo_owner=request.repo_owner,
            repo_name=request.repo_name,
            skill_profile=request.skill_profile.model_dump(),
            max_issues=request.max_issues,
            top_n_starting_points=request.top_n_starting_points,
        )
        return compiled_graph.invoke({})

    job_store.run_in_background(job_id, run_pipeline)
    return AnalyzeResponse(job_id=job_id)


@app.get("/status/{job_id}", response_model=StatusResponse)
def get_status(job_id: str):
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return StatusResponse(status=job["status"], error=job.get("error"))


@app.get("/results/{job_id}")
def get_results(job_id: str):
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] == ERROR:
        raise HTTPException(status_code=500, detail=job["error"])
    if job["status"] in (PENDING, RUNNING):
        raise HTTPException(status_code=202, detail=f"Job is still {job['status']}, not ready yet")

    # status == DONE
    final_state = job["result"]
    return {
        "errors": final_state.get("errors", []),
        "results": final_state.get("final_ranked_list", []),
    }


@app.get("/")
def root():
    return {"status": "Issue Matchmaker API is running"}