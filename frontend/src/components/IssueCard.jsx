import CompassGauge from "./CompassGauge";

const DIFFICULTY_LABEL = (score) => {
  if (score < 0.35) return { label: "Easy terrain", color: "#5B7A5C" };
  if (score < 0.6) return { label: "Moderate terrain", color: "#C08A3E" };
  return { label: "Rough terrain", color: "#8B4A3A" };
};

export default function IssueCard({ issue, rank }) {
  if (!issue) return null; // defensive: skip rendering if a malformed/missing entry slips through

  const difficulty = DIFFICULTY_LABEL(issue.difficulty_score ?? 0.5);

  return (
    <div className="bg-chart-navyLight border border-white/10 rounded-lg p-5 flex gap-5">
      <div className="flex-shrink-0 flex flex-col items-center gap-2 pt-1">
        <span className="font-mono text-xs text-chart-parchmentDim">#{rank}</span>
        <CompassGauge matchScore={issue.match_score} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-3 mb-1">
          <a
            href={issue.url}
            target="_blank"
            rel="noreferrer"
            className="font-display text-lg text-chart-parchment hover:text-chart-brassLight transition-colors leading-snug"
          >
            {issue.title}
          </a>
        </div>

        <div className="flex items-center gap-3 mb-3 text-xs font-mono">
          <span style={{ color: difficulty.color }}>{difficulty.label}</span>
          <span className="text-chart-parchmentDim">·</span>
          <span className="text-chart-parchmentDim">{issue.estimated_time}</span>
          <span className="text-chart-parchmentDim">·</span>
          <span className="text-chart-parchmentDim">issue #{issue.issue_number}</span>
        </div>

        <p className="text-sm text-chart-parchmentDim mb-3 leading-relaxed">
          {issue.understanding?.summary}
        </p>

        {issue.likely_files?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {issue.likely_files.map((f) => (
              <span
                key={f}
                className="font-mono text-[11px] bg-chart-navy border border-white/10 text-chart-parchmentDim px-2 py-0.5 rounded"
              >
                {f}
              </span>
            ))}
          </div>
        )}

        {issue.starting_point && (
          <details className="mt-2 group">
            <summary className="cursor-pointer text-xs font-mono text-chart-brass hover:text-chart-brassLight list-none flex items-center gap-1.5">
              <span className="inline-block transition-transform group-open:rotate-90">▸</span>
              Starting point
            </summary>
            <div className="mt-2 bg-chart-navy border border-white/10 rounded p-3 text-sm text-chart-parchmentDim leading-relaxed whitespace-pre-line">
              {issue.starting_point}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}