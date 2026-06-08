// ============================================
// Copyright (c) 2026
// PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
// Author: Dm.Andreyanov
// Organization: Prizolov Market / Prizolov Lab
// ============================================

type Props = { params: { id: string } };

export default function EventPage({ params }: Props) {
  return (
    <main>
      <h2>Событие #{params.id}</h2>
      <div className="card">
        <p>Детальная карточка матча — Step 7.</p>
        <p style={{ color: "var(--muted)" }}>
          Рынки: П1/X/П2, тоталы, ЖК, угловые с взвешенными прогнозами.
        </p>
      </div>
    </main>
  );
}
