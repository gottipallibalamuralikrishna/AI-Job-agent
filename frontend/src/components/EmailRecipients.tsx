import { useEffect, useState } from "react";
import { Alert, Box, Button, Checkbox, Chip, FormControlLabel, Stack, TextField, Typography } from "@mui/material";
import { recruiterContactsApi, type RecruiterContact } from "../api/recruiterContactsApi";

interface Props {
  allImported: boolean; onAllImported: (value: boolean) => void; importedCount: number;
  selectedIds: string[]; onSelection: (ids: string[]) => void;
  manualText: string; onManualText: (value: string) => void; disabled: boolean;
}

export function parseManualEmails(value: string) {
  return Array.from(new Set(value.split(/[\s,;]+/).map(email => email.trim().toLowerCase()).filter(Boolean)));
}

export function invalidManualEmails(value: string) {
  return parseManualEmails(value).filter(email => !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email));
}

export default function EmailRecipients(props: Props) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [contacts, setContacts] = useState<RecruiterContact[]>([]);
  const [known, setKnown] = useState<Record<string, RecruiterContact>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (props.allImported) return;
    let active = true;
    setLoading(true);
    const timer = window.setTimeout(() => {
      recruiterContactsApi.getContacts({ page, page_size: 20, search, contact_type: "email" }).then(data => {
        if (!active) return;
        setContacts(data.items); setTotal(data.total); setError("");
        setKnown(current => ({ ...current, ...Object.fromEntries(data.items.map(item => [item.id, item])) }));
      }).catch(() => { if (active) setError("Unable to load HR email addresses. Try searching again."); })
        .finally(() => { if (active) setLoading(false); });
    }, 300);
    return () => { active = false; window.clearTimeout(timer); };
  }, [search, page, props.allImported]);
  useEffect(() => {
    if (props.selectedIds.length !== 1 || known[props.selectedIds[0]]) return;
    let active = true;
    recruiterContactsApi.getContactById(props.selectedIds[0]).then(contact => {
      if (active) setKnown(current => ({ ...current, [contact.id]: contact }));
    }).catch(() => {});
    return () => { active = false; };
  }, [props.selectedIds, known]);
  const invalid = invalidManualEmails(props.manualText);
  const toggle = (id: string, selected: boolean) => props.onSelection(selected ? Array.from(new Set([...props.selectedIds, id])) : props.selectedIds.filter(value => value !== id));
  return <Stack spacing={1}>
    <Typography variant="subtitle1">Choose recipients</Typography>
    <FormControlLabel label={`All imported HR emails (${props.importedCount.toLocaleString()})`} control={<Checkbox disabled={props.disabled} checked={props.allImported} onChange={event => props.onAllImported(event.target.checked)} />} />
    {!props.allImported && <>
      <TextField label="Search HR name, email or company" value={search} disabled={props.disabled} onChange={event => { setSearch(event.target.value); setPage(1); }} fullWidth size="small" />
      {error && <Alert severity="error">{error}</Alert>}
      <Stack direction="row" spacing={1}>
        <Button disabled={props.disabled || loading || !contacts.length} onClick={() => props.onSelection(Array.from(new Set([...props.selectedIds, ...contacts.map(item => item.id)])))}>Select this page</Button>
        <Button disabled={props.disabled || !props.selectedIds.length} onClick={() => props.onSelection([])}>Clear selection</Button>
      </Stack>
      <Box sx={{ maxHeight: 230, overflowY: "auto", border: 1, borderColor: "divider", borderRadius: 1, p: 1 }}>
        {loading ? <Typography>Loading HR emails…</Typography> : contacts.length ? contacts.map(contact => <FormControlLabel key={contact.id} sx={{ display: "flex", alignItems: "flex-start", mb: 1 }}
          control={<Checkbox size="small" disabled={props.disabled} checked={props.selectedIds.includes(contact.id)} onChange={event => toggle(contact.id, event.target.checked)} />}
          label={<Box><Typography variant="body2">{contact.contact_name || "Recruiter"} · {contact.contact_value}</Typography><Typography variant="caption" color="text.secondary">{contact.job.company_name}</Typography></Box>} />)
          : <Typography>No HR emails match this search. You can enter an address below.</Typography>}
      </Box>
      <Stack direction="row" spacing={1} alignItems="center">
        <Button disabled={props.disabled || loading || page === 1} onClick={() => setPage(current => current - 1)}>Previous</Button>
        <Typography variant="body2">Page {page} · {total.toLocaleString()} results</Typography>
        <Button disabled={props.disabled || loading || page * 20 >= total} onClick={() => setPage(current => current + 1)}>Next</Button>
      </Stack>
      <Typography variant="body2">{props.selectedIds.length} HR contacts selected across all pages.</Typography>
      <Stack direction="row" gap={1} flexWrap="wrap">{props.selectedIds.slice(0, 20).map(id => <Chip key={id} size="small" label={known[id]?.contact_value || "Selected HR contact"} disabled={props.disabled} onDelete={() => toggle(id, false)} />)}</Stack>
      {props.selectedIds.length > 20 && <Typography variant="caption">Plus {props.selectedIds.length - 20} more selected contacts.</Typography>}
    </>}
    <TextField label="Manually add email addresses" value={props.manualText} onChange={event => props.onManualText(event.target.value)} disabled={props.disabled} fullWidth multiline minRows={2}
      placeholder="hr@company.com, recruiter@anothercompany.com" error={invalid.length > 0}
      helperText={invalid.length ? `Check these addresses: ${invalid.slice(0, 3).join(", ")}` : "Separate addresses with commas, semicolons, spaces or new lines. You can combine these with selected HR contacts. Duplicate addresses receive one email."} />
    {parseManualEmails(props.manualText).length > 5000 && <Alert severity="error">Enter at most 5,000 manual email addresses.</Alert>}
  </Stack>;
}
