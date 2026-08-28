import { useEffect, useRef } from "react";
import gsap from "gsap";

/**
 * A clean circular progress ring for match_score - replaces the earlier
 * compass-needle gauge now that the navigation metaphor has been dropped.
 * The stroke animates in with GSAP on mount rather than snapping to its
 * final value instantly, which reads as considerably more polished.
 */
export default function ScoreRing({ matchScore = 0, size = 56 }) {
  const circleRef = useRef(null);
  const radius = size / 2 - 4;
  const circumference = 2 * Math.PI * radius;

  const tierColor =
    matchScore >= 0.75 ? "#34D399" : matchScore >= 0.45 ? "#FBBF24" : "#F87171";

  useEffect(() => {
    const target = circumference * (1 - matchScore);
    gsap.fromTo(
      circleRef.current,
      { strokeDashoffset: circumference },
      { strokeDashoffset: target, duration: 1, ease: "power3.out", delay: 0.1 }
    );
  }, [matchScore, circumference]);

  return (
    <div
      className="relative flex-shrink-0"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Match score ${Math.round(matchScore * 100)} percent`}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#2A2A2E"
          strokeWidth="3"
        />
        <circle
          ref={circleRef}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={tierColor}
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference}
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center font-mono text-[11px] font-medium"
        style={{ color: tierColor }}
      >
        {Math.round(matchScore * 100)}
      </span>
    </div>
  );
}