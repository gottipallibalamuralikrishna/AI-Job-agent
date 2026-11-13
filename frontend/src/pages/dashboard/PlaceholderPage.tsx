import { Card, CardContent, Typography, Stack } from '@mui/material';

export default function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <Stack spacing={2}>
      <Typography variant="h4" fontWeight={800}>{title}</Typography>
      <Card className="panel-card">
        <CardContent sx={{ p: 3 }}>
          <Typography fontWeight={700}>{title} module</Typography>
          <Typography color="text.secondary" mt={1}>{description}</Typography>
          <Typography color="text.secondary" variant="caption" display="block" mt={2}>
            This module will be connected to real backend data in its implementation phase.
          </Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
