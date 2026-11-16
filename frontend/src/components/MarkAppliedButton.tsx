import { useEffect, useState } from "react";
import { Alert, Button } from "@mui/material";
import { api } from "../api/axios";
export default function MarkAppliedButton({ jobId }: { jobId: string }) {
  const [applied, setApplied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { api.get<{job_id: string}[]>("/applications").then(({data}) => setApplied(data.some(a => a.job_id === jobId))).catch(() => setError("Unable to check application status.")); }, [jobId]);
  return <><Button variant="outlined" disabled={applied || busy} onClick={async () => {
    setBusy(true); setError("");
    try { await api.put(`/applications/${jobId}`); setApplied(true); }
    catch { setError("Unable to save application. Please retry."); }
    finally { setBusy(false); }
  }}>{applied ? "Applied" : busy ? "Saving?" : "Mark as applied"}</Button>{error && <Alert severity="error">{error}</Alert>}</>;
}
