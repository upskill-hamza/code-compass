/**
 * CompassGauge - the signature element of Code Compass.
 *
 * Renders match_score (0-1) as a compass needle bearing rather than a
 * generic percentage bar. North (top, 0deg) = perfect match. The needle
 * sweeps toward a bearing proportional to how far the match falls short of
 * 1.0, so a strong match reads as "true north" - a real match to the
 * navigation metaphor, not just a stylistic wrapper around a number.
 */
export default function CompassGauge({ matchScore = 0, size = 64 }) {
  // Sweep up to +/-70deg off north as match_score drops from 1.0 to 0.0.
  // Alternating left/right by score tier keeps low scores visually distinct
  // rather than all pointing the same "wrong" direction.
  const maxSweepDeg = 70;
  const deviation = (1 - matchScore) * maxSweepDeg;
  const direction = matchScore >= 0.5 ? 1 : -1;
  const needleRotation = deviation * direction;

  const tierColor =
    matchScore >= 0.75 ? "#5B7A5C" : matchScore >= 0.45 ? "#C08A3E" : "#8B4A3A";

  const center = size / 2;
  const radius = size / 2 - 4;

  return (
    <div className="flex flex-col items-center gap-1" role="img" aria-label={`Compass bearing, match score ${Math.round(matchScore * 100)} percent`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="#1B2440"
          stroke="#3A4260"
          strokeWidth="1.5"
        />
        {/* Tick marks at N/E/S/W */}
        {[0, 90, 180, 270].map((deg) => (
          <line
            key={deg}
            x1={center}
            y1={center - radius + 3}
            x2={center}
            y2={center - radius + 7}
            stroke="#B9B2A0"
            strokeWidth="1"
            transform={`rotate(${deg} ${center} ${center})`}
          />
        ))}
        {/* Needle */}
        <g transform={`rotate(${needleRotation} ${center} ${center})`} style={{ transition: "transform 0.6s ease-out" }}>
          <line
            x1={center}
            y1={center}
            x2={center}
            y2={center - radius + 6}
            stroke={tierColor}
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          <line
            x1={center}
            y1={center}
            x2={center}
            y2={center + radius - 12}
            stroke="#6B7288"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </g>
        <circle cx={center} cy={center} r="3" fill="#EDE6D6" />
      </svg>
      <span className="font-mono text-xs" style={{ color: tierColor }}>
        {Math.round(matchScore * 100)}%
      </span>
    </div>
  );
}