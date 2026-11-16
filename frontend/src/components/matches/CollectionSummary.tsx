import { useEffect, useState } from "react";
import { Alert, Box, Button, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { Link } from "react-router-dom";
import { api } from "../../api/axios";

interface Summary {
  status: string | null;
  latest_at: string | null;
  last_success_at: string | null;
  next_scheduled_at: string | null;
  new_jobs: number | null;
  source_issues: number;
  run_failed: boolean;
  blocker: string | null;
  timezone: string;
}

const statuses: Record<string, string> = {
  queued: "Queued",
  running: "Collecting",
  completed: "Completed",
  partial: "Completed with issues",
  failed: "Failed",
};

export default function CollectionSummary() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let active = true;
    let timer: number;
    const load = async () => {
      try {
        const { data } = await api.get<Summary>("/collections/summary", { timeout: 8000 });
        if (active) {
          setSummary(data);
          setUnavailable(false);
        }
      } catch {
        if (active) setUnavailable(true);
      } finally {
        if (active) timer = window.setTimeout(load, 10000);
      }
    };
    void load();
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, []);

  const format = (value: string | null) => value
    ? new Date(value).toLocaleString("en-IN", {
      timeZone: summary?.timezone, day: "numeric", month: "short",
      hour: "numeric", minute: "2-digit", timeZoneName: "short",
    })
    : "—";
  const status = summary?.status;

  return (
    <Card className="match-collection-card" variant="outlined">
      <CardContent>
        <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
          <Typography component="h2" variant="subtitle1" fontWeight={700}>Job collection</Typography>
          <Button component={Link} to="/resume" size="small">Collection details</Button>
        </Stack>
        {unavailable ? (
          <Typography variant="body2" color="text.secondary" role="status">Collection status is currently unavailable.</Typography>
        ) : summary ? (
          <>
            <Box className="match-collection-stats">
              <Box>
                <Typography variant="caption" color="text.secondary" display="block">Latest run</Typography>
                <Chip size="small" variant="outlined" label={status ? statuses[status] ?? status : "No runs yet"}
                  color={status === "failed" ? "error" : status === "partial" ? "warning" : status === "completed" ? "success" : "default"} />
                {summary.latest_at && <Typography variant="caption" color="text.secondary" display="block">{format(summary.latest_at)}</Typography>}
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" display="block">New jobs above 80%</Typography>
                <Typography variant="body2" fontWeight={700}>{summary.new_jobs ?? "—"}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" display="block">Last run that fetched successfully</Typography>
                <Typography variant="body2" fontWeight={700}>{format(summary.last_success_at)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" display="block">Next scheduled run</Typography>
                <Typography variant="body2" fontWeight={700}>{format(summary.next_scheduled_at)}</Typography>
              </Box>
            </Box>
            {summary.blocker && <Alert severity="warning" sx={{ mt: 1.5 }}>{summary.blocker}</Alert>}
            {summary.source_issues > 0 && (
              <Typography variant="body2" color="warning.main" sx={{ mt: 1 }}>
                Sources with issues: {summary.source_issues}
              </Typography>
            )}
            {summary.run_failed && (
              <Typography variant="body2" color="error.main" sx={{ mt: 1 }}>
                The run stopped early. Open Collection details for the reason.
              </Typography>
            )}
          </>
        ) : <Typography variant="body2" color="text.secondary" role="status">Loading collection status…</Typography>}
      </CardContent>
    </Card>
  );
}
