import { useCallback, useEffect, useRef, useState } from "react";

export default function usePagedFeed<T extends { id: string }>(
  fetchPage: (page: number) => Promise<{ items: T[]; total: number; hasMore: boolean }>,
  enabled = true,
) {
  const [items, setItems] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const request = useRef(0);
  const busy = useRef(false);
  const nextPage = useRef(1);

  const loadMore = useCallback(async () => {
    if (!enabled || busy.current) return;
    busy.current = true;
    const sequence = ++request.current;
    const page = nextPage.current;
    setLoading(true);
    setError(false);
    try {
      const data = await fetchPage(page);
      if (sequence !== request.current) return;
      setItems((previous) => {
        const unique = new Map(previous.map((item) => [item.id, item]));
        for (const item of data.items) unique.set(item.id, item);
        return [...unique.values()];
      });
      setTotal(data.total);
      setHasMore(data.hasMore);
      nextPage.current = page + 1;
    } catch {
      if (sequence === request.current) setError(true);
    } finally {
      if (sequence === request.current) {
        busy.current = false;
        setLoading(false);
      }
    }
  }, [enabled, fetchPage]);

  const reload = useCallback(() => {
    request.current++;
    busy.current = false;
    nextPage.current = 1;
    setItems([]);
    setTotal(0);
    setHasMore(false);
    setError(false);
    setLoading(enabled);
    if (enabled) void loadMore();
  }, [enabled, loadMore]);

  useEffect(() => {
    reload();
    return () => { request.current++; busy.current = false; };
  }, [reload]);

  return { items, total, hasMore, loading, error, loadMore, reload };
}
