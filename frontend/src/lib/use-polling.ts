"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

export function usePolling<T>(path: string | null, intervalMs = 10000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!path) return;
    try {
      setData(await api<T>(path));
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطا");
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    reload();
    if (!path) return;
    const timer = window.setInterval(reload, intervalMs);
    return () => window.clearInterval(timer);
  }, [reload, intervalMs, path]);

  return { data, error, loading, reload };
}
