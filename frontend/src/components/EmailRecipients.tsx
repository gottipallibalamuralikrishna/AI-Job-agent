import InfiniteScroll from "./InfiniteScroll";
import usePagedFeed from "../api/usePagedFeed";
import { useCallback, useEffect, useState } from "react";
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
  const [list, setList] = useState<HTMLElement | null>(null);
  const [known, setKnown] = useState<Record<string, RecruiterContact>>({});
  const [debouncedSearch, setDebouncedSearch] = useState("");
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(search.trim());
      if (list) list.scrollTop = 0;
    }, 300);
    return () => window.clearTimeout(timer);
  }, [search, list]);
  const fetchPage = useCallback(async (page: number) => {
    const { items, total } = await recruiterContactsApi.getContacts({
      page, page_size: 20, search: debouncedSearch, contact_type: "email",
    });
    return { items, total, hasMore: page * 20 < total };
  }, [debouncedSearch]);
  const { items: contacts, loading, error, hasMore, loadMore } = usePagedFeed(fetchPage, !props.allImported);
  useEffect(() => {
    if (contacts.length > 0) {
      setKnown((current) => ({ ...current, ...Object.fromEntries(contacts.map((item) => [item.id, item])) }));
    }
  }, [contacts]);
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
      <TextField label="Search HR name, email or company" value={search} disabled={props.disabled} onChange={event => { setSearch(event.target.value); }} fullWidth size="small" />
      {error && <Alert severity="error">Unable to load HR email addresses.</Alert>}
      <Stack direction="row" gap={1} flexWrap="wrap">
        <Button disabled={props.disabled || loading || !contacts.length} onClick={() => props.onSelection(Array.from(new Set([...props.selectedIds, ...contacts.map(item => item.id)])))}>Select loaded contacts</Button>
        <Button disabled={props.disabled || !props.selectedIds.length} onClick={() => props.onSelection([])}>Clear selection</Button>
      </Stack>
      <Box ref={setList} sx={{ maxHeight: 230, overflowY: "auto", border: 1, borderColor: "divider", borderRadius: 1, p: 1 }}>
        {contacts.length ? contacts.map(contact => <FormControlLabel key={contact.id} sx={{ display: "flex", alignItems: "flex-start", mb: 1 }}
          control={<Checkbox size="small" disabled={props.disabled} checked={props.selectedIds.includes(contact.id)} onChange={event => toggle(contact.id, event.target.checked)} />}
          label={<Box><Typography variant="body2">{contact.contact_name || "Recruiter"} · {contact.contact_value}</Typography><Typography variant="caption" color="text.secondary">{contact.job.company_name}</Typography></Box>} />)
          : !loading && !error && <Typography>No HR emails match this search. You can enter an address below.</Typography>}
        <InfiniteScroll root={list} hasMore={hasMore && !props.disabled} loading={loading}
          error={error && !props.disabled} onLoad={loadMore} />
      </Box>
      <Typography variant="body2">{props.selectedIds.length} HR contacts selected.</Typography>
      <Stack direction="row" gap={1} flexWrap="wrap">{props.selectedIds.slice(0, 20).map(id => <Chip key={id} size="small" label={known[id]?.contact_value || "Selected HR contact"} disabled={props.disabled} onDelete={() => toggle(id, false)} />)}</Stack>
      {props.selectedIds.length > 20 && <Typography variant="caption">Plus {props.selectedIds.length - 20} more selected contacts.</Typography>}
    </>}
    <TextField label="Manually add email addresses" value={props.manualText} onChange={event => props.onManualText(event.target.value)} disabled={props.disabled} fullWidth multiline minRows={2}
      placeholder="hr@company.com, recruiter@anothercompany.com" error={invalid.length > 0}
      helperText={invalid.length ? `Check these addresses: ${invalid.slice(0, 3).join(", ")}` : "Separate addresses with commas, semicolons, spaces or new lines. You can combine these with selected HR contacts. Duplicate addresses receive one email."} />
    {parseManualEmails(props.manualText).length > 5000 && <Alert severity="error">Enter at most 5,000 manual email addresses.</Alert>}
  </Stack>;
}
