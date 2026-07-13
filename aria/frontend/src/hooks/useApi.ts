import { useState, useEffect, useCallback, useRef } from 'react';

// ── Generic API Data Fetching Hook ─────────────────────────────────────────────
export function useApi<T>(
  apiCall: () => Promise<T>,
  dependencies: unknown[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiCall();
      setData(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
      setData(null);
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  useEffect(() => {
    refetch();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refetch]);

  return { data, loading, error, refetch };
}

// ── Auto-polling Hook ──────────────────────────────────────────────────────────
export function usePolling<T>(
  apiCall: () => Promise<T>,
  intervalMs = 30_000,
  dependencies: unknown[] = []
) {
  const { data, loading, error, refetch } = useApi(apiCall, dependencies);

  useEffect(() => {
    const id = setInterval(refetch, intervalMs);
    return () => clearInterval(id);
  }, [refetch, intervalMs]);

  return { data, loading, error, refetch };
}

// ── WebSocket Hook ─────────────────────────────────────────────────────────────
export { useWebSocket } from './useWebSocket';

