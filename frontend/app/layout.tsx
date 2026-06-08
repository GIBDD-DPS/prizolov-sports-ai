// ============================================
// Copyright (c) 2026
// PRIZOLOV SPORTS AI v14.14 (STORE-FRONT OPTIMIZED)
// Author: Dm.Andreyanov
// Organization: Prizolov Market / Prizolov Lab
// ============================================

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PRIZOLOV SPORTS AI v14.0",
  description: "Взвешенные спортивные прогнозы — Prizolov Market / Prizolov Lab",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <div className="container">
          <header>
            <h1>
              <a href="/">PRIZOLOV SPORTS AI</a>{" "}
              <span className="badge">v14.0</span>
            </h1>
            <nav>
              <a href="/sport/football/">Футбол</a>
              {" · "}
              <a href="/about/">О проекте</a>
            </nav>
          </header>
          {children}
          <footer>
            © 2026 Dm.Andreyanov — Prizolov Market / Prizolov Lab. Все права защищены.
          </footer>
        </div>
      </body>
    </html>
  );
}
