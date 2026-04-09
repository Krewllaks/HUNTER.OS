"use client";

import { useState, useEffect, useCallback, useRef } from "react";

/**
 * SSE event types emitted by /api/v1/hunt/stream/{product_id}
 */
export type HuntEventType =
  | "discovery_started"
  | "discovery_progress"
  | "lead_found"
  | "lead_reused"
  | "discovery_complete"
  | "discovery_error";

export interface HuntEvent {
  type: HuntEventType;
  data: Record<string, unknown>;
  timestamp: string;
}

interface UseHuntStreamReturn {
  events: HuntEvent[];
  latestEvent: HuntEvent | null;
  isConnected: boolean;
  leadsFound: number;
  progress: number; // 0-100
  status: "idle" | "connecting" | "streaming" | "complete" | "error";
  connect: (productId: number) => void;
  disconnect: () => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Hook for consuming real-time hunt progress via SSE.
 *
 * Usage:
 *   const { connect, events, leadsFound, progress, status } = useHuntStream();
 *   connect(productId);
 */
export function useHuntStream(): UseHuntStreamReturn {
  const [events, setEvents] = useState<HuntEvent[]>([]);
  const [latestEvent, setLatestEvent] = useState<HuntEvent | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [leadsFound, setLeadsFound] = useState(0);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<UseHuntStreamReturn["status"]>("idle");
  const sourceRef = useRef<EventSource | null>(null);

  const disconnect = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const connect = useCallback(
    (productId: number) => {
      // Clean up any existing connection
      disconnect();

      const token = typeof window !== "undefined"
        ? localStorage.getItem("hunter_token")
        : null;

      if (!token) {
        setStatus("error");
        return;
      }

      setStatus("connecting");
      setEvents([]);
      setLeadsFound(0);
      setProgress(0);

      const url = `${API_BASE}/api/v1/hunt/stream/${productId}?token=${encodeURIComponent(token)}`;
      const source = new EventSource(url);
      sourceRef.current = source;

      source.onopen = () => {
        setIsConnected(true);
        setStatus("streaming");
      };

      source.onerror = () => {
        setIsConnected(false);
        if (status !== "complete") {
          setStatus("error");
        }
        source.close();
      };

      // Listen to all known event types
      const eventTypes: HuntEventType[] = [
        "discovery_started",
        "discovery_progress",
        "lead_found",
        "lead_reused",
        "discovery_complete",
        "discovery_error",
      ];

      for (const eventType of eventTypes) {
        source.addEventListener(eventType, (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data);
            const event: HuntEvent = {
              type: eventType,
              data,
              timestamp: data.timestamp || new Date().toISOString(),
            };

            setEvents((prev) => [...prev.slice(-200), event]); // Keep last 200
            setLatestEvent(event);

            // Update counters
            if (eventType === "lead_found") {
              setLeadsFound((prev) => prev + 1);
            }
            if (eventType === "discovery_progress") {
              const total = data.total_queries || 1;
              const done = data.queries_done || 0;
              setProgress(Math.round((done / total) * 100));
            }
            if (eventType === "discovery_complete") {
              setStatus("complete");
              setProgress(100);
              source.close();
            }
            if (eventType === "discovery_error") {
              setStatus("error");
            }
          } catch {
            // Ignore malformed events
          }
        });
      }
    },
    [disconnect, status]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (sourceRef.current) {
        sourceRef.current.close();
      }
    };
  }, []);

  return {
    events,
    latestEvent,
    isConnected,
    leadsFound,
    progress,
    status,
    connect,
    disconnect,
  };
}
