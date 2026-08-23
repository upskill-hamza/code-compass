const STAGE_MESSAGES = {
  pending: "Preparing to chart the repository...",
  running: "Surveying the terrain...",
  error: "Course lost.",
  done: "Chart complete.",
};

export default function ProgressView({ status, errorMessage, onReset }) {
  const isRunning = status === "pending" || status === "running";

  return (
    <div className="w-full max-w-xl mx-auto text-center py-16">
      <div className="relative w-20 h-20 mx-auto mb-6">
        <svg viewBox="0 0 80 80" className="w-full h-full">
          <circle cx="40" cy="40" r="36" fill="none" stroke="#1B2440" strokeWidth="2" />
          <circle
            cx="40"
            cy="40"
            r="36"
            fill="none"
            stroke={status === "error" ? "#8B4A3A" : "#C08A3E"}
            strokeWidth="2"
            strokeDasharray="226"
            strokeDashoffset={isRunning ? "170" : "0"}
            strokeLinecap="round"
            className={isRunning ? "animate-spin" : ""}
            style={{
              transformOrigin: "40px 40px",
              transition: "stroke-dashoffset 0.6s ease",
              animationDuration: "2.2s",
            }}
          />
        </svg>
      </div>

      <p className="font-display text-2xl text-chart-parchment mb-2">
        {STAGE_MESSAGES[status] || "Working..."}
      </p>
      <p className="text-chart-parchmentDim text-sm mb-6">
        {isRunning
          ? "This usually takes a minute or two - cloning the repo, reading every issue, and mapping them to the code."
          : status === "error"
          ? errorMessage || "Something went wrong along the way."
          : ""}
      </p>

      {status === "error" && (
        <button
          onClick={onReset}
          className="text-xs font-mono text-chart-parchmentDim hover:text-chart-parchment border border-white/10 hover:border-white/20 rounded px-4 py-2 transition-colors"
        >
          Try a different repo
        </button>
      )}
    </div>
  );
}