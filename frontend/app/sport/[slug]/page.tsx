// ============================================
// Copyright (c) 2026
// PRIZOLOV SPORTS AI v14.14 (STORE-FRONT OPTIMIZED)
// Author: Dm.Andreyanov
// Organization: Prizolov Market / Prizolov Lab
// ============================================

type Props = { params: { slug: string } };

const SPORT_NAMES: Record<string, string> = {
  football: "Футбол",
  hockey: "Хоккей",
  basketball: "Баскетбол",
};

export default function SportPage({ params }: Props) {
  const name = SPORT_NAMES[params.slug] ?? params.slug;
  const active = params.slug === "football";

  return (
    <main>
      <h2>{name}</h2>
      {!active && (
        <p style={{ color: "var(--muted)" }}>
          Раздел в разработке. Сейчас активен только футбол.
        </p>
      )}
      {active && (
        <p style={{ color: "var(--muted)" }}>
          Линии: П1 / X / П2, тоталы, ЖК, угловые.
        </p>
      )}
    </main>
  );
}
