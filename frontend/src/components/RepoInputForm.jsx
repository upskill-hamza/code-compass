import { useState } from "react";

const EXPERIENCE_LEVELS = ["beginner", "intermediate", "advanced"];
const TIME_OPTIONS = ["few hours", "a weekend", "a week+"];

export default function RepoInputForm({ onSubmit, isSubmitting }) {
  const [repoOwner, setRepoOwner] = useState("Textualize");
  const [repoName, setRepoName] = useState("rich");
  const [experienceLevel, setExperienceLevel] = useState("beginner");
  const [timeAvailable, setTimeAvailable] = useState("few hours");

  function handleSubmit(e) {
    e.preventDefault();
    if (!repoOwner.trim() || !repoName.trim()) return;
    onSubmit({
      repoOwner: repoOwner.trim(),
      repoName: repoName.trim(),
      skillProfile: {
        languages: ["Python"],
        frameworks: [],
        experience_level: experienceLevel,
        time_available: timeAvailable,
        interests: [],
      },
      maxIssues: 10,
      topNStartingPoints: 3,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-xl mx-auto">
      <div className="text-center mb-10">
        <p className="font-mono text-xs tracking-[0.3em] text-chart-brass uppercase mb-3">
          Chart a course
        </p>
        <h1 className="font-display text-4xl md:text-5xl text-chart-parchment mb-3">
          Code Compass
        </h1>
        <p className="text-chart-parchmentDim text-sm max-w-sm mx-auto">
          Point it at a repository and it surveys the open issues for the ones worth your time.
        </p>
      </div>

      <div className="bg-chart-navyLight border border-white/10 rounded-lg p-6 space-y-5">
        <div className="flex gap-3">
          <div className="flex-1">
            <label htmlFor="repoOwner" className="block text-xs font-mono text-chart-parchmentDim mb-1.5">
              Repository owner
            </label>
            <input
              id="repoOwner"
              type="text"
              value={repoOwner}
              onChange={(e) => setRepoOwner(e.target.value)}
              placeholder="Textualize"
              className="w-full bg-chart-navy border border-white/10 rounded px-3 py-2 text-chart-parchment font-mono text-sm focus-visible:border-chart-brass outline-none"
              required
            />
          </div>
          <div className="flex-1">
            <label htmlFor="repoName" className="block text-xs font-mono text-chart-parchmentDim mb-1.5">
              Repository name
            </label>
            <input
              id="repoName"
              type="text"
              value={repoName}
              onChange={(e) => setRepoName(e.target.value)}
              placeholder="rich"
              className="w-full bg-chart-navy border border-white/10 rounded px-3 py-2 text-chart-parchment font-mono text-sm focus-visible:border-chart-brass outline-none"
              required
            />
          </div>
        </div>

        <div>
          <span className="block text-xs font-mono text-chart-parchmentDim mb-1.5">
            Your experience level
          </span>
          <div className="grid grid-cols-3 gap-2">
            {EXPERIENCE_LEVELS.map((level) => (
              <button
                key={level}
                type="button"
                onClick={() => setExperienceLevel(level)}
                className={`py-2 rounded text-sm capitalize border transition-colors ${
                  experienceLevel === level
                    ? "bg-chart-brass/20 border-chart-brass text-chart-brassLight"
                    : "border-white/10 text-chart-parchmentDim hover:border-white/20"
                }`}
              >
                {level}
              </button>
            ))}
          </div>
        </div>

        <div>
          <span className="block text-xs font-mono text-chart-parchmentDim mb-1.5">
            Time you have available
          </span>
          <div className="grid grid-cols-3 gap-2">
            {TIME_OPTIONS.map((time) => (
              <button
                key={time}
                type="button"
                onClick={() => setTimeAvailable(time)}
                className={`py-2 rounded text-sm capitalize border transition-colors ${
                  timeAvailable === time
                    ? "bg-chart-brass/20 border-chart-brass text-chart-brassLight"
                    : "border-white/10 text-chart-parchmentDim hover:border-white/20"
                }`}
              >
                {time}
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full bg-chart-brass hover:bg-chart-brassLight disabled:opacity-50 disabled:cursor-not-allowed text-chart-navy font-medium py-3 rounded transition-colors"
        >
          {isSubmitting ? "Charting course..." : "Find my issues"}
        </button>
      </div>
    </form>
  );
}