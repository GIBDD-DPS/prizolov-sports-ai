// ============================================
// Copyright (c) 2026
// PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
// Author: Dm.Andreyanov
// Organization: Prizolov Market / Prizolov Lab
// ============================================

type Props = {
  home: string;
  away: string;
  league: string;
  kickoff?: string;
  prediction: string;
  confidence: "low" | "medium" | "high";
};

const CONFIDENCE_LABEL = {
  low: "Низкая",
  medium: "Средняя",
  high: "Высокая",
};

export default function EventCard({
  home,
  away,
  league,
  kickoff,
  prediction,
  confidence,
}: Props) {
  const kickoffLabel = kickoff
    ? new Date(kickoff).toLocaleString("ru-RU")
    : null;

  return (
    <div className="card">
      <div style={{ fontSize: 13, color: "var(--muted)" }}>{league}</div>
      <h3 style={{ margin: "8px 0" }}>
        {home} — {away}
      </h3>
      {kickoffLabel && (
        <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 8 }}>{kickoffLabel}</div>
      )}
      <div>
        Прогноз: <strong>{prediction}</strong>{" "}
        <span className="badge">{CONFIDENCE_LABEL[confidence]}</span>
      </div>
    </div>
  );
}
