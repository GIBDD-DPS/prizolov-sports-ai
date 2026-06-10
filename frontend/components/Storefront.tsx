"use client";

// ============================================
// Copyright (c) 2026
// PRIZOLOV SPORTS AI v14.38 (STORE-FRONT OPTIMIZED)
// Author: Dm.Andreyanov
// Organization: Prizolov Market / Prizolov Lab
// ============================================

import { useCallback, useEffect, useState } from "react";

import EventCard from "@/components/EventCard";
import {
  EventItem,
  PredictionItem,
  fetchEvents,
  fetchHealth,
  fetchPredictions,
  getApiBase,
} from "@/lib/api";

const SEL_LABEL: Record<string, string> = { "1": "П1", X: "X", "2": "П2" };

type Props = { sport?: string };

export default function Storefront({ sport = "football" }: Props) {
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [message, setMessage] = useState("Загрузка…");
  const [version, setVersion] = useState<string | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [predictions, setPredictions] = useState<PredictionItem[]>([]);

  const load = useCallback(async () => {
    setStatus("loading");
    setMessage("Загрузка данных…");
    try {
      const [health, eventsData, predData] = await Promise.all([
        fetchHealth(),
        fetchEvents(sport),
        fetchPredictions(sport),
      ]);
      setVersion(String(health.version ?? "?"));
      setEvents(eventsData.items ?? []);
      setPredictions(predData.items ?? []);
      setStatus("ok");
      setMessage(`Обновлено · событий: ${eventsData.count ?? 0}`);
    } catch (err) {
      setStatus("error");
      const msg = err instanceof Error ? err.message : "unknown";
      setMessage(`Данные временно недоступны (${getApiBase()}): ${msg}`);
      setEvents([]);
      setPredictions([]);
    }
  }, [sport]);

  useEffect(() => {
    load();
    const id = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [load]);

  const predByEvent = new Map(predictions.map((p) => [p.event_id, p]));

  return (
    <>
      <div
        className="disclaimer"
        style={{
          borderLeftColor:
            status === "ok" ? "var(--accent-2)" : status === "error" ? "#ef4444" : "var(--warn)",
        }}
      >
        {status === "loading" && message}
        {status === "ok" && (
          <>
            {message}
            {version ? ` · API v${version}` : null}
          </>
        )}
        {status === "error" && (
          <>
            {message}
            <br />
            <small>
              На внешнем хостинге задайте <code>NEXT_PUBLIC_API_URL</code> и разрешите CORS на API
              (переменная <code>STOREFRONT_ORIGINS</code> в Amvera).
            </small>
          </>
        )}
      </div>

      {events.length === 0 && status !== "loading" && (
        <p style={{ color: "var(--muted)" }}>Событий пока нет.</p>
      )}

      {events.map((ev) => {
        const p = predByEvent.get(ev.id);
        const selection = p ? SEL_LABEL[p.selection] ?? p.selection : "—";
        const pct = p ? `${Math.round(p.probability * 100)}%` : "";
        return (
          <EventCard
            key={ev.id}
            home={ev.home_team}
            away={ev.away_team}
            league={ev.league || "Футбол"}
            kickoff={ev.kickoff_at}
            prediction={p ? `${selection} (${pct})` : "—"}
            confidence={(p?.confidence as "low" | "medium" | "high") ?? "medium"}
          />
        );
      })}
    </>
  );
}
