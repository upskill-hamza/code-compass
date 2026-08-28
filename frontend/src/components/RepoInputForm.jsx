import { useState, useEffect, useRef } from "react";
import gsap from "gsap";

const EXPERIENCE_LEVELS = ["beginner", "intermediate", "advanced"];
const TIME_OPTIONS = ["few hours", "a weekend", "a week+"];

export default function RepoInputForm({ onSubmit, isSubmitting }) {
  const [repoOwner, setRepoOwner] = useState("Textualize");
  const [repoName, setRepoName] = useState("rich");
  const [experienceLevel, setExperienceLevel] = useState("beginner");
  const [timeAvailable, setTimeAvailable] = useState("few hours");

  const heroRef = useRef(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(
        ".hero-reveal",
        { opacity: 0, y: 24 },
        { opacity: 1, y: 0, duration: 0.9, ease: "power3.out", stagger: 0.08 }
      );
    }, heroRef);
    return () => ctx.revert();
  }, []);

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

  function PillGroup({ options, value, onChange }) {
    return (
      <div className="inline-flex bg-ink-surface border border-ink-border rounded-full p-1">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            className={`px-4 py-2 rounded-full text-sm capitalize transition-all duration-200 ${
              value === opt
                ? "bg-accent text-white shadow-lg shadow-accent/20"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            {opt}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div ref={heroRef} className="w-full max-w-2xl mx-auto text-center">
      <p className="hero-reveal font-mono text-xs tracking-[0.25em] text-accent-light uppercase mb-5">
        Open source, matched to you
      </p>
      <h1 className="hero-reveal font-sans text-5xl md:text-6xl font-bold tracking-tightest text-text-primary mb-5 leading-[1.05]">
        Find the issue
        <br />
        you can actually finish.
      </h1>
      <p className="hero-reveal text-text-secondary text-lg max-w-md mx-auto mb-12 leading-relaxed">
        Code Compass reads every open issue, the discussion around it, and the code it touches — then ranks what's realistic for you.
      </p>

      <form onSubmit={handleSubmit} className="hero-reveal">
        <div className="flex flex-col sm:flex-row gap-2 max-w-lg mx-auto mb-6">
          <input
            type="text"
            value={repoOwner}
            onChange={(e) => setRepoOwner(e.target.value)}
            placeholder="owner"
            aria-label="Repository owner"
            className="flex-1 bg-ink-surface border border-ink-border rounded-xl px-4 py-3.5 text-text-primary text-center sm:text-left placeholder:text-text-tertiary focus-visible:border-accent outline-none transition-colors"
            required
          />
          <input
            type="text"
            value={repoName}
            onChange={(e) => setRepoName(e.target.value)}
            placeholder="repo"
            aria-label="Repository name"
            className="flex-1 bg-ink-surface border border-ink-border rounded-xl px-4 py-3.5 text-text-primary text-center sm:text-left placeholder:text-text-tertiary focus-visible:border-accent outline-none transition-colors"
            required
          />
        </div>

        <div className="flex flex-col items-center gap-4 mb-10">
          <PillGroup options={EXPERIENCE_LEVELS} value={experienceLevel} onChange={setExperienceLevel} />
          <PillGroup options={TIME_OPTIONS} value={timeAvailable} onChange={setTimeAvailable} />
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="bg-text-primary hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed text-ink font-semibold px-8 py-4 rounded-full transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
        >
          {isSubmitting ? "Analyzing..." : "Find my issues"}
        </button>
      </form>
    </div>
  );
}