import { useState, useRef, useEffect } from "react";
import RepoInputForm from "./components/RepoInputForm";
import ProgressView from "./components/ProgressView";
import ResultsList from "./components/ResultsList";
import { startAnalysis, pollStatus, getResults } from "./api";

// App moves through 3 views based on `phase`: "form" -> "progress" -> "results"
export default function App() {
  const [phase, setPhase] = useState("form");
  const [status, setStatus] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [resultsData, setResultsData] = useState(null);
  const [repoMeta, setRepoMeta] = useState({ repoOwner: "", repoName: "" });

  const stopPollingRef = useRef(null);

  useEffect(() => {
    // Cleanup: stop any in-flight polling if the component unmounts
    return () => {
      if (stopPollingRef.current) stopPollingRef.current();
    };
  }, []);

  async function handleSubmit({ repoOwner, repoName, skillProfile, maxIssues, topNStartingPoints }) {
    setPhase("progress");
    setStatus("pending");
    setErrorMessage("");
    setRepoMeta({ repoOwner, repoName });

    try {
      const jobId = await startAnalysis({ repoOwner, repoName, skillProfile, maxIssues, topNStartingPoints });

      stopPollingRef.current = pollStatus(jobId, async (statusUpdate) => {
        setStatus(statusUpdate.status);

        if (statusUpdate.status === "error") {
          setErrorMessage(statusUpdate.error || "The analysis failed.");
          return;
        }

        if (statusUpdate.status === "done") {
          try {
            const data = await getResults(jobId);
            setResultsData(data);
            setPhase("results");
          } catch (err) {
            setStatus("error");
            setErrorMessage(String(err.message || err));
          }
        }
      });
    } catch (err) {
      setStatus("error");
      setErrorMessage(String(err.message || err));
    }
  }

  function handleReset() {
    if (stopPollingRef.current) stopPollingRef.current();
    setPhase("form");
    setStatus(null);
    setErrorMessage("");
    setResultsData(null);
  }

  return (
    <div className="min-h-screen bg-ink flex items-center justify-center px-4 py-12">
      {phase === "form" && (
        <RepoInputForm onSubmit={handleSubmit} isSubmitting={false} />
      )}

      {phase === "progress" && (
        <ProgressView status={status} errorMessage={errorMessage} onReset={handleReset} />
      )}

      {phase === "results" && resultsData && (
        <ResultsList
          results={resultsData.results}
          errors={resultsData.errors}
          repoOwner={repoMeta.repoOwner}
          repoName={repoMeta.repoName}
          onReset={handleReset}
        />
      )}
    </div>
  );
}