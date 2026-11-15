/** Tiny SVG bar chart, no libraries. */
export default function BarChart({ points, height = 120 }: { points: { label: string; value: number }[]; height?: number }) {
  const max = Math.max(1, ...points.map((p) => p.value));
  const w = 100 / Math.max(1, points.length);
  return (
    <div>
      <svg viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" className="h-28 w-full" role="img" aria-label="leads per day">
        {points.map((p, i) => {
          const hgt = (p.value / max) * (height - 4);
          return (
            <g key={p.label}>
              <rect x={i * w + w * 0.15} y={height - hgt} width={w * 0.7} height={hgt} rx={0.6}
                fill={p.value ? "#5eead4" : "#1c2533"} opacity={p.value ? 0.85 : 1}>
                <title>{`${p.label}: ${p.value}`}</title>
              </rect>
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex justify-between text-[10px] text-muted">
        <span>{points[0]?.label}</span><span>{points[Math.floor(points.length / 2)]?.label}</span><span>{points.at(-1)?.label}</span>
      </div>
    </div>
  );
}
