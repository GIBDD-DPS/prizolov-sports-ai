// ============================================
// Copyright (c) 2026
// PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
// Author: Dm.Andreyanov
// Organization: Prizolov Market / Prizolov Lab
// ============================================

const DEFAULT_API =
  process.env.NEXT_PUBLIC_API_URL ?? "https://sport-ai-dmandreyanov.amvera.io/api/v1";

const FETCH_TIMEOUT_MS = 15000;
const MAX_RETRIES = 2;

export type ApiList<T> = {
  count: number;
  items: T[];
};

export type EventItem = {
  id: number;
  home_team: string;
  away_team: string;
  league: string;
  kickoff_at: string;
  status: string;
  sport_slug: string;
};

export type PredictionItem = {
  id: number;
  event_id: number;
  market_type: string;
  selection: string;
  probability: number;
  confidence: string;
  factors?: Record<string, unknown> | null;
};

async function fetchWithRetry<T>(url: string): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
      const res = await fetch(url, {
        signal: controller.signal,
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      clearTimeout(timer);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return (await res.json()) as T;
    } catch (err) {
      lastError = err;
      if (attempt < MAX_RETRIES) {
        await new Promise((r) => setTimeout(r, 800 * (attempt + 1)));
      }
    }
  }
  throw lastError;
}

export function getApiBase(): string {
  return DEFAULT_API.replace(/\/$/, "");
}

export async function fetchHealth() {
  return fetchWithRetry<Record<string, unknown>>(`${getApiBase()}/health`);
}

export async function fetchEvents(sport = "football", limit = 20) {
  return fetchWithRetry<ApiList<EventItem>>(
    `${getApiBase()}/events?sport=${sport}&limit=${limit}`
  );
}

export async function fetchPredictions(sport = "football", limit = 50) {
  return fetchWithRetry<ApiList<PredictionItem>>(
    `${getApiBase()}/predictions?sport=${sport}&limit=${limit}`
  );
}
