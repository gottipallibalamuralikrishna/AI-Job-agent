import { useEffect, useState } from "react";
import { Alert, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { api } from "../../api/axios";
interface Application { job_id: string; applied_at: string; snapshot: { title: string; company_name: string; location: string | null; application_url: string | null } }
export default function ApplicationsPage() {
 const [items, setItems] = useState<Application[]>([]);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState("");
 useEffect(() => { api.get<Application[]>("/applications").then(({data}) => setItems(data)).catch(() => setError("Unable to load applications.")).finally(() => setLoading(false)); }, []);
 return <Stack spacing={2}><Typography variant="h4">Applications</Typography>{error && <Alert severity="error">{error}</Alert>}{loading ? <Typography>Loading applications?</Typography> : !error && !items.length && <Typography>After applying on the employer?s website, select ?Mark as applied? on the job.</Typography>}{items.map(a => <Card key={a.job_id}><CardContent><Typography variant="h6">{a.snapshot.title}</Typography><Typography>{a.snapshot.company_name} ? {a.snapshot.location}</Typography><Typography>Applied ? {new Date(a.applied_at).toLocaleDateString()}</Typography>{a.snapshot.application_url && <Button href={a.snapshot.application_url} target="_blank" rel="noopener noreferrer">View job</Button>}</CardContent></Card>)}</Stack>;
}
