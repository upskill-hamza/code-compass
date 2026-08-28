import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import IssueCard from "./IssueCard";

gsap.registerPlugin(ScrollTrigger);

export default function ResultsList({ results, errors, repoOwner, repoName, onReset }) {
  const safeResults = Array.isArray(results) ? results.filter(Boolean) : [];
  const safeErrors = Array.isArray(errors) ? errors : [];
  const containerRef = useRef(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(
        ".results-header",
        { opacity: 0, y: 16 },
        { opacity: 1, y: 0, duration: 0.7, ease: "power2.out" }
      );

      // Each card fades/slides in as it enters the viewport while scrolling,
      // rather than all appearing at once - this is the actual
      // scroll-triggered behavior, not just an on-load animation.
      gsap.utils.toArray(".issue-card").forEach((card, i) => {
        gsap.fromTo(
          card,
          { opacity: 0, y: 32 },
          {
            opacity: 1,
            y: 0,
            duration: 0.7,
            ease: "power3.out",
            delay: i * 0.03,
            scrollTrigger: {
              trigger: card,
              start: "top 88%",
              toggleActions: "play none none none",
            },
          }
        );
      });
    }, containerRef);

    return () => ctx.revert();
  }, [safeResults.length]);

  return (
    <div ref={containerRef} className="w-full max-w-2xl mx-auto py-16">
      <div className="results-header flex items-center justify-between mb-10">
        <div>
          <p className="font-mono text-xs tracking-[0.25em] text-accent-light uppercase mb-2">
            Analysis complete
          </p>
          <h2 className="font-sans text-3xl font-bold tracking-tightest text-text-primary">
            {repoOwner}/{repoName}
          </h2>
        </div>
        <button
          onClick={onReset}
          className="text-sm text-text-secondary hover:text-text-primary border border-ink-border hover:border-white/20 rounded-full px-4 py-2.5 transition-colors"
        >
          New search
        </button>
      </div>

      {safeErrors.length > 0 && (
        <div className="mb-6 bg-tier-hard/5 border border-tier-hard/20 rounded-xl p-4 text-sm text-text-secondary">
          <p className="font-mono text-xs text-tier-hard mb-1">
            {safeErrors.length} issue{safeErrors.length > 1 ? "s" : ""} couldn't be fully analyzed
          </p>
          {safeErrors.map((e, i) => (
            <p key={i} className="text-xs">{e}</p>
          ))}
        </div>
      )}

      {safeResults.length === 0 ? (
        <div className="text-center py-16 text-text-secondary">
          <p className="font-sans text-xl font-semibold text-text-primary mb-2">No open issues found</p>
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