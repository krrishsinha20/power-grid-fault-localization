import { useCallback, useEffect, useRef, useState } from "react";

const DEFAULT_INTERVAL = Number(import.meta.env.VITE_POLL_INTERVAL_MS ?? 5000);

/**
 * Polls `fetcher` on an interval and exposes { data, error, loading,
 * refresh }. We use polling rather than WebSockets here -- justified
 * in ARCHITECTURE.md: at the assignment's scale (dozens of incidents,
 * not thousands) a 5s poll comfortably beats the brief's <120s
 * detection-to-screen target, and it sidesteps the classic
 * WebSocket-behind-a-proxy deployment failure mode on free hosting
 * tiers. `refresh` lets a user action (e.g. injecting a fault) force
 * an immediate re-fetch instead of waiting for the next tick.
 */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number = DEFAULT_INTERVAL
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    const tick = async () => {
      if (cancelled) return;
      await refresh();
      if (!cancelled) {
        timer = window.setTimeout(tick, intervalMs);
      }
    };

    tick();

    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs]);

  return { data, error, loading, refresh };
}
