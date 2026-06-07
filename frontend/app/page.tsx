// ============================================
// Copyright (c) 2026
// PRIZOLOV SPORTS AI v14.0 (STORE-FRONT OPTIMIZED)
// Author: Dm.Andreyanov
// Organization: Prizolov Market / Prizolov Lab
// ============================================

import EventCard from "@/components/EventCard";

export default function HomePage() {
  return (
    <main>
      <h2>Ближайшие события</h2>
      <p style={{ color: "var(--muted)" }}>
        Публичная витрина взвешенных прогнозов. MVP: футбол.
      </p>
      <div className="disclaimer">
        Прогнозы носят информационный характер и не являются рекомендацией к ставкам.
      </div>
      <EventCard
        home="—"
        away="—"
        league="Данные появятся после Шага 5 (парсер Forebet)"
        prediction="Ожидание"
        confidence="medium"
      />
    </main>
  );
}
