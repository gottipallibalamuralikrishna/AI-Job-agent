import { useEffect, useState } from "react";
import { Alert, Box, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { api } from "../../api/axios";
import { useAuth } from "../../context/AuthContext";

interface CollectionRun {
  id: string;
  status: string;
  created_at: string;
  error: string | null;
  results: { source: string; status: string; created?: number; updated?: number; error?: string }[];
}

export default function CollectionStatus() {
  const { user } = useAuth();
  const [runs, setRuns] = useState<CollectionRun[]>([]);
  const [error, setError] = useState("");
  const [queuing, setQueuing] = useState(false);
  const load = async () => {
    try {
      const { data } = await api.get<CollectionRun[]>("/collections");
      setRuns(data);
    } catch {
      setError("Unable to load job collection status.");
    }
  };
  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(timer);
  }, []);
  const collect = async () => {
    setQueuing(true);
    setError("");
    try {
      await api.post("/collections");
      await load();
    } catch {
      setError("Select a primary resume and extract its profile before collecting jobs.");
    } finally {
      setQueuing(false);
    }
  };
  const latest = runs[0];
  return (
    <Card><CardContent><Stack spacing={2}>
      <Typography variant="h6">Job collection</Typography>
      <Typography color="text.secondary">
        Uses your primary resume. Jobs scoring above 80 are saved with application links.
        Automatic collection runs daily at 8:00 AM India time while the backend is running.
        Jobs expire after 30 days; HR contacts are kept.
      </Typography>
      {user?.include_international_remote && <Typography color="text.secondary">
        Includes overseas remote roles explicitly open to {user.preferred_job_country || "your country"} or worldwide applicants.
      </Typography>}
      <Button variant="outlined" disabled={queuing || latest?.status === "queued" || latest?.status === "running"} onClick={() => void collect()}>
        {queuing ? "Queuing..." : "Collect matching jobs"}
      </Button>
      {error && <Alert severity="error">{error}</Alert>}
      {latest ? <>
        <Typography>Latest collection: {latest.status} · {new Date(latest.created_at).toLocaleString()}</Typography>
        {latest.error && <Alert severity="error">{latest.error}</Alert>}
        {latest.results.map((result, index) => <Box key={`${result.source}-${index}`}>
          <Typography variant="body2">{result.source}: {result.status}
            {result.status === "completed" && ` — ${result.created ?? 0} new, ${result.updated ?? 0} updated`}
          </Typography>
          {result.error && <Typography variant="caption" color="warning.main">{result.error}</Typography>}
        </Box>)}
      </> : <Typography color="text.secondary">No collections yet.</Typography>}
    </Stack></CardContent></Card>
  );
}
