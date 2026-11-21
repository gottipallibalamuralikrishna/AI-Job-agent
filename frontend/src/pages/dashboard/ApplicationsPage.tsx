import { useEffect, useState } from "react";
import {
  Alert, Button, Paper, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Typography,
} from "@mui/material";
import { api } from "../../api/axios";

interface Application {
  job_id: string;
  applied_at: string;
  snapshot: {
    title: string;
    company_name: string;
    location: string | null;
    application_url: string | null;
  };
}

export default function ApplicationsPage() {
  const [items, setItems] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Application[]>("/applications")
      .then(({ data }) => setItems(data))
      .catch(() => setError("Unable to load applications."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Stack spacing={2} sx={{ p: { xs: 2, md: 3 } }}>
      <Typography variant="h4" component="h1">Applications</Typography>
      {error && <Alert severity="error">{error}</Alert>}
      {loading && <Typography role="status">Loading applications...</Typography>}
      {!loading && !error && items.length === 0 && (
        <Typography color="text.secondary">
          When you apply for a job, select Mark as applied to track it here.
        </Typography>
      )}
      {items.length > 0 && (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" aria-label="Job applications" sx={{ minWidth: 620 }}>
            <TableHead>
              <TableRow>
                <TableCell>Job title</TableCell>
                <TableCell>Company</TableCell>
                <TableCell>Location</TableCell>
                <TableCell>Applied on</TableCell>
                <TableCell align="right">Link</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map(({ job_id, applied_at, snapshot }) => (
                <TableRow key={job_id} hover>
                  <TableCell component="th" scope="row">{snapshot.title}</TableCell>
                  <TableCell>{snapshot.company_name}</TableCell>
                  <TableCell>{snapshot.location || "Not specified"}</TableCell>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>{new Date(applied_at).toLocaleDateString()}</TableCell>
                  <TableCell align="right">
                    {snapshot.application_url && (
                      <Button size="small" href={snapshot.application_url} target="_blank" rel="noopener noreferrer"
                        aria-label={"View job: " + snapshot.title} sx={{ whiteSpace: "nowrap" }}>
                        View job
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Stack>
  );
}
