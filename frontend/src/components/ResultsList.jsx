import IssueCard from "./IssueCard";

export default function ResultsList({ results, errors, repoOwner, repoName, onReset }) {
  const safeResults = Array.isArray(results) ? results.filter(Boolean) : [];
  const safeErrors = Array.isArray(errors) ? errors : [];

  return (
    <div className="w-full max-w-2xl mx-auto py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <p className="font-mono text-xs tracking-[0.3em] text-chart-brass uppercase mb-2">
            Chart complete
          </p>
          <h2 className="font-display text-3xl text-chart-parchment">
            {repoOwner}/{repoName}
          </h2>
        </div>
        <button
          onClick={onReset}
          className="text-xs font-mono text-chart-parchmentDim hover:text-chart-parchment border border-white/10 hover:border-white/20 rounded px-3 py-2 transition-colors"
        >
          Chart another repo
        </button>
      </div>

      {safeErrors.length > 0 && (
        <div className="mb-6 bg-difficulty-hard/10 border border-difficulty-hard/30 rounded-lg p-4 text-sm text-chart-parchmentDim">
          <p className="font-mono text-xs text-difficulty-hard mb-1">
            {safeErrors.length} issue{safeErrors.length > 1 ? "s" : ""} couldn't be fully analyzed
          </p>
          {safeErrors.map((e, i) => (
            <p key={i} className="text-xs">{e}</p>
          ))}
        </div>
      )}

      {safeResults.length === 0 ? (
        <div className="text-center py-16 text-chart-parchmentDim">
          <p className="font-display text-xl mb-2">No open issues found</p>
          <p className="text-sm">This repo may not have any open, non-PR issues right now.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {safeResults.map((issue, i) => (
            <IssueCard key={issue.issue_number ?? i} issue={issue} rank={i + 1} />
          ))}
        </div>
      )}
    </div>
  );
}