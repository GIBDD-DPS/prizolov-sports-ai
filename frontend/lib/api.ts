// ============================================
// Copyright (c) 2026
// PRIZOLOV SPORTS AI v14.14 (STORE-FRONT OPTIMIZED)
// Author: Dm.Andreyanov
// Organization: Prizolov Market / Prizolov Lab
// ============================================

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "https://prizolov-sports-dmandreyanov.amvera.io/api/v1";

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function fetchEvents(sport = "football") {
  const res = await fetch(`${API_BASE}/events?sport=${sport}`, { next: { revalidate: 300 } });
  if (!res.ok) throw new Error("Events fetch failed");
  return res.json();
}

export async function fetchPredictions(sport = "football") {
  const res = await fetch(`${API_BASE}/predictions?sport=${sport}`, { next: { revalidate: 300 } });
  if (!res.ok) throw new Error("Predictions fetch failed");
  return res.json();
}
