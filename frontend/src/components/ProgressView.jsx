import { useEffect, useRef } from "react";
import gsap from "gsap";

const STAGE_MESSAGES = {
  pending: "Getting started...",
  running: "Reading every issue, mapping the code...",
  error: "Something went wrong.",
  done: "Done.",
};

export default function ProgressView({ status, errorMessage, onReset }) {
  const isRunning = status === "pending" || status === "running";
  const containerRef = useRef(null);

  useEffect(() => {
    gsap.fromTo(
      containerRef.current,
      { opacity: 0, y: 12 },
      { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" }
    );
  }, []);

  return (
    <div ref={containerRef} className="w-full max-w-md mx-auto text-center py-20">
      <div className="relative w-12 h-12 mx-auto mb-8">
        <div
          className={`absolute inset-0 rounded-full border-2 ${
            status === "error" ? "border-tier-hard" : "border-ink-border"
          }`}
        />
        {isRunning && (
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-accent animate-spin" />
        )}
      </div>

      <p className="font-sans text-2xl font-semibold tracking-tightest text-text-primary mb-2">
        {STAGE_MESSAGES[status] || "Working..."}
      </p>
      <p className="text-text-secondary text-sm mb-8">
        {isRunning
          ? "This usually takes a minute or two."
          : status === "error"
          ? errorMessage || "The analysis couldn't be completed."
          : ""}
      </p>

      {status === "error" && (
        <button
          onClick={onReset}
          className="text-sm text-text-secondary hover:text-text-primary border border-ink-border hover:border-white/20 rounded-full px-5 py-2.5 transition-colors"
        >
          Try a different repo
        </button>
      )}
    </div>
  );
}