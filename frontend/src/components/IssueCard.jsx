import ScoreRing from "./ScoreRing";

const DIFFICULTY_LABEL = (score) => {
  if (score < 0.35) return { label: "Easy", color: "#34D399" };
  if (score < 0.6) return { label: "Moderate", color: "#FBBF24" };
  return { label: "Hard", color: "#F87171" };
};

export default function IssueCard({ issue, rank }) {
  if (!issue) return null;

  const difficulty = DIFFICULTY_LABEL(issue.difficulty_score ?? 0.5);

  return (
    <div className="issue-card bg-ink-surface border border-ink-border rounded-2xl p-6 flex gap-5 transition-all duration-300 hover:border-white/20 hover:-translate-y-0.5">
      <div className="flex-shrink-0 flex flex-col items-center gap-2 pt-1">
        <span className="font-mono text-xs text-text-tertiary">{String(rank).padStart(2, "0")}</span>
        <ScoreRing matchScore={issue.match_score} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-3 mb-2">
          <a
            href={issue.url}
            target="_blank"
            rel="noreferrer"
            className="font-sans text-lg font-semibold text-text-primary hover:text-accent-light transition-colors leading-snug tracking-tight"
          >
            {issue.title}
          </a>
        </div>

        <div className="flex items-center gap-2.5 mb-3 text-xs font-mono">
          <span
            className="px-2 py-0.5 rounded-full text-[11px] font-medium"
            style={{ color: difficulty.color, backgroundColor: `${difficulty.color}1A` }}
          >
            {difficulty.label}
          </span>
          <span className="text-text-tertiary">{issue.estimated_time}</span>
          <span className="text-text-tertiary">·</span>
          <span className="text-text-tertiary">#{issue.issue_number}</span>
        </div>

        <p className="text-sm text-text-secondary mb-4 leading-relaxed">
          {issue.understanding?.summary}
        </p>

        {issue.likely_files?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {issue.likely_files.map((f) => (
              <span
                key={f}
                className="font-mono text-[11px] bg-ink border border-ink-border text-text-secondary px-2 py-1 rounded-md"
              >
                {f}
              </span>
            ))}
          </div>
        )}

        {issue.starting_point && (
          <details className="group">
            <summary className="cursor-pointer text-xs font-medium text-accent-light hover:text-accent list-none flex items-center gap-1.5">
              <span className="inline-block transition-transform duration-200 group-open:rotate-90">›</span>
              Starting point
            </summary>
            <div className="mt-3 bg-ink border border-ink-border rounded-xl p-4 text-sm text-text-secondary leading-relaxed whitespace-pre-line">
              {issue.starting_point}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}