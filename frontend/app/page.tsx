// ============================================
// Copyright (c) 2026
// PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
// Author: Dm.Andreyanov
// Organization: Prizolov Market / Prizolov Lab
// ============================================

import Storefront from "@/components/Storefront";

export default function HomePage() {
  return (
    <main>
      <h2>Ближайшие события</h2>
      <p style={{ color: "var(--muted)" }}>
        Публичная витрина взвешенных прогнозов. MVP: футбол.
      </p>
      <Storefront sport="football" />
    </main>
  );
}
