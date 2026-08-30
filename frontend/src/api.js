const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function startAnalysis({ repoOwner, repoName, skillProfile, maxIssues, topNStartingPoints }) {
  const response = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      repo_owner: repoOwner,
      repo_name: repoName,
      skill_profile: skillProfile,
      max_issues: maxIssues,
      top_n_starting_points: topNStartingPoints,
    }),
  });
  if (!response.ok) {
    throw new Error(`Failed to start analysis (${response.status})`);
  }
  const data = await response.json();
  return data.job_id;
}

export async function getStatus(jobId) {
  const response = await fetch(`${API_BASE}/status/${jobId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch status (${response.status})`);
  }
  return response.json(); // { status, error }
}

export async function getResults(jobId) {
  const response = await fetch(`${API_BASE}/results/${jobId}`);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Failed to fetch results (${response.status})`);
  }
  return response.json(); // { errors, results }
}

// Polls /status every intervalMs until status is "done" or "error", calling
// onUpdate with each status response along the way. Returns a cleanup
// function to stop polling (important for React StrictMode's double-mount
// in dev, and for unmounting mid-poll).
export function pollStatus(jobId, onUpdate, intervalMs = 3000) {
  let cancelled = false;

  async function tick() {
    if (cancelled) return;
    try {
      const status = await getStatus(jobId);
      if (cancelled) return;
      onUpdate(status);
      if (status.status === "done" || status.status === "error") {
        return; // stop polling - terminal state reached
      }
    } catch (err) {
      if (cancelled) return;
      onUpdate({ status: "error", error: String(err) });
      return;
    }
    setTimeout(tick, intervalMs);
  }

  tick();

  return () => {
    cancelled = true;
  };
}