import { useState, type FormEvent } from 'react';
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function RegisterPage() {
  const { register } = useAuth(); const navigate = useNavigate();
  const [full_name, setName] = useState(''); const [email, setEmail] = useState('');
  const [password, setPassword] = useState(''); const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setBusy(true);
    try { await register({ full_name, email, password }); navigate('/login', { replace: true }); }
    catch (e: unknown) {
      const message = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setError(message ?? 'Unable to create your account.');
    } finally { setBusy(false); }
  }
  return <Box className="auth-page"><Paper className="auth-card" elevation={0}>
    <Typography className="brand-mark">✦ JobPilot AI</Typography>
    <Typography variant="h4" fontWeight={750} mt={4}>Create your account</Typography>
    <Typography color="text.secondary" mt={1} mb={3}>Your next opportunity starts here.</Typography>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    <Stack component="form" onSubmit={submit} spacing={2}>
      <TextField label="Full name" value={full_name} onChange={e => setName(e.target.value)} required />
      <TextField label="Email address" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
      <TextField label="Password (minimum 10 characters)" type="password" value={password} onChange={e => setPassword(e.target.value)} inputProps={{ minLength: 10 }} required />
      <Button type="submit" variant="contained" size="large" disabled={busy}>{busy ? 'Creating account…' : 'Create account'}</Button>
    </Stack>
    <Typography color="text.secondary" mt={3} textAlign="center">Already registered? <Link to="/login">Sign in</Link></Typography>
  </Paper></Box>;
}
