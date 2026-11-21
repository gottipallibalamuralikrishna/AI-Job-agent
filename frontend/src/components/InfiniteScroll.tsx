import { useEffect, useRef } from "react";
import { Box, Button, CircularProgress } from "@mui/material";

export default function InfiniteScroll({ hasMore, loading, error, onLoad, root }:
  { hasMore: boolean; loading: boolean; error: boolean; onLoad: () => void; root?: HTMLElement | null }) {
  const marker = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!hasMore || loading || error || !marker.current) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        observer.disconnect();
        onLoad();
      }
    }, { root, rootMargin: "120px 0px" });
    observer.observe(marker.current);
    return () => observer.disconnect();
  }, [hasMore, loading, error, onLoad, root]);

  return (
    <Box ref={marker} sx={{ minHeight: 1, textAlign: "center", py: loading || error ? 1 : 0 }}>
      {loading && <CircularProgress size={22} aria-label="Loading more results" />}
      {error && <Button size="small" onClick={onLoad}>Retry loading results</Button>}
    </Box>
  );
}
