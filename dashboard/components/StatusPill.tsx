const TONES: Record<string, string> = {
  ok: "border-good/40 text-good", active: "border-good/40 text-good", booked: "border-good/40 text-good", won: "border-good/40 text-good",
  failed: "border-bad/40 text-bad", lost: "border-bad/40 text-bad", unsubscribed: "border-bad/40 text-bad",
  running: "border-accent2/40 text-accent2", in_sequence: "border-accent2/40 text-accent2",
  paused: "border-warn/40 text-warn", parked: "border-warn/40 text-warn", proposed: "border-warn/40 text-warn",
  named: "border-good/40 text-good", generic: "border-warn/40 text-warn", none: "border-line text-muted",
};
export default function StatusPill({ value }: { value: string | null | undefined }) {
  const v = value ?? "–";
  return <span className={`pill ${TONES[v] ?? "border-line text-muted"}`}>{v}</span>;
}
