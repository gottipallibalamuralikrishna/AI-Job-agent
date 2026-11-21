import { useEffect, useState } from "react";
import { Alert, Button, Card, CardContent, Chip, LinearProgress, Stack, Typography } from "@mui/material";
import { isAxiosError } from "axios";
import { RefreshCw } from "lucide-react";
import { api } from "../../api/axios";

interface CollectionRun {
  status: string;
  error: string | null;
  results: { status: string; created?: number }[];
}

const statusLabels: Record<string, string> = {
  queued: "Queued", running: "Collecting", completed: "Completed",
  partial: "Completed with issues", failed: "Failed",
};

export default function CollectionStatus() {
  const [latest, setLatest] = useState<CollectionRun | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [queueError, setQueueError] = useState("");
  const [queuing, setQueuing] = useState(false);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let timer: number;
    const load = async () => {
      try {
        const { data } = await api.get<CollectionRun[]>("/collections", {
          signal: controller.signal, timeout: 8000,
        });
        if (controller.signal.aborted) return;
        setLatest(data[0] ?? null);
        setLoadError(false);
      } catch {
        if (!controller.signal.aborted) setLoadError(true);
      } finally {
        if (!controller.signal.aborted) timer = window.setTimeout(load, 5000);
      }
    };
    void load();
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [refresh]);

  const collect = async () => {
    setQueuing(true);
    setQueueError("");
    try {
      const { data } = await api.post<{ status: string }>("/collections");
      setLatest({ status: data.status, results: [], error: null });
      setRefresh((value) => value + 1);
    } catch (error) {
      const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
      setQueueError(typeof detail === "string" ? detail : "Unable to start collection. Try again.");
    } finally {
      setQueuing(false);
    }
  };

  const running = latest?.status === "running" || latest?.status === "queued";
  const results = latest?.results ?? [];
  const newJobs = results.reduce((count, result) => count + (result.created ?? 0), 0);
  const issues = results.filter((result) => result.status !== "completed").length;

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.5}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1} flexWrap="wrap">
            <Stack spacing={0.25}>
              <Typography variant="h6" component="h2">Job collection</Typography>
              <Typography variant="caption" color="text.secondary">Daily at 8:00 AM IST · Matches above 80%</Typography>
            </Stack>
            {latest && <Chip size="small" variant="outlined" label={statusLabels[latest.status] ?? latest.status} />}
          </Stack>
          {(queuing || running) && <LinearProgress aria-label="Job collection progress" sx={{ borderRadius: 2 }} />}
          {latest && (
            <Stack direction="row" flexWrap="wrap" gap={2} role="status">
              <Typography variant="body2"><strong>{newJobs}</strong> new jobs</Typography>
              <Typography variant="body2" color="text.secondary">{results.length} sources checked</Typography>
              {issues > 0 && <Typography variant="body2" color="warning.main">{issues} with issues</Typography>}
            </Stack>
          )}
          {(loadError || queueError || latest?.error) && (
            <Alert severity="error">{queueError || latest?.error || "Unable to refresh collection status."}</Alert>
          )}
          <Button size="small" variant="contained" startIcon={<RefreshCw size={14} />}
            disabled={queuing || running} onClick={() => void collect()}
            sx={{ alignSelf: "flex-start" }}>
            {queuing ? "Starting…" : running ? "Collection in progress" : "Collect matching jobs"}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
