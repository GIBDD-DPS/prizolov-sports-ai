// ============================================
// Copyright (c) 2026
// PRIZOLOV SPORTS AI v14.14 (STORE-FRONT OPTIMIZED)
// Author: Dm.Andreyanov
// Organization: Prizolov Market / Prizolov Lab
// ============================================

type Props = {
  home: string;
  away: string;
  league: string;
  prediction: string;
  confidence: "low" | "medium" | "high";
};

const CONFIDENCE_LABEL = {
  low: "Низкая",
  medium: "Средняя",
  high: "Высокая",
};

export default function EventCard({ home, away, league, prediction, confidence }: Props) {
  return (
    <div className="card">
      <div style={{ fontSize: 13, color: "var(--muted)" }}>{league}</div>
      <h3 style={{ margin: "8px 0" }}>
        {home} — {away}
      </h3>
      <div>
        Прогноз: <strong>{prediction}</strong>{" "}
        <span className="badge">{CONFIDENCE_LABEL[confidence]}</span>
      </div>
    </div>
  );
}
