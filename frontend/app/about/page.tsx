// ============================================
// Copyright (c) 2026
// PRIZOLOV SPORTS AI v14.0 (STORE-FRONT OPTIMIZED)
// Author: Dm.Andreyanov
// Organization: Prizolov Market / Prizolov Lab
// ============================================

export default function AboutPage() {
  return (
    <main>
      <h2>О проекте</h2>
      <div className="card">
        <p>
          <strong>PRIZOLOV SPORTS AI v14.0</strong> — платформа взвешенных спортивных
          прогнозов от Dm.Andreyanov (Prizolov Market / Prizolov Lab).
        </p>
        <p>
          Источники данных: Forebet, Predictz, Betensured. Агрегация с весами
          источников и факторов.
        </p>
        <p style={{ color: "var(--muted)" }}>
          Production: prizolov-sports-dmandreyanov.amvera.io
        </p>
      </div>
      <div className="disclaimer">
        Прогнозы носят информационный характер и не являются рекомендацией к ставкам.
      </div>
    </main>
  );
}
