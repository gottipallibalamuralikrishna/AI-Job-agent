import { useEffect, useState } from "react";
import { Alert, Box, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { api } from "../api/axios";
import EmailRecipients, { parseManualEmails, invalidManualEmails } from './EmailRecipients';

interface Context { connected: boolean; email: string; resume_name: string | null; sender_name: string; subject: string; body: string; imported_recipients: number; daily_limit: number }
interface Preview { recipient_count: number; sample_recipient: string; subject: string; body: string; resume_name: string | null; preview_token: string }
interface Campaign { id: string; subject: string; sender_email: string; template_name: string | null; total: number; sent: number; queued: number; failed: number; pending_verification: number; cancelled: boolean; errors: string[] }
interface EmailTemplate { id: string; name: string; subject: string; body: string }

function errorText(error: unknown) {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === "string" ? detail : "Unable to complete the request. Please retry.";
}

export default function RecruiterEmailDialog({ contactId }: { contactId?: string }) {
  const [open, setOpen] = useState(false);
  const [context, setContext] = useState<Context | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [allImported, setAllImported] = useState(false);
  const [contactIds, setContactIds] = useState<string[]>(contactId ? [contactId] : []);
  const [manualText, setManualText] = useState("");
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [templateId, setTemplateId] = useState("");
  const [templateName, setTemplateName] = useState("");
  const [editingTemplate, setEditingTemplate] = useState(false);
  const [attach, setAttach] = useState(true);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [history, setHistory] = useState<Campaign[]>([]);
  const [key, setKey] = useState(() => crypto.randomUUID());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const loadHistory = async () => {
    const { data } = await api.get<Campaign[]>("/outreach/campaigns");
    setHistory(data);
  };
  useEffect(() => {
    if (!open) return;
    let active = true;
    setError(""); setNotice(""); setPreview(null); setTemplateId(""); setEditingTemplate(false); setTemplateName("");
    setAllImported(false); setContactIds(contactId ? [contactId] : []); setManualText("");
    api.get<EmailTemplate[]>("/outreach/templates").then(({data}) => { if (active) setTemplates(data); }).catch(e => { if (active) setError(errorText(e)); });
    api.get<Context>("/outreach/context").then(({ data }) => {
      if (!active) return;
      setContext(data); setEmail(data.email); setSubject(data.subject); setBody(data.body); setAttach(Boolean(data.resume_name));
    }).catch(e => { if (active) setError(errorText(e)); });
    void loadHistory().catch(e => setError(errorText(e)));
    const timer = window.setInterval(() => void loadHistory().catch(() => {}), 10000);
    return () => { active = false; window.clearInterval(timer); };
  }, [open, contactId]);
  const manualEmails = parseManualEmails(manualText);
  const recipientsValid = (allImported || contactIds.length > 0 || manualEmails.length > 0) && !invalidManualEmails(manualText).length && manualEmails.length <= 5000;
  const recipientsChanged = () => { setPreview(null); setKey(crypto.randomUUID()); };
  const request = { all_imported: allImported, contact_ids: allImported ? [] : contactIds, manual_emails: manualEmails, subject, body, template_id: templateId || null, attach_resume: attach, request_key: key };
  const selectTemplate = (template: EmailTemplate) => {
    setTemplateId(template.id); setTemplateName(template.name); setSubject(template.subject); setBody(template.body);
    setEditingTemplate(false); setPreview(null); setKey(crypto.randomUUID());
  };
  const saveTemplate = async () => {
    setBusy(true); setError("");
    try {
      const payload = { name: templateName, subject, body };
      const { data } = templateId ? await api.put<EmailTemplate>(`/outreach/templates/${templateId}`, payload) : await api.post<EmailTemplate>("/outreach/templates", payload);
      setTemplates(current => [data, ...current.filter(item => item.id !== data.id)]); selectTemplate(data); setNotice("Template saved and selected.");
    } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  };
  const connect = async () => {
    setBusy(true); setError("");
    try {
      await api.put("/outreach/connection", { email, app_password: password });
      setContext(current => current ? { ...current, connected: true, email } : current); setPassword(""); setNotice("Email account connected.");
    } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  };
  const send = async () => {
    if (!preview) return;
    setBusy(true); setError("");
    try {
      const { data } = await api.post<{ queued: number; duplicates_skipped?: number; already_queued?: boolean }>("/outreach/campaigns", { ...request, preview_token: preview.preview_token });
      setNotice(data.already_queued ? "This request was already queued. See sending history below." : `${data.queued} emails queued. ${data.duplicates_skipped ?? 0} duplicates skipped. Keep the backend running to send them.`);
      setPreview(null); setKey(crypto.randomUUID()); await loadHistory();
    } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  };
  return <>
    <Button variant="contained" onClick={() => setOpen(true)}>{contactId ? "Email recruiter" : "Email imported recruiters"}</Button>
    <Dialog open={open} onClose={() => { if (!busy) { setPassword(""); setOpen(false); } }}
      fullWidth maxWidth="md" className="recruiter-email-dialog">
      <DialogTitle>Recruiter email</DialogTitle>
      <DialogContent><Stack spacing={2} sx={{ pt: 1 }}>
        {error && <Alert severity="error">{error}</Alert>}
        {notice && <Alert severity="success">{notice}</Alert>}
        {!context && !error && <Typography>Loading email setup…</Typography>}
        {context && <>
          <Typography variant="h6">1. Choose an email template</Typography>
          <TextField select label="Saved email template" value={templateId} disabled={busy} fullWidth onChange={e => {
            const template = templates.find(item => item.id === e.target.value);
            if (template) selectTemplate(template);
          }}>
            <MenuItem value="" disabled>Select a template to send</MenuItem>
            {templates.map(template => <MenuItem key={template.id} value={template.id}>{template.name}</MenuItem>)}
          </TextField>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <Button disabled={busy} variant="outlined" onClick={() => {
              setTemplateId(""); setTemplateName(""); setSubject(context.subject); setBody(context.body); setEditingTemplate(true); setPreview(null);
            }}>Create template</Button>
            <Button component="label" variant="outlined" disabled={busy}>Upload template
              <input hidden type="file" accept=".txt,.json" disabled={busy} onChange={async e => {
                const file = e.target.files?.[0]; e.target.value = ""; if (!file) return;
                if (file.size > 131072) { setError("Template file must be smaller than 128 KB."); return; }
                setBusy(true); setError(""); setPreview(null);
                try {
                  const form = new FormData(); form.append("file", file);
                  const { data } = await api.post<EmailTemplate>("/outreach/templates/upload", form);
                  setTemplates(current => [data, ...current]); selectTemplate(data); setNotice("Template uploaded and selected.");
                } catch (error) { setError(errorText(error)); } finally { setBusy(false); }
              }} />
            </Button>
            <Button disabled={busy} onClick={() => {
              const url = URL.createObjectURL(new Blob([`Subject: ${context.subject}\n\n${context.body}\n`], { type: "text/plain;charset=utf-8" }));
              const link = document.createElement("a"); link.href = url; link.download = "recruiter-email-template.txt"; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
            }}>Download sample</Button>
          </Stack>
          <Typography variant="caption">Upload UTF-8 .txt or .json files up to 128 KB. Text files start with “Subject:” on the first line, followed by the message. JSON uses name, subject, and body.</Typography>
          {templateId && !editingTemplate && <Button disabled={busy} onClick={() => { setEditingTemplate(true); setPreview(null); }}>Edit selected template</Button>}
          {editingTemplate && <TextField label="Template name" value={templateName} onChange={e => setTemplateName(e.target.value)} fullWidth inputProps={{ maxLength: 100 }} />}
          <TextField label="Template subject" value={subject} disabled={busy} InputProps={{ readOnly: !editingTemplate }} onChange={e => { setSubject(e.target.value); setPreview(null); }} fullWidth />
          <TextField label="Template message" value={body} disabled={busy} InputProps={{ readOnly: !editingTemplate }} onChange={e => { setBody(e.target.value); setPreview(null); }} fullWidth multiline minRows={9} helperText="Plain-text email. Personalize with {recruiter_name}, {company}, and {sender_name}." />
          {editingTemplate && <Button variant="contained" disabled={busy || !templateName.trim() || !subject.trim() || body.trim().length < 10} onClick={() => void saveTemplate()}>{templateId ? "Save template changes" : "Save template"}</Button>}
          {!templateId && !editingTemplate && <Alert severity="info">Create or upload a template, then select it to prepare your email.</Alert>}
          <Typography variant="h6">2. Sending account and recipients</Typography>
          {context.connected ? <Box><Typography>Sending from {context.email}</Typography><Button disabled={busy} onClick={async () => {
            setBusy(true);
            try { await api.delete("/outreach/connection"); setContext({ ...context, connected: false }); setPreview(null); }
            catch (e) { setError(errorText(e)); } finally { setBusy(false); }
          }}>Disconnect account</Button></Box> : <>
            <Typography>Connect your Gmail account once. Google app passwords require 2-Step Verification.</Typography>
            <TextField label="Sending Gmail address" type="email" value={email} onChange={e => setEmail(e.target.value)} fullWidth />
            <TextField label="Google app password" type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="new-password" fullWidth />
            <Button href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer">Create a Google app password</Button>
            <Button variant="outlined" disabled={busy || !email || !password} onClick={() => void connect()}>Connect email</Button>
          </>}
          <EmailRecipients disabled={busy} importedCount={context.imported_recipients} allImported={allImported}
            onAllImported={value => { setAllImported(value); setContactIds([]); recipientsChanged(); }}
            selectedIds={contactIds} onSelection={ids => { setContactIds(ids); recipientsChanged(); }}
            manualText={manualText} onManualText={value => { setManualText(value); recipientsChanged(); }} />
          <Typography>Emails are sent individually, up to {context.daily_limit} per rolling 24 hours. Remaining emails stay queued.</Typography>
          <FormControlLabel control={<Checkbox checked={attach} disabled={!context.resume_name} onChange={e => { setAttach(e.target.checked); setPreview(null); }} />} label={`Attach primary resume${context.resume_name ? `: ${context.resume_name}` : " (select a primary resume first)"}`} />
          <Button variant="outlined" disabled={busy || !recipientsValid || !templateId || editingTemplate || !subject.trim() || !body.trim()} onClick={async () => {
            setBusy(true); setError("");
            try { const { data } = await api.post<Preview>("/outreach/preview", request); setPreview(data); }
            catch (e) { setError(errorText(e)); } finally { setBusy(false); }
          }}>Preview email and recipients</Button>
          {preview && <Box sx={{ p: 2, border: 1, borderColor: "divider", borderRadius: 1 }}>
            <Typography variant="h6">Preview for {preview.sample_recipient}</Typography>
            <Typography>{preview.subject}</Typography><Typography sx={{ whiteSpace: "pre-wrap", my: 2 }}>{preview.body}</Typography>
            <Typography>Attachment: {preview.resume_name || "None"}</Typography>
            <Typography>{preview.recipient_count.toLocaleString()} recipients selected. Already queued or previously sent copies of the same message and resume will be skipped.</Typography>
            <Button sx={{ mt: 2 }} variant="contained" disabled={busy || !recipientsValid || !context.connected || !templateId || editingTemplate} onClick={() => void send()}>Send to {preview.recipient_count.toLocaleString()} recruiters</Button>
          </Box>}
          {history.length > 0 && <Typography variant="h6">Sending history</Typography>}
          {history.map(campaign => <Box key={campaign.id} sx={{ borderTop: 1, borderColor: "divider", pt: 1 }}>
            <Typography>{campaign.subject}</Typography>
            <Typography variant="caption">From {campaign.sender_email}</Typography>
            {campaign.template_name && <Typography variant="caption" display="block">Template: {campaign.template_name}</Typography>}
            <Typography variant="body2">{campaign.sent} sent · {campaign.queued} queued · {campaign.failed} failed · {campaign.pending_verification} need delivery verification{campaign.cancelled ? " · Cancelled" : ""}</Typography>
            {campaign.errors?.map(message => <Typography display="block" variant="caption" color="warning.main" key={message}>{message}</Typography>)}
            {campaign.pending_verification > 0 && <Typography variant="caption">Check your Sent folder for interrupted deliveries. These emails will not be retried automatically.</Typography>}
            {campaign.queued > 0 && !campaign.cancelled && <Button disabled={busy} onClick={async () => {
              setBusy(true); setError("");
              try { await api.post(`/outreach/campaigns/${campaign.id}/cancel`); await loadHistory(); }
              catch (e) { setError(errorText(e)); } finally { setBusy(false); }
            }}>Cancel remaining emails</Button>}
          </Box>)}
        </>}
      </Stack></DialogContent>
      <DialogActions><Button disabled={busy} onClick={() => { setPassword(""); setOpen(false); }}>Close</Button></DialogActions>
    </Dialog>
  </>;
}
