import { useState, type FormEvent } from 'react';
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setBusy(true);
    try { await login({ email, password }); navigate('/', { replace: true }); }
    catch (e: unknown) {
      const message = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setError(message ?? 'Unable to sign in. Check your connection and try again.');
    } finally { setBusy(false); }
  }

  return (
    <Box className="auth-page">
      <Paper className="auth-card" elevation={0}>
        <Typography className="brand-mark">✦ JobPilot AI</Typography>
        <Typography variant="h4" fontWeight={750} mt={4}>Welcome back</Typography>
        <Typography color="text.secondary" mt={1} mb={3}>Sign in to continue your job search.</Typography>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <Stack component="form" onSubmit={submit} spacing={2}>
          <TextField label="Email address" type="email" value={email} onChange={e => setEmail(e.target.value)} required fullWidth />
          <TextField label="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} required fullWidth />
          <Button type="submit" variant="contained" size="large" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</Button>
        </Stack>
        <Typography color="text.secondary" mt={3} textAlign="center">New to JobPilot? <Link to="/register">Create an account</Link></Typography>
      </Paper>
    </Box>
  );
}
