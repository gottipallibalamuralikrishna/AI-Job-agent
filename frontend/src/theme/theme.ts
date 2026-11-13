import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#8b7cff' },
    secondary: { main: '#36cfc9' },
    background: { default: '#090d18', paper: '#111827' },
    text: { primary: '#f4f6fc', secondary: '#9aa6bd' },
    success: { main: '#35c98a' },
  },
  shape: { borderRadius: 12 },
  typography: { fontFamily: '"Inter", "Segoe UI", sans-serif', button: { textTransform: 'none', fontWeight: 600 } },
});
